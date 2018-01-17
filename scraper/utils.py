
from __future__ import print_function

import numpy as np
import pandas as pd

from functools import wraps
import logging
import re

from common import decorators
from common import email
from scraper import github

""" First contrib date without MIN_DATE restriction:
> fcd = utils.first_contrib_dates("pypi").dropna()
> df = pd.DataFrame(fcd.rename("fcd"))
> df["url"] = utils.package_urls("pypi")
> df = df.dropna(axis=1).sort_values("fcd")
> df.groupby(df["fcd"].str[:4]).count()

> data = df.iloc[:400]
> def second_month(row):
>     cs = scraper_utils.commit_stats(row["url"])
>     return cs[cs>0].index[1]
> data["second_month"] = data.apply(second_month, axis=1)
> data.groupby(data["second_month"].str[:4]).count()

1970: 3, 1973: 1, 1974: 3, 1997+: 2, 2, 2, 9, 14, 29, 50, 45, 99, 118, ...
looking at their second month of contributions, it is:
nothing before 1997,       1997+: 2, 0, 1, 9, 12, 18, 50, 47, 77, 113,  


So, 1997 looks like a reasonable lower bound.
Only 7 projects (1 commit each) have such commits, so they are safe to ignore
"""

MIN_DATE = "1997"
# username to be used all unidentified users
DEFAULT_USERNAME = "-"

fs_cache = decorators.typed_fs_cache('scraper')

logger = logging.getLogger("ghd.scraper")

# mapping of providers to API objects
# so far it looks like GitHub covers over 99% of projects
PROVIDERS = {
    "github.com": github.GitHubAPI(),
    "bitbucket.org": None,
    "gitlab.org": None,
    "sourceforge.net": None,
}

"""
>>> URL_PATTERN.search("github.com/jaraco/jaraco.xkcd").group(0)
'github.com/jaraco/jaraco.xkcd'
>>> URL_PATTERN.search("bitbucket.org/abcd/efgh&klmn").group(0)
'bitbucket.org/abcd/efgh'
"""
URL_PATTERN = re.compile(
    "(github\.com|bitbucket\.org|gitlab\.com)/"
    "([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)")


def named_url_pattern(name):
    """ Return project-specific pattern
    This pattern must be consistent with URL_PATTERN
    So far it is only used by pypi.Package to search for URL in code
    """
    return "(github\.com|bitbucket\.org|gitlab\.com)/[a-zA-Z0-9_.-]+/" + name


def parse_url(url):
    # type: (str) -> (str, str)
    """Return provider and project id
    >>> parse_url("github.com/user/repo")
    ("github.com", "user/repo")
    >>> parse_url("bitbucket.org/user/repo")
    ("bitbucket.org", "user/repo")
    >>> parse_url("gitlab.com/user/repo")
    ("gitlab.com", "user/repo")
    >>> parse_url("A quick brown fox jumps over the lazy dog")
    (None, None)
    >>> parse_url(None)
    (None, None)
    """
    if url:
        m = URL_PATTERN.search(url)
        if m:
            return m.group(1), m.group(2)
    return None, None


def get_provider(url):
    provider_name, project_url = parse_url(url)
    provider = PROVIDERS.get(provider_name)
    if provider is None:
        raise NotImplementedError(
            "Provider %s is not supported (yet?)"%provider_name)
    return provider, project_url


def gini(x):
    # simplified version from https://github.com/oliviaguest/gini
    n = len(x) * 1.0
    return np.sort(x).dot(2 * np.arange(n) - n + 1) / (n * np.sum(x))


def quantile(df, column, q):
    # type: (pd.DataFrame, str, float) -> pd.DataFrame
    def agg(x):
        return sum(x.sort_values(ascending=False).cumsum() / x.sum() <= q)

    return df.groupby(column).aggregate(agg)


def user_stats(stats, date_field, aggregated_field):
    # type: (pd.DataFrame, str, str) -> pd.DataFrame
    """Helper function for internal use only
    Aggregates specified stats dataframe by month/users"""
    if stats.empty:
        # a dirty hack to allow further aggregation
        return pd.DataFrame(columns=[date_field, 'author', aggregated_field])
    return stats[['author']].groupby(
        [stats[date_field].str[:7], stats['author']]).count().rename(
        columns={'author': aggregated_field}
    ).astype(np.int)


def zeropad(df, fill_value=0):
    if pd.isnull(start):
        idx = []
    else:
        idx = [d.strftime("%Y-%m")
               for d in pd.date_range(start, 'now', freq="M")]
    return df.reindex(idx, fill_value=fill_value)


@fs_cache('raw')
def commits(repo_url):
    # type: (str) -> pd.DataFrame
    """
    convert old cache files:
    find -type f -name '*.csv' -exec rename 's/(?<=\/)commits\./_commits./' {} +
    """
    provider, project_url = get_provider(repo_url)
    return pd.DataFrame(
        provider.repo_commits(project_url),
        columns=['sha', 'author', 'author_name', 'author_email', 'authored_date',
                 'committed_date', 'parents']).set_index('sha', drop=True)


@fs_cache('aggregate', 2)
def commit_user_stats(repo_name):
    # type: (str) -> pd.DataFrame
    stats = commits(repo_name)
    stats['author'] = stats['author'].fillna(DEFAULT_USERNAME)
    df = user_stats(stats, "authored_date", "commits")
    return df


