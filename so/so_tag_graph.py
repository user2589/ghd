#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import csv
import xml.sax
import argparse
# import networkx as nx  # 64Gb RAM is not enough to convert to pandas DF
import numpy as np
import pandas as pd

CACHE_PATH = ''


class SOHandler(xml.sax.ContentHandler):
    df = None  # adjanscency graph

    def __init__(self, tags):
        self.df = pd.DataFrame(0, columns=tags, index=tags)
        xml.sax.ContentHandler.__init__(self)

    def startElement(self, name, attrs):
        if name != 'row':
            return  # ignore all other tags

        if attrs.get('PostTypeId') == "1":  # ignore answers
            tags = [t.lstrip("<")
                    for t in attrs.get('Tags', "").split(">") if t]
            for t1 in tags:
                if not t1:
                    continue
                for t2 in tags:
                    if not t2:
                        continue
                    try:
                        self.df.ix[t1, t2] += 1
                    except KeyError:
                        sys.stderr.write("Question %s: unknown tag %s or %s \n" % (
                            attrs['Id'], t1, t2))


def get_tags(tagfile):
    tags = pd.read_csv(tagfile)['name']
    tags[len(tags)] = "nan"  # somehow it is not in the original tagset
    return tags


def get_adj_matrix(tagfile, infile):
    cache_fname = 'graph.csv'
    if os.path.exists(os.path.join(CACHE_PATH, cache_fname)):
        reader = csv.reader(open(cache_fname))
        names = reader.next()[1:]
        df = pd.DataFrame(0, dtype=np.float16, columns=names, index=names)
        for row in reader:
            tag = row[0]
            df.loc[tag] = [float(v) if v else 0 for v in row[1:]]
        return df
    # ~10 hours
    tags = get_tags(args.tagfile)  # less than a second
    sax_parser = SOHandler(tags)
    xml_parser = xml.sax.make_parser()
    xml_parser.setContentHandler(sax_parser)
    xml_parser.parse(args.input)

    df = sax_parser.df
    # df = df.div(np.diag(df), 'columns')
    df.to_csv(cache_fname, float_format="%g")
    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Build tag adjascency matrix. in CSV')

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

    df = get_adj_matrix(args.tagfile, args.input)
