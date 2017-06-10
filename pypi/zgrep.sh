#!/usr/bin/env bash

PATTERN=$1
FILE=$2

if [[ ! -e "${FILE}" ]]; then
    # file does not exist
    exit 2
elif [[ -d "${FILE}" ]]; then
    # this is a directory
    # suppress permissions denied messages
    grep -r -E -m1 -ohia "${PATTERN}" "${FILE}" 2> /dev/null | head -n 1
elif [[ "${FILE: -2}" == "gz" ]]; then
    # sometimes there are 2 matches per line, so even with -m1 we need head
    gunzip < "${FILE}" 2> /dev/null | grep -E -m1 -ohia "${PATTERN}" | head -n 1
    test $? -eq 0 && exit 0
    exit 1
elif [[ "${FILE: -3}" == "zip" ]]; then
#    zipgrep -m1 -oh ${PATTERN}${PACKAGE} $FILE
    flist=`unzip -Z1 "$FILE" | sed -e 's/\\\\/\\\\\\\\/g' `
    for i in ${flist}; do
        unzip -p-L "$FILE" "$i" 2> /dev/null | grep -E -m1 -ohi "${PATTERN}" | head -n 1
        test $? -eq 0 && exit 0
    done
    exit 1
fi
