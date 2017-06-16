#!/usr/bin/env python

from __future__ import unicode_literals, print_function

import os
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    import django
    django.setup(set_prefix=False)

import argparse
import csv

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import settings
from ghtorrent import utils as ght_utils

#     commits + stackoverflow
#     commits + SO + issues
#     same + developers
#     same + 2 classes of developers
# TODO: developers / window - try for several repositories?

# quirk to sync up datasets
ght_utils.LAST_DEPLOYMENT = '2017-02'  # limited by StackOverflow dataset

# constants
SO_STATS = pd.read_csv('so_stats.csv', index_col=0)
CACHE_PATH = os.path.join(settings.DATASET_PATH, 'trajectories_cache')
COLUMNS = {'commits', 'new_issues', 'closed_issues', 'so', 'time'}

# repository criteria
LANGUAGE = None
DATE_RANGE = ('2008-01', '2014-01')
CORR = pd.DataFrame()


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


def _get_data(package_name, repo_name):
    user, repo = repo_name.split("/")
    cache_fname = os.path.join(CACHE_PATH, ".".join((user, repo, 'csv')))
    if os.path.isfile(cache_fname):
        if os.stat(cache_fname).st_size == 0:
            return None
        return pd.read_csv(cache_fname, index_col=0)

    try:
        r = ght_utils.GitHubRepository(repo_name)
    except ValueError:  # this repo is not in GHTorrent dataset
        open(cache_fname, b'a').close()
        return None

    df = pd.DataFrame()
    df['commits'] = pd.Series(r.commit_stats())
    df['new_issues'] = pd.Series(r.new_issues())
    df['closed_issues'] = pd.Series(r.closed_issues())
    # not using r.r.language-pkgname because without r we don't know the tag
    so_name = package_name
    if so_name in SO_STATS.index:
        try:
            df['so'] = SO_STATS.loc[so_name, df.index]
        except KeyError:  # two series don't intersect
            pass

    df = df.sort_index().fillna(0)
    df.to_csv(cache_fname)
    return df


def get_data(package_name, repo_name, columns, smoothing=6, threshold=100):
    data = _get_data(package_name, repo_name)

    # validation checks
    if data is None or len(data) == 0:
        return None

    if 'so' in columns and 'so' not in data:  # there is no such tag
        return None

    start_date = min(data.index)
    if start_date < DATE_RANGE[0] or start_date > DATE_RANGE[1]:
        return None

    if any(data[c].sum() < threshold for c in columns if c != 'time'):
        return None

    if 'so' in columns:
        # check if this tag is related to language
        # CORR might not be initialized
        if package_name in CORR.index and CORR.loc[package_name][0] < 0.3:
            return None

    return data.sort_index().rolling(
        min_periods=1, window=smoothing, center=False).mean()

if __name__ == "__main__":
    draw_func = {
        'all': plt.loglog,
        'x': plt.semilogx,
        'y': plt.semilogy,
        'none': plt.plot
    }

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
                        help='Use momentary values instead of cumulative sum')
    parser.add_argument("-l", "--log", default='all', choices=draw_func.keys(),
                        help='Axes to apply log scale, all by default')
    parser.add_argument('--threshold', default=100, type=int,
                        help='Lower bound of project activity to display')
    parser.add_argument('--figsize', default=12,
                        help='Figure size in inches, 12 by default')
    parser.add_argument('--marker', default=".", help='Matplotlib marker shape')
    parser.add_argument('--marker-size', default=10,
                        help='Matplotlib marker size, 10 by default')
    parser.add_argument('--language', default='python',
                        choices=('python', 'javascript'),
                        help='Language to check against on StackOverflow')
    args = parser.parse_args()

    LANGUAGE = args.language
    CORR = _get_corr(LANGUAGE)

    delay = 0.0001
    columns = {
        'x': args.x,
        'y': args.y,
    }
    if args.z:
        columns['z'] = args.z

    figure_params = {'figsize': (args.figsize, args.figsize)}
    plot_params = {'marker': args.marker, 'ms': args.marker_size}

    # TODO: 3D chart support
    fig = plt.figure(**figure_params)
    ax = fig.add_subplot(111)
    plt.xlabel(columns['x'].replace("_", " "))
    plt.ylabel(columns['y'].replace("_", " "))
    if hasattr(args, 'title'):
        plt.title(args.title)

    draw = draw_func[args.log]
    reader = csv.DictReader(args.input)

    for record in reader:
        if not record['github_url']:
            continue

        data = get_data(record['name'], record['github_url'],
                        columns.values(), threshold=args.threshold)

        if data is None:
            continue

        if not args.nc:
            data = data.cumsum()

        if 'time' in columns.values():
            data['time'] = np.arange(len(data))

        print("Processing", record['name'], record['github_url'])
        draw(data[columns['x']], data[columns['y']], **plot_params)
        if args.annotate:
            xy = (data.iloc[-1][columns['x']], data.iloc[-1][columns['y']])
            ax.annotate(record['name'], xy=xy)
        plt.pause(delay)

    if args.output:
        plt.savefig(args.output, bbox_inches='tight')
