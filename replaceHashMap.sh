#!/bin/bash

inDir=$1

if [ ! -d $inDir ];then
	echo "wrong parameters!"
	exit 1
fi

javaFileList=$(mktemp -t javaList.XXXX)

echo "Get all java files in $inDir to $javaFileList"
find $inDir -type f -name "*.java" > $javaFileList

function replace()
{
	src=$1
	target=$2

	echo "replace $src to $target"
	
	cat $javaFileList | xargs -n1 sed -i "s/$src/$target/g"
}


function hashMapToArrayMap()
{
	replace "java.util.HashMap" "android.util.ArrayMap"
	replace "Maps.newHashMap" "Maps.newArrayMap"
}


hashMapToArrayMap