# @fs_cache('aggregate')
def commit_stats(repo_name):
    # type: (str) -> pd.DataFrame
    """Commits aggregated by month"""
    return commit_user_stats(repo_name).groupby(
        'authored_date').sum()["commits"]


# @fs_cache('aggregate')
def commit_users(repo_name):
    # type: (str) -> pd.DataFrame
    """Number of contributors by month"""
    return commit_user_stats(repo_name).groupby(
        'authored_date').count()["commits"].rename("users")


# @fs_cache('aggregate')
def commit_gini(repo_name):
    # type: (str) -> pd.DataFrame
    return commit_user_stats(repo_name).groupby(
        "authored_date").aggregate(gini)['commits'].rename("gini")


def contributions_quantile(repo_name, q):
    # type: (str, float) -> pd.DataFrame
    return quantile(commit_user_stats(repo_name),
                    "authored_date", q)["commits"].rename("q%g" % (q*100))


@fs_cache('raw')
def issues(repo_url):
    # type: (str) -> pd.DataFrame
    provider, project_url = get_provider(repo_url)
    return pd.DataFrame(
        provider.repo_issues(project_url),
        columns=['number', 'author', 'closed', 'created_at', 'updated_at',
                 'closed_at']).set_index('number', drop=True)


@fs_cache('aggregate')
def non_dev_issues(repo_name):
    # type: (str) -> pd.DataFrame
    """Same as new_issues with subtracted issues authored by contributors"""
    cs = commits(repo_name)[['authored_date', 'author']]
    fc = cs.loc[pd.notnull(cs['author'])].groupby(
        'author').min()['authored_date']

    i = issues(repo_name)[['created_at', 'author']].sort_values('created_at')
    i['fc'] = i['author'].map(fc)
    return i.loc[~(i['fc'] < i['created_at']), ['author', 'created_at']]


@fs_cache('aggregate', 2)
def issue_user_stats(repo_name):
    return user_stats(issues(repo_name), "created_at", "new_issues")


@fs_cache('aggregate', 2)
def non_dev_issue_user_stats(repo_name):
    return user_stats(non_dev_issues(repo_name), "created_at", "new_issues")


# @fs_cache('aggregate')
def new_issues(repo_name):
    # type: (str) -> pd.Series
    """New issues aggregated by month"""
    return issue_user_stats(repo_name).groupby('created_at').sum()['new_issues']


# @fs_cache('aggregate')
def non_dev_issue_stats(repo_name):
    # type: (str) -> pd.Series
    """Same as new_issues, not counting issues submitted by developers"""
    i = non_dev_issues(repo_name)
    return i.groupby(i['created_at'].str[:7]).count()['created_at'].rename(
        "non_dev_issues")


# @fs_cache('aggregate')
def submitters(repo_name):
    # type: (str) -> pd.Series
    """New issues aggregated by month"""
    return issue_user_stats(repo_name).groupby(
        'created_at').count()["new_issues"].rename("submitters")


# @fs_cache('aggregate')
def non_dev_submitters(repo_name):
    # type: (str) -> pd.Series
    """New issues aggregated by month"""
    return non_dev_issue_user_stats(repo_name).groupby(
        'created_at').count()["new_issues"].rename("non_dev_submitters")


@fs_cache('aggregate')
def closed_issues(repo_name):
    # type: (str) -> pd.DataFrame
    """New issues aggregated by month"""
    df = issues(repo_name)
    closed = df.loc[df['closed'], 'closed_at'].astype(object)
    return _zeropad(closed.groupby(closed.str[:7]).count(),
                    start=df['created_at'].min())


@fs_cache('aggregate')
def open_issues(repo_name):
    # type: (str) -> pd.DataFrame
    """Open issues aggregated by month"""
    submitted = new_issues(repo_name).cumsum()
    closed = closed_issues(repo_name).cumsum()
    res = submitted - closed
    return res.rename("open_issues")


@fs_cache('aggregate')
def domain_commit_stats(repo_name):
    cs = commits(repo_name).reset_index()[['sha', 'author_email']]
    cs['domain'] = cs['author_email'].map(email.domain)
    return cs[['domain', 'sha']].groupby('domain').count()['sha'].rename(
        'commits').sort_values(ascending=False)


# @fs_cache('aggregate')
def commercial_involvement(repo_name):
    cs = commits(repo_name)[['authored_date', 'author_email']]
    cs["commercial"] = email.is_commercial_bulk(cs["author_email"])
    stats = cs.groupby(cs['authored_date'].str[:7]).agg(
        {'authored_date': 'count', 'commercial': 'sum'}
    ).rename(columns={'authored_date': "commits"})
    return (stats["commercial"] / stats["commits"]).rename("commercial")


# @fs_cache('aggregate')
def university_involvement(repo_name):
    cs = commits(repo_name)[['authored_date', 'author_email']]
    cs["university"] = email.is_university_bulk(cs["author_email"])
    stats = cs.groupby(cs['authored_date'].str[:7]).agg(
        {'authored_date': 'count', 'university': 'sum'}
    ).rename(columns={'authored_date': "commits"})
    return (stats["university"] / stats["commits"]).rename("university")
