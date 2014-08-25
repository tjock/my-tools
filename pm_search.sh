#!/bin/bash

if [ $# -eq 0 ]
then
	IN_PATH="."
else
	IN_PATH=$1
fi
HOME_PATH=`cd ~ && pwd`
TMP_PATH=$HOME_PATH"/out_pm_search/tmp/"
OUT_PATH=$HOME_PATH"/out_pm_search/out/"

# Scan public intefaces in a file
function _grep_public_interface()
{
		 #       public    return-type    func         (    int       param       ,           )         { 
		     egrep "(\\s*)public(\\s*)(\\S+)(\\s*)(\\S+)(\\s*)(\()((\\S+)(\\s*)(\\S+)(\\s*),?)*(\\s*)(\))(\\s*)(\{)" $1
}


function deleteNote()
{
	if [ -f $1 ]
	then
		echo $1
		sed -e :a -e "N;s/\/\//\n\/\//g;ba" $1 > tmp
		sed -i '/^$/d; /^\/\//d' tmp
		sed -e :a -e "N;s/\n/#/g;ba" tmp > tmp1

		sed -i 's/\/\*/\n\@\@/g;' tmp1
		sed -i 's/\*\//\@\@\@\n/g;' tmp1
		sed -i '/^$/d;/^\@\@.*\@\@\@$/d;' tmp1
		sed -i 's/\t/ /g;' tmp1

		sed -e :a -e "N;s/public/\nPUBLIC/g;ba" tmp1 > tmp
		sed -e :a -e "N;s/{/\n/g;ba" tmp > tmp1
		sed -e :a -e "N;s/\;/\n/g;ba" tmp1 > tmp
		sed 's/#/ /g; s/PUBLIC/public/g; s/  */ /g' tmp > $1
	fi
}


function isCodeNotNoted()
{
	echo "FALSE"
}


function getFuncName()
{
	echo "what"
}

if [ -d $OUT_PATH ]
then
	rm $OUT_PATH -rf
fi

if [ -d $TMP_PATH ]
then
	rm $TMP_PATH -rf
fi

mkdir -p $OUT_PATH
mkdir -p $TMP_PATH

cp -r $IN_PATH $TMP_PATH
echo "copy files...."

find $TMP_PATH -name "*.java" > java_file
find $TMP_PATH -name "*.aidl" > aidl_file
find $TMP_PATH -name "java_out" | xargs rm -f

cat java_file | while read LINE
do
	fName=`basename $LINE`
	let "flen=${#LINE}-${#fName}"
	out_file_path="${LINE:0:$flen}"
	out_file_name=`echo $out_file_path | sed 's/\/tmp\//\/out\//g'`
	
	if [ ! -d $out_file_name ]
	then
		mkdir -p $out_file_name
	fi
	out_file_name=$out_file_name"/java_out"

	echo -e "\n####$LINE####" > $out_file_name

	deleteNote $LINE

	awk '{if ($0 ~ /public .*\(.*\)/){print $0}}' $LINE > tmp
        
	sed -i 's/(/( /g; s/)/ )/g; s/,/ /g' tmp


	awk '
	BEGIN{i=1; begin=0}
	{
		begin=0;
		i=1;
		while (i < NF)
		{
			if (begin == 0)
			{
				if ($i ~ /.*\(/)
				{
					begin=i;
				}
			}else
			{
				if ( (begin%2) == (i%2))
				{
					gsub(/.*/, "", $i);
				}
			}
			i++;
		}
		print $0
	}' tmp > tmp1

	sed 's/  */ /g; s/( /(/g; s/) /)/g; s/ )/)/g' tmp1 >> $out_file_name

done

rm tmp
rm tmp1
rm -rf $TMP_PATH
