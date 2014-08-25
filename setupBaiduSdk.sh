#!/bin/bash

if [ "x$1" != "x" ];then
	PRJ_DIR=$1
else
	PRJ_DIR=$PWD
fi

PRJ_JAVA_LIB=$PRJ_DIR/out/target/common/obj/JAVA_LIBRARIES
PRJ_BAIDU_SDK=$PRJ_DIR/sdk_baidu_framework
PRJ_BAIDU_SDK_SOURCE=$PRJ_BAIDU_SDK/sources

if [ ! -d $PRJ_JAVA_LIB ];then
	echo "wrong project directory, please cd to the root of android project"
	#exit 1
fi

mkdir -p $PRJ_BAIDU_SDK_SOURCE

for framework in $(ls $PRJ_JAVA_LIB | egrep "framework|service|common|mediatek|telephony"); do
	if [ -f $PRJ_JAVA_LIB/$framework/classes-full-debug.jar ]; then
		jar_name=$(echo $framework | sed 's/_intermediates/\.jar/g')
		echo "add $jar_name.jar for baidu's sdk"
		cp $PRJ_JAVA_LIB/$framework/classes-full-debug.jar $PRJ_BAIDU_SDK/$jar_name
	fi
done

cp $PRJ_DIR/frameworks/base/core/java/* $PRJ_BAIDU_SDK_SOURCE -rf
cp $PRJ_DIR/frameworks/base/services/java/* $PRJ_BAIDU_SDK_SOURCE -rf
cp $PRJ_DIR/baidu/frameworks/base/core/java/* $PRJ_BAIDU_SDK_SOURCE -rf

find $PRJ_BAIDU_SDK_SOURCE -name "*.mk" -type f | xargs rm -f
