#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import argparse
import random
import csv

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from common import utils
from so import utils as so_utils

#     commits + SO + issues
#     same + developers
#     same + 2 classes of developers
# TODO: developers / window - try for several repositories?

# constants
SO_STATS = so_utils.question_stats()
COLUMNS = {'commits', 'new_issues', 'open_issues', 'so', 'time'}

# repository criteria
DATE_RANGE = ('2008-01', '2014-01')
CORR = pd.DataFrame()


def get_data(package_name, repo_name, columns, language,
             smoothing=6, threshold=0):
    data = utils.get_data(package_name, repo_name, language)

    # validation checks
    if data is None or data.empty:
        return None

    start_date = min(data.index)
    if start_date < DATE_RANGE[0] or start_date > DATE_RANGE[1]:
        return None

    total = data.sum(axis=0)
    if any(total[c] < threshold for c in columns if c and c != 'time'):
        return None

    if 'so' in columns:
        # check if this tag is related to language
        # CORR might not be initialized
        if package_name in CORR.index and CORR.loc[package_name][0] < 0.3:
            return None

    # Detecting imports:
    # there exist a month where over 20% of issues were created
    if ('new_issues' in columns or 'open_issues' in columns) and \
            total['new_issues'] > 100 and \
            (data['new_issues'] > (total['new_issues'] * 0.4)).sum() > 0:
            return None

    return data.sort_index().rolling(
        min_periods=1, window=smoothing, center=False).mean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A script to visualize sustainability metrics")
    parser.add_argument('x', default='commits', choices=COLUMNS,
                        help='X axis metric, commits by default')
    parser.add_argument('y', default='new_issues', choices=COLUMNS,
                        help='Y axis metric, new issues by default')
    parser.add_argument('-i', '--input', default="-",
                        type=argparse.FileType('r'),
                        help='File to use as input, empty or "-" for stdin')
    parser.add_argument('-o', '--output', default="",
                        help='Output filename.png')
    parser.add_argument('-z', nargs="?", choices=COLUMNS,
                        help='Z axis metric, not used by default')
    parser.add_argument('-t', '--threshold', default=0, type=int,
                        help='Lower bound of project activity to display, '
                             '0 by default')
    parser.add_argument("-d", "--dropout", default=0, type=float,
                        help='Share of projects to skip randomly, [0..1), '
                             '0 by default.')
    parser.add_argument('-s', '--smoothing', default=6, type=int,
                        help='Smoothing window in month, 6 by default')
    parser.add_argument('--title', type=str,
                        help='Plot title, default blank')
    parser.add_argument("-l", "--log", default='',
                        help='Axes to apply log scale, none by default, eg. xy.'
                             ' Log is never applied to time scale.')
    parser.add_argument('-c', '--clusters', default="", nargs='?',
                        help='Pandas csv with numeric classes for coloring')
    parser.add_argument('-a', '--annotate', action='store_true',
                        help='Add annotations')
    parser.add_argument('--nc', action='store_true',
                        help='Use momentary values instead of cumulative sum.'
                             'Open issues are always non-cumulative.')
    parser.add_argument('--figsize', default=12, type=int,
                        help='Figure size in inches, 12 by default')
    parser.add_argument('--marker', default=".", help='Matplotlib marker shape')
    parser.add_argument('--marker-size', default=10,
                        help='Matplotlib marker size, 10 by default')
    parser.add_argument('--language', default=None, type=str,
                        choices=('python', 'javascript'),
                        help='Language to check against on StackOverflow')
    args = parser.parse_args()

    default_color = None
    if args.clusters:
        clusters = pd.read_csv(args.clusters, index_col=0)
        colors = {None: '', 0: 'r', 1: 'b'}

        def color(pkgname):
            if pkgname not in clusters.index:
                return default_color
            cls = clusters.loc[pkgname][0]
            if cls is None or np.isnan(cls):
                return default_color
            return "C%d" % cls
    else:
        def color(pkgname):
            return default_color

    lang = args.language
    if lang:
        CORR = so_utils.correlation(lang)
    columns = {'x': args.x, 'y': args.y, 'z': args.z}

    fig_xsize = args.figsize if args.z else args.figsize * 3 // 2
    figure_params = {'figsize': (fig_xsize, args.figsize)}
    plot_params = {'marker': args.marker, 'ms': args.marker_size}

    if args.log == 'all':
        args.log = 'xyz'
    args.log = "".join(c for c in args.log if columns[c] not in (None, 'time'))

    ax = utils.Plot(args.title, columns['x'], columns['y'], columns['z'],
                    figure_params, plot_params, log=args.log)

    reader = csv.DictReader(args.input)

    for record in reader:
        if args.clusters and record['name'] not in clusters.index:
            continue

        if not record['github_url']:
            continue

        data = get_data(record['name'], record['github_url'], columns.values(),
                        lang, args.smoothing, args.threshold)

        if data is None:
            continue

        if args.dropout > 0 and random.random() < args.dropout:
            continue

        if not args.nc:
            for c in columns.values():
                if c and c not in ('open_issues', 'time'):
                    data[c] = data[c].cumsum()

        if 'time' in columns.values():
            data['time'] = np.arange(len(data))

        for c in args.log:
            data[columns[c]] += 1

        c = color(record['name'])
        print("Processing", record['name'], record['github_url'])
        annotation = args.annotate and record['name']

        ax.plot(*(data[columns[c]] for c in 'xyz' if columns[c]),
                annotation=annotation,
                # c=colors[int(bool(record['downstream']))])
                c=c)

    print("Done. Press any key to continue..")
    plt.waitforbuttonpress()

    if args.output:
        ax.save(args.output)
