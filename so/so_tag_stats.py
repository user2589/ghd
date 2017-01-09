#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import xml.sax
import argparse
from collections import defaultdict
import pandas as pd


class SOHandler(xml.sax.ContentHandler):
    df = None  # resulting dataframe
    processed = 0
    time = None
    month = None
    questions = {}  # questions[q.id] = [tag1, tag2, ...]
    askers = defaultdict(set)  # askers[tag] = set(user1, user2, ...)
    responders = defaultdict(set)
    month_askers = None
    month_responders = None

    def __init__(self, tagfile):
        # prepopulating tags speedups this script from 80h to 10
        tags = pd.read_csv(tagfile)['name']
        tags[len(tags)] = "nan"  # somehow it is not in the original tagset
        idx = pd.MultiIndex.from_product(
            [tags, [True, False], ['posts', 'users', 'new_users']],
            names=['tag', 'q', 'field'])
        columns = [str(m)[:7] for m in
                   pd.date_range('2008-07-1', periods=102, freq='M')]
        # field = {'posts', 'users', 'new_users'}
        self.df = pd.DataFrame(0, columns=columns, index=idx)
        self.time = time.time()
        xml.sax.ContentHandler.__init__(self)

    def startElement(self, name, attrs):
        if name != 'row':
            return  # ignore all other tags

        self.processed += 1
        month = attrs['CreationDate'][:7]
        if month > self.month:
            sec = int(time.time() - self.time)
            perf = self.processed / (sec + 1)
            sys.stderr.write(
                "{}: posts: {}, elapsed: {}s, posts per second: {}\n".format(
                    month, self.processed, sec, perf))
            self.month_askers = defaultdict(set)
            self.month_responders = defaultdict(set)
            self.month = month

        post_id = int(attrs['Id'])
        # 88723 records out of 33M records don't have OwnerId
        try:
            user = int(attrs.get('OwnerUserId'))
        except (ValueError, TypeError) as _:
            user = 0

        if attrs.get('PostTypeId') == "1":
            tags = [t.lstrip("<")
                    for t in attrs.get('Tags', "").split(">") if t]
            self.questions[post_id] = tags  # list is faster than set
            for tag in tags:
                self.df.loc[tag, True, 'posts'][month] += 1
                self.df.loc[tag, True, 'users'][month] += \
                    user not in self.month_askers[tag]
                self.df.loc[tag, True, 'new_users'][month] += \
                    user not in self.askers[tag]
                self.month_askers[tag].add(user)
                self.askers[tag].add(user)
        elif attrs.get('PostTypeId') == "2":  # rarely there are others, like 5
            parent = int(attrs['ParentId'])
            for tag in self.questions.get(parent, []):
                self.df.loc[tag, False, 'posts'][month] += 1
                self.df.loc[tag, False, 'users'][month] += \
                    user not in self.month_responders[tag]
                self.df.loc[tag, False, 'new_users'][month] += \
                    user not in self.responders[tag]
                self.month_responders[tag].add(user)
                self.responders[tag].add(user)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get monthly tag stats in CSV')

    parser.add_argument('input', default="-", nargs="?",
                        type=argparse.FileType('r'),
                        help='File to use as input, empty or "-" for stdin')
    parser.add_argument('-o', '--output', default="-",
                        type=argparse.FileType('w'),
                        help='Output filename, "-" or skip for stdout')
    parser.add_argument('--tagfile', default="tags.csv",
                        type=argparse.FileType('r'),
                        help='Tags CSV file produced by xml2csv')
    args = parser.parse_args()

    xml_parser = xml.sax.make_parser()
    sax_parser = SOHandler(args.tagfile)
    xml_parser.setContentHandler(sax_parser)
    xml_parser.parse(args.input)

    sax_parser.df.to_csv(args.output)
