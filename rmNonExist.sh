#!/bin/bash

function usage()
{
	echo ">>>>>>>>>>>>>>> usage <<<<<<<<<<<<<<<<"
	echo ">>> rmNonExist.sh [-i] inputMk officialDir"
	echo ">>> -i: these will modify the input makefile"
	echo ">>> inputMk: input makefile"
	echo ">>> officalDir: where the official direcotry is, "
	echo ">>> make sure there is a system directory right in the officalDir"
	echo ">>>>>>>>>>>>>>>  end  <<<<<<<<<<<<<<<<"
}

function filterOut()
{
	mk=$1
	filterParam=`echo $FILTER_OUT_PARAM | sed 's/^|//g; s/|$//g'`

	if [ "x$filterParam" != "x" ];then
		tempFile=`mktemp -t filterIn.mk.XXX`
		echo "egrep -v \"$filterParam\" $mk > $tempFile"
		egrep -v "$filterParam" $mk > $tempFile
		mv $tempFile $mk
	fi
}

if [ "$#" -le 1 ];then
	usage
	exit
fi

if [ "$1" == "-i" ];then
	REPLACE=true
	shift
else
	REPLACE=false
fi

INPUT_MK=$1
OFFICIAL_DIR=$2
ARG_MAX=`getconf ARG_MAX`
GREP_ARG_MAX=`expr $ARG_MAX - 2000`
INPUT_MK_STR=`cat $INPUT_MK`
FILTER_OUT_PARAM=""

if [ "x$INPUT_MK" == "x" ] || [ ! -f $INPUT_MK ]; then
	echo ">>> File $INPUT_MK doesn't exist!"
	usage
	exit 1
fi

if [ "x$OFFICIAL_DIR" == "x" ] || [ ! -d $OFFICIAL_DIR ]; then
	echo ">>> Directory $INPUT_MK doesn't exist!"
	usage
	exit 1
fi

if [ $REPLACE == true ];then
	OUTPUT_MK=$INPUT_MK
else
	OUTPUT_MK="`basename $INPUT_MK`.ok.mk"
	cp $INPUT_MK $OUTPUT_MK
fi

tempMk=`mktemp -t input.mk.XXX`
echo ">>> tempMk: $tempMk"

grep -v "^[ \t]#" $INPUT_MK \
	| grep ':' \
	| awk -F: '{print $2}' \
	| sed 's/[ \t\/]*\\[ \t]*$//g' \
	| sed "s/^[ \t\/]*//g" \
	| grep "^system" > $tempMk

while read LINE
do
	if [ ! -f "$OFFICIAL_DIR/$LINE" ];then
		echo ">>> $OFFICIAL_DIR/$LINE doesn't exist!, remove from $INPUT_MK"
		baseName=${LINE##*system/}
		FILTER_OUT_PARAM="$FILTER_OUT_PARAM|$baseName"
		if [ ${#FILTER_OUT_PARAM} -ge "$GREP_ARG_MAX" ];then
			echo ">>> the parameter is too long, use grep to filter out!"
			filterOut $OUTPUT_MK
			FILTER_OUT_PARAM=""
		fi
	fi
done < $tempMk

filterOut $OUTPUT_MK
echo ">>> output: $OUTPUT_MK"

rm $tempMk
