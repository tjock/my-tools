#!/bin/bash

if [ $# -eq 0 ]
then
    file_path="."
else
    file_path="$1"
fi ;

find "$file_path" -name "*.smali" > smali_file;

cat smali_file | while read line;
do
    file=$line;
	echo "replace $file"
	sed -i 's/invoke-direct {p0},/invoke-direct\/range {p0 .. p0},/g' $file
done

rm smali_file;
