#!/usr/bin/env python

from __future__ import print_function

import csv
import argparse
import urllib
import re
import json

from pprint import pprint

import ijson.backends.yajl2 as ijson
# import ijson

try:
    string_type = basestring
except NameError:
    string_type = str


def _get_url(item):
    if not item:
        return ''
    if isinstance(item, list):
        item = item[0]
    if isinstance(item, string_type):
        return item
    return item.get('url', '')


def npm_gen(fh = None):
    # url = 'https://skimdb.npmjs.com/registry/_all_docs?include_docs=true'
    # fh = urllib.urlopen(url)
    fh = open('/home/mvaliev/AppEngine/dataset/nodejs_skimdb.json')
    packages = ijson.items(fh, 'rows.item')
    gh = re.compile("github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)")

    for package in packages:
        try:
            # a bunch of fixes for malformed urls
            # TODO: add str(package) fallback
            repo = _get_url(package['doc'].get('repository')) or \
                   _get_url(package['doc'].get('homepage')) or \
                   _get_url(package['doc'].get('bugs')) or str(package)
            if not repo:
                continue
            m = gh.search(repo)
            if not m:
                continue
        except:
            print(repo, type(repo), m)
            pprint(package)
            raise
        yield {
            'name': package['doc']['name'],
            'github_url': m.group(1)
        }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Generate CSV with package names and github urls")
    parser.add_argument('-o', '--output', default="-",
                        type=argparse.FileType('w'),
                        help='Output filename, "-" or skip for stdout')
    args = parser.parse_args()

    fields = ['name', 'github_url']
    writer = csv.writer(args.output)
    writer.writerow(fields)

    for package in npm_gen():
        writer.writerow([package[f] for f in fields])
