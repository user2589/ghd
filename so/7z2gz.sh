#!/usr/bin/env bash

# This file converts passed .7z archive into .gz
# It is created as a workaround for a libarchive bug preventing reading large
# archives https://github.com/libarchive/libarchive/issues/913
# So, we're converting .7z to gz and reading them with

# DEPENDENCIES
# 7z comes with p7zip-full
# sudo apt-get install p7zip-full

ARCHIVE_FULL_PATH=$1

ARCHIVE_PATH=$(dirname ${ARCHIVE_FULL_PATH})
ARCHIVE_FNAME=$(basename ${ARCHIVE_FULL_PATH})
# manual on parameter substitution:
# http://tldp.org/LDP/abs/html/parameter-substitution.html
BASENAME=${ARCHIVE_FNAME%.*}
FNAME=${BASENAME##*-}.xml
OUTFILE=${ARCHIVE_PATH}/${FNAME}.gz

7z e -so ${ARCHIVE_FULL_PATH} ${FNAME} 2> /dev/null | gzip > ${OUTFILE}

touch -d "$(date -R -r ${ARCHIVE_FULL_PATH})" ${OUTFILE}
# rm ${ARCHIVE_FULL_PATH}

echo $OUTFILE
