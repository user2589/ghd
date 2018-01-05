#!/usr/bin/env python

from __future__ import print_function

import ijson.backends.yajl2 as ijson
import pandas as pd

import logging
import urllib
import json
from collections import defaultdict

import scraper
from common import decorators as d


try:  # Py3 compatibility - unicode_literals isn't enough
  basestring
except NameError:
  basestring = str

logger = logging.getLogger('ghd')
fs_cache = d.fs_cache('npm')


def _pkginfo_iterator():
    # url = 'https://skimdb.npmjs.com/registry/_all_docs?include_docs=true'
    # fh = urllib.urlopen(url)
    fh = open("../dataset/npm.cache/npm.json")
    return ijson.items(fh, 'rows.item')


def _get_field(item, field, default=None):
    """Retrieve a field from JSON structure

    >>> item = {'one': 1, 'two': [1], 'three': {}}
    >>> _get_field(item, 'one')
    1
    >>> _get_field(item, 'two')
    1
    >>> _get_field(item, 'three')
    {}
    >>> _get_field(item, 'four') is None
    True
    """
    if not item:
        return default
    if isinstance(item, list):
        return _get_field(item[0], field)
    if isinstance(item, basestring):
        return item
    return item.get(field, default)


def json_path(item, *path):
    # type: (dict, *str) -> object
    """Helper function to traverse JSON

    >>> a = {'doc': {'versions': {'0.1': {'time': '2018-01-01T00:00.00.00Z'}}}}
    >>> json_path(a, 'doc', 'versions', '0.1', 'time')
    "2018-01-01T00:00.00.00Z"
    >>> json_path(a, 'doc', 'times', '0.1', 'time') is None
    True
    """
    res = item
    for key in path:
        try:  # this way is faster and supports list indexes
            res = res[key]
        except (IndexError, KeyError):
            return None
    return res


@fs_cache
def packages_info():
    # type: () -> pd.DataFrame
    """ Get a bunch of information about npm packages
    This will return pd.DataFrame with package name as index and columns:
        - url: date of release, YYYY-MM-DD str
        - version: version of release, str
        - deps: dependencies, comma separated string
        - owners
    """

    def gen():
        logger = logging.getLogger("npm.utils.package_info")
        for package in _pkginfo_iterator():
            logger.info("Processing %s", package['key'])
            repo = _get_field(package['doc'].get('repository'), 'url') or \
                _get_field(package['doc'].get('homepage'), 'url') or \
                _get_field(package['doc'].get('bugs'), 'url') or str(package)

            m = repo and scraper.URL_PATTERN.search(repo)

            yield {
                'name': package['key'],
                'url': m and m.group(0),
                'author': _get_field(package['doc'].get('author', {}), 'email')
            }
    return pd.DataFrame(gen(), columns=('name', 'url', 'author')
                        ).set_index('name', drop=True)


@fs_cache
def dependencies():
    """ Get a bunch of information about npm packages
    This will return pd.DataFrame with package name as index and columns:
        - version: version of release, str
        - date: release date, ISO str
        - deps: names of dependencies, comma separated string
        - raw_dependencies: dependencies, JSON dict name: ver
    """

    def gen():
        logger = logging.getLogger("npm.utils.package_info")
        for package in _pkginfo_iterator():
            logger.info("Processing %s", package['key'])
            """ possible sources of release date:
            - ['doc']['time'][<ver>] - best source, sometimes missing
            - ['doc']['versions'][<ver>]['ctime|mtime']  # e.g. Graph
            - ['doc']['time']['modified|created'] # e.g. stack-component
            - ['doc']['ctime|mtime']  # e.g. Lingo
            - empty  # JSLint-commonJS
            """
            for version, release in package['doc'].get('versions', {}).items():
                deps = release.get('dependencies') or {}
                deps = {dep.decode("utf8"): ver
                        for dep, ver in deps.items()}
                time = json_path(package, 'doc', 'time', version) or \
                    json_path(release, 'ctime') or \
                    json_path(release, 'mtime') or \
                    json_path(package, 'doc', 'time', 'created') or \
                    json_path(package, 'doc', 'time', 'modified') or \
                    None

                yield {
                    'name': package['key'],
                    'version': version,
                    'date': time,
                    'deps': ",".join(deps.keys()),
                    'raw_dependencies': json.dumps(deps)
                }

    return pd.DataFrame(gen(), columns=(
        'name', 'version', 'date', "deps", "raw_dependencies")
                       ).sort_values(['name', 'date']).set_index('name', drop=True)
