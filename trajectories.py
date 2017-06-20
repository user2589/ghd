#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import os
import argparse
import random
import csv

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import common
from scraper import utils

#     commits + SO + issues
#     same + developers
#     same + 2 classes of developers
# TODO: developers / window - try for several repositories?

# TODO: replace with automatic detection using so.utils.* and deployment ver
LAST_DEPLOYMENT = '2017-02'  # limited by StackOverflow dataset

# constants
# TODO: set up permanent so cache path
SO_STATS = pd.read_csv('so_stats.csv', index_col=0)
# CACHE_PATH = os.path.join(settings.DATASET_PATH, 'trajectories_cache')
COLUMNS = {'commits', 'new_issues', 'open_issues', 'so', 'time'}

# repository criteria
DATE_RANGE = ('2008-01', '2014-01')
CORR = pd.DataFrame()

trajectories_cache = common.cache('trajectories')


def _get_corr(language):
    fname = 'so_corr_%s.csv' % language.lower()
    if os.path.isfile(fname):
        return pd.read_csv(fname, index_col=0)
    from so import utils as so_utils
    df = so_utils.read_adjacency_matrix('so_adjacency.csv')
    counts = pd.DataFrame(np.diag(df.values), index=df.index)
    # some tags have zero counts, so we need to fillna()
    corr = (df.loc[language] / counts).fillna(0)
    corr.to_csv(fname, float_format="%.2g")
    return corr


@trajectories_cache()
def _get_data(package_name, repo_name, language=""):
    # type: (str, str, str) -> pd.DataFrame
    df = pd.concat([
        utils.commit_stats(repo_name),  # 'commits'
        utils.new_issues(repo_name),    # 'new_issues'
        utils.open_issues(repo_name),   # 'open_issues'
    ], axis=1)
    # not using r.r.language-pkgname because without r we don't know the tag
    lname = language and language + "-" + package_name
    so_name = lname if lname and lname in SO_STATS.index else package_name

    if so_name in SO_STATS.index:
        try:
            df['so'] = SO_STATS.loc[so_name, df.index]
        except KeyError:
            # two series don't intersect,
            # e.g. development was started after LAST_DEPLOYMENT
            pass
    if 'so' not in df:
        df['so'] = 0
    if df.empty:
        return df

    idx = [d.strftime("%Y-%m") for d in pd.date_range(
        period='M', start=min(df.index), end=min(max(df.index), LAST_DEPLOYMENT))]

    df = pd.concat([pd.DataFrame(index=idx), df], axis=1)
    df['open_issues'] = df['open_issues'].fillna(method='ffill')
    return df.loc[df.index <= LAST_DEPLOYMENT].fillna(0).astype(np.int)


def get_data(package_name, repo_name, columns, language,
             smoothing=6, threshold=0):
    data = _get_data(package_name, repo_name, language)

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
        description="TBA")
    parser.add_argument('-i', '--input', default="-",
                        type=argparse.FileType('r'),
                        help='File to use as input, empty or "-" for stdin')
    parser.add_argument('-o', '--output', default="",
                        help='Output filename.png')
    parser.add_argument('-x', default='commits', choices=COLUMNS,
                        help='X axis metric, commits by default')
    parser.add_argument('-y', default='new_issues', choices=COLUMNS,
                        help='Y axis metric, new issues by default')
    parser.add_argument('-z', nargs="?", choices=COLUMNS,
                        help='Z axis metric, not used by default')
    parser.add_argument('-t', '--title', type=str,
                        help='Plot title, default blank')
    parser.add_argument('-a', '--annotate', action='store_true',
                        help='Add annotations')
    parser.add_argument('--nc', action='store_true',
                        help='Use momentary values instead of cumulative sum.'
                             'Open issues are always non-cumulative.')
    parser.add_argument("-l", "--log", default='',
                        choices=('', 'x', 'y', 'z', 'all'),
                        help='Axes to apply log scale, none by default. '
                             'Log is never applied to time scale.')
    parser.add_argument("-d", "--dropout", default=0, type=float,
                        help='Share of projects to skip randomly, 0..1, '
                             '0 by default.')
    parser.add_argument('--threshold', default=0, type=int,
                        help='Lower bound of project activity to display, '
                             '0 by default')
    parser.add_argument('--figsize', default=12, type=int,
                        help='Figure size in inches, 12 by default')
    parser.add_argument('--marker', default=".", help='Matplotlib marker shape')
    parser.add_argument('--marker-size', default=10,
                        help='Matplotlib marker size, 10 by default')
    parser.add_argument('--language', default=None, type=str,
                        choices=('python', 'javascript'),
                        help='Language to check against on StackOverflow')
    args = parser.parse_args()

    lang = args.language
    CORR = _get_corr(lang)
    if args.log == 'all':
        args.log = 'xyz' if args.z else 'xy'

    fig_xsize = args.figsize if args.z else args.figsize * 3 // 2
    figure_params = {'figsize': (fig_xsize, args.figsize)}
    plot_params = {'marker': args.marker, 'ms': args.marker_size}
    fig = plt.figure(**figure_params)

    columns = {
        'x': args.x,
        'y': args.y,
        'z': args.z
    }

    if columns['z']:
        from mpl_toolkits.mplot3d import Axes3D

        ax = fig.add_subplot(111, projection='3d')
        ax.set_xlabel(columns['x'].replace("_", " "))
        ax.set_ylabel(columns['y'].replace("_", " "))
        ax.set_zlabel(columns['z'].replace("_", " "))
    else:
        plt.xlabel(columns['x'].replace("_", " "))
        plt.ylabel(columns['y'].replace("_", " "))
        ax = fig.add_subplot(111)

    if hasattr(args, 'title'):
        plt.title(args.title)

    draw_func = {
        'xyz': ax.loglog,
        'xy': ax.loglog,
        'x': ax.semilogx,
        'y': ax.semilogy,
        '': ax.plot
    }
    draw = draw_func["".join(c for c in args.log if columns[c] != "time")]
    reader = csv.DictReader(args.input)
    DEBUG = False
    if DEBUG:
        reader = [{'name': 'pandas', 'github_url': "pandas-dev/pandas"}]
        args.dropout = 0

    for record in reader:
        if not record['github_url']:
            continue

        data = get_data(record['name'], record['github_url'],
                        columns.values(), lang, threshold=args.threshold)

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

        for c in 'xyz':
            if columns[c] and (c in args.log or args.log == 'all') \
                    and columns[c] != 'time':
                data[columns[c]] += 1

        print("Processing", record['name'], record['github_url'])
        if columns['z']:
            ax.plot(data[columns['x']], -data[columns['y']], data[columns['z']],
                    **plot_params)
        else:
            draw(data[columns['x']], data[columns['y']], **plot_params)
        if args.annotate:
            xy = (data.iloc[-1][columns['x']], data.iloc[-1][columns['y']])
            ax.annotate(record['name'], xy=xy)
        plt.pause(0.0001)

    print("Done. Press any key to continue..")
    plt.waitforbuttonpress()

    if args.output:
        plt.savefig(args.output, bbox_inches='tight')
