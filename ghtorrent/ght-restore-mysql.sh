#!/usr/bin/env bash

mngr="$(dirname $0)../manage.py"
dbshell="${mngr} dbshell"

usage()
{
  echo "Usage: $0 dump_dir"
  echo
  echo "Restore a database from CSV and SQL files in dump_dir"
}

if [ -z $1 ]
then
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

if [ ! -e $dumpDir/schema.sql ]; then
  echo "Cannot find $dumpDir/schema.sql to create DB schema"
  exit 1
fi

# 1. Create db schema
echo "`date` Creating the DB schema"
${mngr} migrate

# 2. Restore CSV files
for f in "commits.csv" "projects.csv" "users.csv" ; do
  table=`basename $f|cut -f1 -d'.'`
  echo "`date` Restoring table $table"

  # we need it for quite a few tables
  sed -i "s/0000-00-00 00:00:00/1971-01-01 00:00:00/" "$f"

  if [ "$table" = "projects" ]; then
    sed -i "s/https:\/\/api\.github\.com\/repos\///" "$f"
    sed -i "s/https:\/\/api\.\/repos\///" "$f"
  fi

  # sed  expression added to fix invalid dates in the data files
  echo "SET foreign_key_checks = 0; LOAD DATA LOCAL INFILE '$f'
        INTO TABLE $table CHARACTER SET UTF8
        FIELDS TERMINATED BY ','
        OPTIONALLY ENCLOSED BY '\"' LINES TERMINATED BY '\n' " |
  $dbshell || exit 1
done

# 3. Create indexes
if [ ! -e $dumpDir/indexes.sql ]; then
  echo "Cannot find $dumpDir/indexes.sql to create DB indexes"
  exit 1
fi

echo "`date` Creating indexes"
cat $dumpDir/indexes.sql |
sed -e "s/\`ghtorrent\`//" |
grep -v "^--" |
while read idx; do
  echo "`date` $idx"
  echo $idx | $dbshell || exit 1
done
