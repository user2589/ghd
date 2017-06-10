#!/usr/bin/env bash

DIR=$1
IMAGE=${2-"deps"}

if [[ ! -d "$DIR" ]]; then
    exit 1
fi

#NAME=${3-$(basename "${DIR}")}
# NAME is not used - some packages contain invalid symbols
# TODO: use name if it matches allowed pattern
#if [[ ! -z "${NAME}" ]]; then  # not used at this moment
#    NAME="--name \"pypi_${NAME%-*}\""
#fi

if [[ "$(docker images -q myimage:mytag 2> /dev/null)" == "" ]]; then
    BUILDDIR="$(dirname $0)/docker"
    DOCKERFILE="$BUILDDIR/${IMAGE}.dockerfile"
    if [[ ! -f "${DOCKERFILE}" ]]; then
        # echo "Docker file ${DOCKERFILE} is not found!"
        # echo "Usage: $(basename $0) volume_dir image_name"
        exit 1
    fi
    docker build -f "${DOCKERFILE}" -t ${IMAGE} "${BUILDDIR}" > /dev/null
fi

docker run --rm -t -v "${DIR}":/home/user/package:ro -m 512m ${IMAGE} 2> /dev/null
