#!/bin/bash
CURR=$(pwd)
mkdir -p data
for SAMPLE in $(find ../../tpmscan-dataset -name 'detail' -exec dirname {} \;)
do
    cd "$SAMPLE/../"
    zip -r $CURR/data/$(basename $SAMPLE).zip $(basename $SAMPLE)
    cd $CURR
done
