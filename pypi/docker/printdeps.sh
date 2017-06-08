#!/usr/bin/env bash

cd /home/user/package

GETDEPS_PYTHON="
from __future__ import print_function, unicode_literals
import setuptools
from distutils import core

def fooprint(*args, **kwargs):
    pass

def fooinput(*args, **kwargs):
    return ''

# suppress occasional prints some developers put into setup.py
_print = print
print = fooprint
input = raw_input = fooinput

def mock_setup(*args, **kwargs):
    reqs = kwargs.get('install_requires', [])
    if isinstance(reqs, str):
        reqs = reqs.split('\n')
    elif isinstance(reqs, bytes):
        reqs = reqs.split(b'\n')
    _print(','.join(reqs))

setuptools.setup = mock_setup
core.setup = mock_setup

import setup
"
TIMEOUT="timeout --kill-after=5 --signal=9 30"

# some files have syntax errors, so better supress warnings
DEPS=`${TIMEOUT} python3 -c "${GETDEPS_PYTHON}" 2>/dev/null`

if [[ $? -eq 0 ]]; then
    echo ${DEPS}
    exit 0
fi

DEPS=`${TIMEOUT} python -c "${GETDEPS_PYTHON}" 2>/dev/null`

if [[ $? -eq 0 ]]; then
    echo ${DEPS}
    exit 0
fi
