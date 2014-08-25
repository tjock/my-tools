#!/bin/bash

FSTYPE=""
DEVICE=""
while [ 1 ]; do
    if [ $1 == "-f" ]; then
        FSTYPE=$2
    elif [ $1 == "-d" ];then
        DEVICE=$2
    else
        break
    fi
    shift
    shift
done

src=$1
target=$2

recovery_fstab=/etc/recovery.fstab
src_basename=`basename $src`

function getSystemFstab()
{
    recFstab=`mktemp -t recovery.XXX`
    echo "tmp: $recFstab"

    adb pull /etc/recovery.fstab $recFstab

    if [ "x$DEVICE" == "x" ];then
      DEVICE=$(awk '/\/system/{print $3}' $recFstab)
    fi

    if [ "x$FSTYPE" == "x" ];then
      FSTYPE=$(awk '/\/system/{print $2}' $recFstab)
    fi  
#    DEVICE=`adb shell cat $recovery_fstab | grep '^/system' | awk '{print $3}'`
#    FSTYPE=`adb shell cat $recovery_fstab | grep '^/system' | awk '{print $2}'`
#    rm $recFstab
}

function waitrecovery()
{
    while [ 1 ];
    do
        ret=`adb devices | grep recovery`
        if [ "x$ret" != "x" ];then
            echo "ret: $ret"
            break;
        fi
        sleep 1
    done
}


if [ -f $src ]; then
    echo "wait for adb ..."
    adb wait-for-device

    adb reboot recovery
    echo "reboot to recovery..."

    waitrecovery
	#adb wait-for-device

    getSystemFstab

    if [ "x$FSTYPE" != "x" ] && [ "x$DEVICE" != "x" ];then
        echo "begin mount -t $FSTYPE $DEVICE /system"
        adb shell mount -t $FSTYPE $DEVICE /system
        adb push $1 $2
        adb reboot
    else
        echo "error: can not get fstab in $recovery_fstab"
        exit 1
    fi
fi
