
import logging
import importlib
from collections import defaultdict

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans

from common import decorators as d
from scraper import utils as scraper_utils

logger = logging.getLogger("ghd.common")


@d.fs_cache('')
def package_urls(ecosystem):
    # type: (str) -> pd.DataFrame
    """Get list of packages and their respective GitHub repositories"""
    assert ecosystem in ('pypi', 'npm'), "Ecosystem is not suppoerted"
    pkg = importlib.import_module(ecosystem + '.utils')
    return pd.Series(pkg.packages_info()).dropna().rename("github_url")


@d.fs_cache('common')
def first_contrib_log(ecosystem):
    # type: (str) -> pd.DataFrame
    """ Log of first contributions to a project by developers
    :param ecosystem: str:{pypi|npm}
    :return: pd.DataFrame with three columns:
        authored_date: str, full date (e.g. 2017-05-01 16:45:01Z)
        author: GitHub username of the author (unidentified authors are ignored)
        project: package name in the ecosystem
    """

    def gen():
        for package, url in package_urls(ecosystem).iteritems():
            logger.info("Processing %s (%s)", package, url)
            cs = scraper_utils.commits(
                url)[['author', 'authored_date']].dropna()
            cs = cs.loc[cs["authored_date"] > scraper_utils.MIN_DATE]
            if cs.empty:
                continue
            cs['project'] = package
            yield cs.groupby('author').min()

    # only ~13m & 500M RAM; cached less than 1s
    return pd.concat(gen(), axis=0).reset_index().sort_values("authored_date")


@d.fs_cache('common')
def first_contrib_dates(ecosystem):
    # type: (str) -> pd.Series
    # ~100 without caching
    return pd.Series({package: scraper_utils.commits(url)['authored_date'].min()
                      for package, url in package_urls(ecosystem).iteritems()})


@d.fs_cache('common')
def monthly_data(ecosystem, metric):
    # type: (str, str) -> pd.DataFrame
    # providers are expected to accept package github url
    # and return a single column dataframe
    providers = {
        'commits': scraper_utils.commit_stats,
        'contributors': scraper_utils.commit_users,
        'gini': scraper_utils.commit_gini,
        'q50': lambda repo: scraper_utils.contributions_quantile(repo, 0.5),
        'q70': lambda repo: scraper_utils.contributions_quantile(repo, 0.7),
        'issues': scraper_utils.new_issues,
        'non_dev_issues': scraper_utils.non_dev_issue_stats,
        'submitters': scraper_utils.submitters,
        # 'dependencies': None,
        # 'size': None,
        # 'connectivity': None,
        # 'backports': None,
    }
    assert metric in providers, "Metric is not supported"
    metric_provider = providers[metric]

    def gen():
        for package, url in package_urls(ecosystem).iteritems():
            logger.info("Processing %s", package)
            yield metric_provider(url).rename(package)

    return pd.concat(gen(), axis=1).T


@d.fs_cache('common')
def clustering_data(ecosystem, metric):
    def gen():
        start_dates = first_contrib_dates(ecosystem).dropna().str[:7]
        ms = monthly_data(ecosystem, metric)
        for package, start in start_dates.iteritems():
            logger.info("Processing %s", package)
            yield ms.loc[package, start:].reset_index(drop=True)

    return pd.concat(gen(), axis=1).T


def head(cdf, years):
    cdf.columns = [int(column) for column in cdf.columns]
    cdf = cdf.iloc[:, :years * 12 - 1]
    return cdf.loc[pd.notnull(cdf.iloc[:, -1])]


def cluster(cdf, n_clusters, years):
    c = KMeans(n_clusters=n_clusters)
    cdf = head(cdf, years)
    classes = c.fit_predict(cdf.values)
    predictions = pd.DataFrame(classes, index=cdf.index, columns=['class'])
    return predictions


def get_blank(cdf, classes=None):
    if classes is None:
        classes = pd.DataFrame(0, index=cdf.index, columns=['class'])
    return pd.DataFrame(np.array([
        cdf.values.ravel(),  # values
        np.tile(np.arange(len(cdf.columns)), len(cdf)),  # time
        np.repeat(np.arange(len(cdf)), len(cdf.columns)),  # unit
        np.repeat(classes.values, len(cdf.columns))  # condition
    ]).T, columns=['value', 'time', 'unit', 'condition'])


def tsplot(cdf, classes=None, title="", fname=None, figsize=None, **kwargs):
    # type: (pd.DataFrame, pd.DataFrame, str, str) -> None
    cdf = cdf.loc[classes.index]
    blank = get_blank(cdf, classes)
    fig = plt.figure(figsize=figsize)
    sns.tsplot(blank, value='value', time='time', unit='unit',
               condition='condition', **kwargs)
    if title:
        plt.title(title)
    plt.show()
    if fname:
        plt.savefig(fname, bbox_inches='tight')


@d.fs_cache('common')
def connectivity(ecosystem):
    def gen():
        clog = first_contrib_log(ecosystem)
        users = defaultdict(set)  # users[user] = set(projects participated)
        projects = defaultdict(set)  # projects[proj] = set(projects connected)
        stats = pd.Series(0, index=package_urls("pypi").index)

        month = scraper_utils.MIN_DATE

        for _, row in clog.iterrows():
            rmonth = row['authored_date'][:7]
            if rmonth < month:  # i.e. < scraper.MIN_DATE
                continue
            elif rmonth > month:
                yield stats.rename(month)
                month = rmonth
            for proj in users[row['author']]:
                stats[proj] += 1
            # this way project is connected to itself on its first commit
            # it will get useful later, otherwise just subtract 1
            users[row['author']].add(row['project'])
            projects[row['project']] |= users[row['author']]
            stats[row['project']] = len(projects[row['project']])
    # 1min
    return pd.concat(gen(), axis=1)
