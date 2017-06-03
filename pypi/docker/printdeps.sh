#!/usr/bin/env bash

cd /home/user/package

GETDEPS_PYTHON="
from __future__ import print_function
import setuptools
from distutils import core

def fooprint(*args, **kwargs):
    pass

# suppress occasional prints some developers put into setup.py
_print = print
print = fooprint

def mock_setup(*args, **kwargs):
    reqs = kwargs.get('install_requires', [])
    if not isinstance(reqs, list):
        reqs = reqs.split('\n')
    _print(','.join(reqs))

setuptools.setup = mock_setup
core.setup = mock_setup

import setup
"

# some files have syntax errors, so better supress warnings
DEPS=`python3 -c "${GETDEPS_PYTHON}" 2>/dev/null`

if [[ $? -eq 0 ]]; then
    echo ${DEPS}
    exit 0
fi

DEPS=`python -c "${GETDEPS_PYTHON}" 2>/dev/null`

if [[ $? -eq 0 ]]; then
    echo ${DEPS}
    exit 0
fi
