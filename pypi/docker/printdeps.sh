#!/usr/bin/env bash

cd /home/user/package

GETDEPS_PYTHON="
from __future__ import print_function
import setuptools
from distutils import core

def mock_setup(*args, **kwargs):
    print(','.join(kwargs.get('install_requires', [])))

setuptools.setup = mock_setup
core.setup = mock_setup

import setup
"

# some files have syntax errors, so better supress warnings
DEPS=`python -c "${GETDEPS_PYTHON}" 2>/dev/null`

if [[ $? -eq 0 ]]; then
    echo ${DEPS}
    exit 0
fi

DEPS=`python3 -c "${GETDEPS_PYTHON}" 2>/dev/null`

if [[ $? -eq 0 ]]; then
    echo ${DEPS}
    exit 0
fi
