#!/bin/bash

set -x

ARTIFACTS=$1
VERSION=$2
INITPREFIX=$3

BASE=initrd-base
BIN=$BASE/usr/bin
SBIN=$BASE/usr/sbin
LIB=$BASE/usr/lib
LIB64=$BASE/usr/lib64
DEV=$BASE/dev
SYS=$BASE/sys
PROC=$BASE/proc
ETC=$BASE/etc
BOOT=$BASE/boot

mkdir -p $BIN
mkdir -p $SBIN
mkdir -p $LIB
mkdir -p $LIB64
mkdir -p $DEV
mkdir -p $SYS
mkdir -p $PROC
mkdir -p $ETC
mkdir -p $BOOT

pushd $BASE > /dev/null 2>&1
ln -s usr/bin bin
ln -s usr/lib64 lib64
ln -s usr/lib lib
ln -s usr/sbin sbin
popd > /dev/null 2>&1

# Create necessary device nodes
mknod -m 640 $DEV/tty0    c 4 0
mknod -m 640 $DEV/tty1    c 4 1
mknod -m 640 $DEV/tty     c 5 0
mknod -m 640 $DEV/console c 5 1
mknod -m 644 $DEV/ptmx    c 5 2
mknod -m 664 $DEV/null    c 1 3
mknod -m 664 $DEV/zero    c 1 5
mknod -m 664 $DEV/random  c 1 8
mknod -m 664 $DEV/urandom c 1 9
mknod -m 664 $DEV/loop0   b 7 0
mknod -m 664 $DEV/loop1   b 7 1
mkdir -m 755 $DEV/pts
mknod -m 600 $DEV/pts/0   c 136 0
mknod -m 000 $DEV/pts/ptmx c 5 2
mknod -m 660 $DEV/ram0    b 1 1

# Stuff for initrd to work
cp $ARTIFACTS/initrd/$VERSION/bin/* $BIN
cp $ARTIFACTS/initrd/$VERSION/lib64/* $LIB64
cp $ARTIFACTS/initrd/${INITPREFIX}-init $BASE/
# Experimental tools
cp $ARTIFACTS/share/System.map-5.14.0-symbiote+ $BOOT/
cp $ARTIFACTS/all_releases/Symlib/libSym.so $LIB64
cp $ARTIFACTS/redis/$VERSION/redis-server $BIN
cp $ARTIFACTS/redis/$VERSION/dep_libs/* $LIB64
cp -R $ARTIFACTS/all_releases/Tools/shortcut $LIB
cp -R $ARTIFACTS/all_releases/Tools/bin/* $BIN

pushd $BASE > /dev/null 2>&1
find . | cpio -o --quiet -H newc | gzip -9 -n > $ARTIFACTS/initrd/${INITPREFIX}-redis.cpio.gz
popd > /dev/null 2>&1
rm -Rf $BASE
