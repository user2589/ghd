#!/usr/bin/env bash

ACTION=$1
ENGINE=$2
URL=$3
DATASET_PATH=$4

SOURCE_PATH=$(realpath $(dirname $0))

# change if you don't want to rely on Django db shell
# e.g.:   mysql --password=.. -u user -h host dbname
# or: su -c "psql" dbuser
DBSHELL="$(realpath $(dirname $0)/../manage.py) dbshell"
# This part supposed to cover default database, username and encoding
# e.g. you can do something like
#     echo "SET default_storage_engine=MYISAM " | $DBSHELL
# for Django dbshell, everything is handled by Django itself (by settings)T parckag
usage () {
  echo "Usage: $0 deploy db_engine archive_url save_path"
  echo "   or: $0 purge db_engine"
  echo
  echo "Deploy: download GHTorrent archive from the specified URL to the
  specified path, extract and deploy the dataset to the database."
  echo "Purge: delete all tables; does not delete existing dataset files."
  echo
  echo "db_engine: {mysql|postgresql}"
  echo "archive_url: URL to GHTorrent archive (full .tar.gz dump expected)"
  echo "save_path: directory to save the archive"
}

purge () {
    ${DBSHELL} < ${SOURCE_PATH}/drop.${ENGINE}.sql
}

set -e


# Preliminary checks - database engine
if [[ ! -f "schema.${ENGINE}.sql" ]]; then
    echo "DB engine '${ENGINE}' is not supported (yet)."
    echo "    Available options are: mysql, postgresql"
    usage
    exit 1
fi

case ${ACTION} in
purge)
    purge
    ;;
action)
    if [[ -z "${URL}" ]] || [[ -z "${DATASET_PATH}" ]]; then
        usage
        exit 1
    fi

    if [[ ! -d "${DATASET_PATH}" ]]; then
        echo "Error: the specified path does not exist or not a directory"
        usage
        exit 1
    fi

    cd ${DATASET_PATH}

    # don't download if file already exists
    BASENAME=$(basename ${URL})
    if [[ -f "${BASENAME}" ]]; then
        echo "Archive ${BASENAME} already exists; skipping download"
    else
        wget ${URL}
    fi

    # extract archive
    if [[ -d "${BASENAME::-7}" ]]; then
        echo "Folder ${BASENAME} already exists; skipping extraction"
    else
        # extracting - couple hours
        tar -zxvf ${BASENAME}
        # fix invalid timestamps ~5 hours
        sed -i "s/\"0000-00-00 00:00:00\"/\"1970-01-01 00:00:00\"/" *.csv
    fi

    # cleanup the database
    purge
    # create schema
    echo
    echo "Creating schema"
    ${DBSHELL} < ${SOURCE_PATH}/schema.${ENGINE}.sql

    # import data
    echo
    echo "Importing data - usually it takes ~30 hours"
    ${DBSHELL} < ${SOURCE_PATH}/import.${ENGINE}.sql

    # create indices
    echo
    echo "Creating indices"
    ${DBSHELL} < ${SOURCE_PATH}/indices.${ENGINE}.sql

    cd -
    ;;

*)
    echo "Action '${ACTION}' is not recognized"
    usage
    exit 1
    ;;
esac
