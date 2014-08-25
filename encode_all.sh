#!/bin/bash

#####################################################
#
#  use to decode all of the apk and jar in the system
#  note: unzip the zip first
#
#####################################################

APKTOOL="$PORT_ROOT/tools/apktool"
PRJROOT=$PWD

APKTOOL_IF_FRAMEWORK_DIR="$HOME/apktool/framework/"
METAINF="$PRJROOT/other/METAINF"

if [ $# -eq 0 ]
then
    echo "usage: decode_all.sh SYSTEM_DIR [OUT_DIR]"
    echo "eg: decode_all.sh system/framework"
#    file_path="."
else
    file_path=$1
fi

if [ $# -eq 1 ]
then
    out_path="."
else
    out_path=$2
fi

function updateApktoolYml()
{
    local apktoolYml=$1
    if [ -f $apktoolYml ];then
        echo "APKTOOL_IF_FRAMEWORK_DIR: $APKTOOL_IF_FRAMEWORK_DIR"
        for FILE in $(ls $APKTOOL_IF_FRAMEWORK_DIR | sort -r)
        do
           echo "FILE: "$FILE
           fileBaseName=`basename $FILE`
           resId=${fileBaseName%\.*}
           resIdMatch="- $resId"
           resIdMatch2="  - $resId"
           echo "update $apktoolYml with $resIdMatch"
           fileMatch=$((grep -n "ids:" $apktoolYml) | awk '{print $1}')
           if [ "$fileMatch" ];then
               lineNum=${fileMatch%%:*}
               echo "old lineNum: $lineNum"
               lineNum=`expr $lineNum`
               echo "new lineNum: $lineNum"
               sed -i "/$resIdMatch/d"  $apktoolYml
               sed -i "$lineNum a $resIdMatch"  $apktoolYml
               sed -i "s/$resIdMatch/$resIdMatch2/g" $apktoolYml
           fi      
        done
    else
        echo "ERROR: $apktoolYml doesn't exist!"
    fi
}

function processjarfile()
{
    if [ -d "$METAINF" ];then
        DIR=`dirname $1`
        FILENAME=`basename $1`
        if [ ! -f $1 ];then
            exit 0
        fi
        cd $DIR
        if [ -d Jar ];then
            rm -rf Jar
        fi
        mkdir -p Jar
        cp -rf "$METAINF"/* ./Jar
        jar xf $FILENAME  
        mv classes.dex ./Jar
        if [ ${FILENAME:0:9} != "framework" ];then
            rm -rf Jar/preloaded-classes
        fi
        jar cf $FILENAME -C Jar/ .
           rm -rf Jar
        cd -
    fi
}

find $file_path -name "build" | xargs rm -rf

find $file_path -name "AndroidManifest.xml" | grep -v "/framework/" > /tmp/apk_file
find $file_path -name "AndroidManifest.xml" | grep "/framework/" > /tmp/framework_apk_file
find $file_path -name "*.jar.out" > /tmp/jar_file

if [ ! -d $out_path ]
then
    mkdir -p $out_path
fi

cat /tmp/apk_file | while read line
do
    smaliDir=`dirname $line`
    updateApktoolYml "$smaliDir/apktool.yml"

    out_file=${smaliDir:${#file_path}:${#smaliDir}}
    out_file="$out_file.apk"

    echo "D: apktool b $smaliDir $out_path/$out_file"
    $APKTOOL b $smaliDir "$out_path/$out_file"
done

cat /tmp/framework_apk_file | while read line
do
    smaliDir=`dirname $line`

    out_file=${smaliDir:${#file_path}:${#smaliDir}}
    out_file="$out_file.apk"

    echo "D: apktool b $smaliDir $out_path/$out_file"
    $APKTOOL b $smaliDir "$out_path/$out_file"
done

cat /tmp/jar_file | while read smaliDir
do
    out_file=${smaliDir:${#file_path}:${#smaliDir}}
    len=`expr ${#out_file}-4`
    out_file=${out_file:0:$len}

    echo "D: apktool b $smaliDir $out_path/$out_file"
    $APKTOOL b $smaliDir "$out_path/$out_file"
    processjarfile "$out_path/$out_file"
done

rm /tmp/apk_file
rm /tmp/jar_file
rm /tmp/framework_apk_file
