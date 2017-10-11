
from __future__ import unicode_literals

import logging
import importlib
import datetime
from collections import defaultdict

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans

from common import decorators as d
import scraper

logger = logging.getLogger("ghd")

SUPPORTED_ECOSYSTEMS = ('npm', 'pypi')

SUPPORTED_METRICS = {
    'commits': scraper.commit_stats,
    'contributors': scraper.commit_users,
    'gini': scraper.commit_gini,
    'q50': lambda repo: scraper.contributions_quantile(repo, 0.5),
    'q70': lambda repo: scraper.contributions_quantile(repo, 0.7),
    'q90': lambda repo: scraper.contributions_quantile(repo, 0.9),
    'issues': scraper.new_issues,
    'closed_issues': scraper.closed_issues,
    'non_dev_issues': scraper.non_dev_issue_stats,
    'submitters': scraper.submitters,
    'non_dev_submitters': scraper.non_dev_submitters,
    # 'dependencies': None,  # should come from pypi
    # 'size': None,
    # 'connectivity': None,
    # 'backports': None,
}


def _get_ecosystem(ecosystem):
    """Returns an imported module for the ecosystem.
    Basically, an importlib wrapper
    :param ecosystem: str:{pypi|npm}
    :return: module
    """
    assert ecosystem in SUPPORTED_ECOSYSTEMS, "Ecosystem is not supported"
    return importlib.import_module(ecosystem)


@d.fs_cache('')
def package_urls(ecosystem):
    # type: (str) -> pd.DataFrame
    """Get list of packages and their respective GitHub repositories"""
    es = _get_ecosystem(ecosystem)
    return pd.Series(es.packages_info()).dropna().rename("github_url")


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
            cs = scraper.commits(
                url)[['author', 'authored_date']].dropna()
            cs = cs.loc[cs["authored_date"] > scraper.MIN_DATE]
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
    return pd.Series({package: scraper.commits(url)['authored_date'].min()
                      for package, url in package_urls(ecosystem).iteritems()})


@d.fs_cache('common')
def monthly_data(ecosystem, metric):
    # type: (str, str) -> pd.DataFrame
    """
    :param ecosystem: str
    :param metric: str:
    :return: pd.DataFrame
    """
    # providers are expected to accept package github url
    # and return a single column dataframe
    assert metric in SUPPORTED_METRICS, "Metric is not supported"
    metric_provider = SUPPORTED_METRICS[metric]

    def gen():
        for package, url in package_urls(ecosystem).iteritems():
            logger.info("Processing %s", package)
            yield metric_provider(url).rename(package)

    return pd.concat(gen(), axis=1).T


@d.fs_cache('common')
def clustering_data(ecosystem, metric):
    # type: (str, str) -> pd.DataFrame
    """
    :param ecosystem: str
    :param metric: str:
    :return: pd.DataFrame
    """
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


def contributors(ecosystem, months=1):
    # type: (str) -> pd.DataFrame
    assert months > 0
    """ Get a historical list of developers contributing to ecosystem projects
    This function takes 7m20s for 54k PyPi projects @months=1, 23m20s@4
    :param ecosystem: {"pypi"|"npm"}
    :return: pd.DataFrame, index is projects, columns are months, cells are
        sets of stirng github usernames
    """
    # fcd = first_contrib_dates(ecosystem).dropna()
    start = "1998-01"  # fcd.min() starts at 1997-02
    columns = [d.strftime("%Y-%m")
               for d in pd.date_range(start, 'now', freq="M")][:-3]

    def gen():
        for package, repo in package_urls(ecosystem).iteritems():
            logger.info("Processing %s: %s", package, repo)
            s = scraper.commit_user_stats(repo).reset_index()[
                ['authored_date', 'author']].groupby('authored_date').agg(
                lambda df: set(df['author']))['author'].rename(
                package).reindex(columns)
            if months > 1:
                s = pd.Series(
                    (set().union(*[c for c in s[max(0, i - months + 1):i + 1]
                                 if c and pd.notnull(c)])
                     for i in range(len(columns))),
                    index=columns, name=package)
            yield s

    return pd.DataFrame(gen(), columns=columns)


