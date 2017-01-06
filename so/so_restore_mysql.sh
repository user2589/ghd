#!/usr/bin/env bash

mngr="$(dirname $0)../manage.py"

usage() {
  echo "Usage: $(basename $0) dump_dir
    Restore a database from CSV and SQL files in dump_dir"
}

if [ -z $1 ]; then
  usage
  exit 1
fi

shift $(expr $OPTIND - 1)
dumpDir=$1

if [ ! -e $dumpDir ]; then
  echo "Cannot find directory to restore from"
  exit 1
fi

# Convert to full path
dumpDir="`pwd`/$dumpDir"

# 0. Create db schema
echo "Creating the DB schema"
${mngr} migrate

# 1. Extract data from xml
for item in User Post Tag Vote; do
    litem=`echo  $item | tr '[:upper:]' '[:lower:]'`
    echo "Extracting ${litem}s.."
    { echo "COPY so_${litem} FROM STDIN CSV QUOTE '\"' DELIMITER ',' ESCAPE '\' HEADER;
      "; gunzip < ${dumpDir}/${item}s.xml.gz ${mngr} so_xml2csv } | ${mngr} dbshell
done


# 2. Restore CSV files - old MySQL version; replaced by Postgres COPY FROM
#for f in $dumpDir/*.csv ; do
#  table=`basename $f|cut -f1 -d'.'`
#  echo "`date` Restoring table $table"

  # since we're using MyISAM we don't care about disabling foreign keys
  # otherwise, you need to set global variable before doing mysqlimport
  # Note: use mysqlimport because LOAD DATA LOCAL does not support utf8 chars
#  mysqlimport --default-character-set=utf8 --fields-terminated-by=',' \
#              --fields-optionally-enclosed-by='\"' --lines-terminated-by='\n' \
#              --fields-escaped-by="\\" \
#              --local -u $user --password=$passwd $db $f || exit 1
#done

echo "Done"
