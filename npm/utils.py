#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
import urllib
import re

import ijson.backends.yajl2 as ijson

logger = logging.getLogger('ghd')


def _get_url(item):
    if not item:
        return ''
    if isinstance(item, list):
        item = item[0]
    if isinstance(item, str):
        return item
    return item.get('url', '')


def packages_info():
    url = 'https://skimdb.npmjs.com/registry/_all_docs?include_docs=true'
    fh = urllib.urlopen(url)
    packages = ijson.items(fh, 'rows.item')
    gh = re.compile("github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)")

    for package in packages:
        repo = _get_url(package['doc'].get('repository')) or \
               _get_url(package['doc'].get('homepage')) or \
               _get_url(package['doc'].get('bugs')) or str(package)
        if not repo:
            continue
        m = gh.search(repo)
        if not m:
            continue

        yield {
            'name': package['doc']['name'],
            'github_url': m.group(1)
        }