@d.fs_cache('common')
def active_contributors(ecosystem, months=1):
    return count_dependencies(contributors(ecosystem, months))


@d.fs_cache('common')
def connectivity(ecosystem):
    """ Number of projects focal project is connected to via its developers
    :param ecosystem: {"pypi"|"npm"}
    :return: pd.DataFrame, index is projects, columns are months
    """
    def gen():
        clog = first_contrib_log(ecosystem)
        users = defaultdict(set)  # users[user] = set(projects participated)
        projects = defaultdict(set)  # projects[proj] = set(projects connected)
        stats = pd.Series(0, index=package_urls("pypi").index)

        month = scraper.MIN_DATE

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


def upstreams(ecosystem):
    # type: (str) -> pd.DataFrame
    # ~12s without caching
    es = _get_ecosystem(ecosystem)
    deps = es.deps_and_size().sort_values("date")
    deps['dependencies'] = deps['dependencies'].map(
        lambda x: set(x.split(",")) if x and pd.notnull(x) else set())

    idx = [d.strftime("%Y-%m")  # start is around 2005
           for d in pd.date_range(deps['date'].min(), 'now', freq="M")]

    df = deps.groupby([deps.index, deps['date'].str[:7]])['dependencies'].last()
    return df.unstack(level=-1).T.reindex(idx).fillna(method='ffill').T


def downstreams(uss):
    """ Basically, reversed upstreams
    :param uss: either ecosystem (pypi|npm) or an upstreams DataFrame
    :return: pd.DataFrame, df.loc[project, month] = set([*projects])
    """
    # ~35s without caching
    uss = upstreams(uss)

    def gen():
        for month in uss.columns:
            s = defaultdict(set)
            for pkg, dss in uss[month].iteritems():
                if dss and pd.notnull(dss):
                    # add package as downstream to each of upstreams
                    for ds in dss:
                        s[ds].add(pkg)
            yield pd.Series(s, name=month, index=uss.index)

    return pd.DataFrame(gen()).T


def cumulative_dependencies(deps):
    def gen():
        for month, dependencies in deps.T.iterrows():
            cumulative_upstreams = {}

            def traverse(pkg):
                if pkg not in cumulative_upstreams:
                    cumulative_upstreams[pkg] = set()  # prevent infinite loop
                    ds = dependencies[pkg]
                    if ds and pd.notnull(ds):
                        cumulative_upstreams[pkg] = set.union(
                            ds, *(traverse(d) for d in ds if d in dependencies))
                return cumulative_upstreams[pkg]

            yield pd.Series(dependencies.index, index=dependencies.index).map(
                traverse).rename(month)

    return pd.concat(gen(), axis=1)


def count_dependencies(df):
    # type: (pd.DataFrame) -> pd.DataFrame
    # takes around 20s for full pypi history
    return df.applymap(lambda s: len(s) if s and pd.notnull(s) else 0)


def _fcd(ecosystem, start_date):
    es = _get_ecosystem(ecosystem)
    fcd = first_contrib_dates(ecosystem).dropna().str[:7]
    fcd = fcd[fcd > start_date]
    deps = es.deps_and_size()
    # first_release_date
    frd = deps["date"].groupby("name").min().reindex(fcd.index).fillna("9999")
    # remove packages which were released before first commits
    # usually those are imports from other VCSes
    return fcd[fcd <= frd]  # drops 623 packages


