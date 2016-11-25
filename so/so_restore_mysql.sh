#!/usr/bin/env bash

# defaults
user=""
passwd=""
host=""
db=""
engine="MyISAM"

usage()
{
  echo "Usage: $0 [-u dbuser ] [-p dbpasswd ] [-h dbhost] [-d database ] dump_dir"
  echo
  echo "Restore a database from CSV and SQL files in dump_dir"
  echo "    -u database user (default: $user)"
  echo "    -p database passwd (default: $passwd)"
  echo "    -h database host (default: $host)"
  echo "    -d database to restore to. Must exist. (default: $db)"
  echo "    -e db engine: MyISAM for fast import and querying speed"
  echo "                  InnoDB for normal operations (default: $engine)"
}

if [ -z $1 ]
then
  usage
  exit 1
fi

while getopts "u:p:h:d:e:" o
do
  case $o in
  u)  user=$OPTARG ;;
  p)  passwd=$OPTARG ;;
  h)  host=$OPTARG ;;
  d)  db=$OPTARG ;;
  e)  engine=$OPTARG ;;
  \?)     echo "Invalid option: -$OPTARG" >&2
    usage
    exit 1
    ;;
  esac
done

# Setup MySQL command line
if [ -z $passwd ]; then
  mysql="mysql -u $user -s -h $host -D $db"
else
  mysql="mysql -u $user --password=$passwd -s -h $host -D $db"
fi

shift $(expr $OPTIND - 1)
dumpDir=$1

if [ ! -e $dumpDir ]; then
  echo "Cannot find directory to restore from"
  exit 1
fi

# Convert to full path
dumpDir="`pwd`/$dumpDir"

if [ ! -e $dumpDir/so_schema.sql ]; then
  echo "Cannot find $dumpDir/schema.sql to create DB schema"
  exit 1
fi

# 0. Extract data from xml
echo "Extracting users.."
gunzip < Users.xml.gz | python3 so.py > so_users.csv
echo "Extracting tags.."
gunzip < Tags.xml.gz | python3 so.py > so_tag_names.csv
echo "Extracting posts.."
gunzip < Posts.xml.gz | python3 so.py > so_posts.csv
echo "Votes are deliberately ignored. Run update query manually if interested"
#echo "Extracting votes.."
#gunzip < Votes.xml.gz | python3 so.py > so_votes.csv

# 1. Create db schema
echo "`date` Creating the DB schema"
cat $dumpDir/schema.sql |
sed -e "s/\`ghtorrent\`/\`$db\`/" |
sed -e "s/InnoDB/$engine/"|
grep -v "^--" |
$mysql


# 2. Restore CSV files with disabled FK checks
for f in $dumpDir/*.csv ; do
  table=`basename $f|cut -f1 -d'.'`
  echo "`date` Restoring table $table"

  # since we're using MyISAM we don't care about disabling foreign keys
  # otherwise, you need to set global variable before doing mysqlimport
  # Note: use mysqlimport because LOAD DATA LOCAL does not support utf8 chars
  mysqlimport --default-character-set=utf8 --fields-terminated-by=',' \
              --fields-optionally-enclosed-by='\"' --lines-terminated-by='\n' \
              --fields-escaped-by="\\" \
              --local -u $user --password=$passwd $db $f || exit 1
done

# 3. Create indexes
if [ ! -e $dumpDir/indexes.sql ]; then
  echo "Cannot find $dumpDir/indexes.sql to create DB indexes"
  exit 1
fi

echo "`date` Creating indexes"
cat $dumpDir/indexes.sql |
sed -e "s/\`ghtorrent\`/\`$db\`/" |
grep -v "^--" |
while read idx; do
  echo "`date` $idx"
  echo $idx | $mysql || exit 1
done

#: ft=bash