@d.fs_cache('common')
def dead_projects(ecosystem):
    es = _get_ecosystem(ecosystem)
    deps = es.deps_and_size()
    commits = monthly_data(ecosystem, "commits")
    last_release = deps[['date']].groupby("name").max()
    death_date = pd.to_datetime(last_release['date'], format="%Y-%m-%d") + \
        datetime.timedelta(days=365)
    death_str = death_date.dt.strftime("%Y-%m-%d")

    dead = pd.DataFrame([(death_str <= month).rename(month) for month in commits.columns]).T
    sure_dead = (commits.T[::-1].rolling(
                 window=12, min_periods=1).max() <= 1)[::-1].T.astype(bool)
    dead.update(sure_dead)
    return dead


@d.fs_cache('common')
def monthly_dataset(ecosystem, start_date='2008'):
    # TODO: more descriptive name to distinguish from monthly_data
    fcd = _fcd(ecosystem, start_date)
    mddfs = {metric: monthly_data(ecosystem, metric).loc[:, start_date:]
             for metric in ("commits", "contributors", "gini", "q50", "q70",
                            "issues", "closed_issues", "submitters",
                            "non_dev_issues")}

    # definition of active: > 1 commit per month in a given year
    mddfs['dead'] = dead_projects(ecosystem).loc[:, start_date:]

    mddfs['connectivity'] = connectivity(ecosystem)
    _upstreams = upstreams(ecosystem).loc[
        mddfs['dead'].index, mddfs['dead'].columns]
    active_upstreams = _upstreams.where(~mddfs['dead'])
    mddfs['upstreams'] = count_dependencies(_upstreams)
    mddfs['c_upstreams'] = count_dependencies(
        cumulative_dependencies(_upstreams))
    mddfs['a_upstreams'] = count_dependencies(active_upstreams)
    mddfs['ac_upstreams'] = count_dependencies(
        cumulative_dependencies(active_upstreams))

    _downstreams = downstreams(ecosystem).loc[
        mddfs['dead'].index, mddfs['dead'].columns]
    active_downstreams = _downstreams.where(~mddfs['dead'])
    mddfs['downstreams'] = count_dependencies(_downstreams)
    mddfs['c_downstreams'] = count_dependencies(
        cumulative_dependencies(_downstreams))
    mddfs['a_downstreams'] = count_dependencies(active_downstreams)
    mddfs['ac_downstreams'] = count_dependencies(
        cumulative_dependencies(active_downstreams))

    def gen():
        for package, start in fcd.iteritems():
            logger.info("Processing %s", package)
            idx = mddfs["commits"].loc[package, start:].index
            df = pd.DataFrame({
                'project': package,
                'date': idx,
                'age': np.arange(len(idx))
            })
            for metric, mddf in mddfs.items():
                if package in mddf.index:
                    df[metric] = mddf.loc[package, idx].fillna(0).values
                else:  # upstream/downstream for packages without releases
                    df[metric] = 0
            yield df

    return pd.concat(gen()).reset_index(drop=True)


@d.fs_cache('common')
def survival_data(ecosystem, start_date="2008"):
    fcd = _fcd(ecosystem, start_date)
    md = monthly_dataset("pypi", start_date)

    window = 12  # right-censoring

    def gen():
        for project, _ in fcd.iteritems():
            logger.info("Processing %s", project)
            df = md.loc[md['project'] == project]
            if len(df) > window:
                df['dead'] = df['dead'].shift(-1).fillna(method='ffill').astype(int)
                df = df.iloc[:-window]
            else:
                continue
            dead = df.loc[df['dead'] > 0, ['dead']]
            if not dead.empty:
                df = df.loc[:dead.index[0]]
            for _, row in df.iterrows():
                yield row

    return pd.DataFrame(gen(), columns=md.columns)


def yearly_dataset(md):
    # DEPRECATED
    gc = md.drop('age', axis=1).groupby(['project', md['age'] // 12])
    yd = gc.mean()
    yd['observations'] = gc.agg({'project': 'count'})
    return yd.loc[yd['observations'] == 12].drop(
        'observations', axis=1).reset_index().set_index("project")
