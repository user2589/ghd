
import logging
from functools import wraps

import pandas as pd
import numpy as np

from scraper import github
from common import decorators


MIN_DATE = "1998"
DEFAULT_USERNAME = "-"
github_api = github.API()
scraper_cache = decorators.typed_fs_cache('scraper')

logger = logging.getLogger("ghd.scraper")


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


def _zeropad(df, fill_value=0, start=None, pad=3):
    """Ensure monthly index on the passed df, fill in gaps with zeroes"""
    start = start or df.index.min()
    if pd.isnull(start):
        idx = []
    else:
        idx = [d.strftime("%Y-%m")
               for d in pd.date_range(start, 'now', freq="M")][:-pad]
    return df.reindex(idx, fill_value=fill_value)


def zeropad(fill_value):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return _zeropad(func(*args, **kwargs), fill_value=fill_value)
        return wrapper
    return decorator


def clean_email(raw_email):
    """Extract email from a full address. Example:
      'John Doe <jdoe+github@foo.com>' -> jdoe@foo.com"""
    email = raw_email.split("<", 1)[-1].split(">", 1)[0]
    try:
        uname, domain = email.split("@")
    except ValueError:
        raise ValueError("Invalid email")
    uname = uname.rsplit(" ", 1)[-1]
    domain = domain.split(" ", 1)[0]

    return "%s@%s" % (uname.split("+", 1)[0], domain)


@scraper_cache('raw')
def commits(repo_name):
    # type: (str) -> pd.DataFrame
    return pd.DataFrame(
        github_api.repo_commits(repo_name),
        columns=['sha', 'author', 'author_name', 'author_email', 'authored_date',
                 'committed_date', 'parents']).set_index('sha')


@scraper_cache('aggregate', 2)
def commit_user_stats(repo_name):
    # type: (str) -> pd.DataFrame
    stats = commits(repo_name)
    stats['author'] = stats['author'].fillna(DEFAULT_USERNAME)
    df = user_stats(stats, "authored_date", "commits")
    return df


@scraper_cache('aggregate')
@zeropad(0)
def commit_stats(repo_name):
    # type: (str) -> pd.DataFrame
    """Commits aggregated by month"""
    return commit_user_stats(repo_name).groupby(
        'authored_date').sum()["commits"]


@scraper_cache('aggregate')
@zeropad(0)
def commit_users(repo_name):
    # type: (str) -> pd.DataFrame
    """Number of contributors by month"""
    return commit_user_stats(repo_name).groupby(
        'authored_date').count()["commits"].rename("users")


@scraper_cache('aggregate')
@zeropad(np.nan)
def commit_gini(repo_name):
    # type: (str) -> pd.DataFrame
    return commit_user_stats(repo_name).groupby(
        "authored_date").aggregate(gini)['commits'].rename("gini")


@zeropad(0)
def contributions_quantile(repo_name, q):
    # type: (str, float) -> pd.DataFrame
    return quantile(commit_user_stats(repo_name),
                    "authored_date", q)["commits"].rename("q%g" % (q*100))


@scraper_cache('raw')
def issues(repo_name):
    # type: (str) -> pd.DataFrame
    return pd.DataFrame(
        github_api.repo_issues(repo_name),
        columns=['number', 'author', 'closed', 'created_at', 'updated_at',
                 'closed_at']).set_index('number', drop=True)


@scraper_cache('aggregate')
@zeropad(0)
def non_overlap(repo_name):
    """Same as new_issues with subtracted issues authored by contributors"""
    cs = commits(repo_name)[['authored_date', 'author']]
    cs = cs.loc[pd.notnull(cs['author'])].sort_values(by='authored_date').reset_index()

    if cs.empty:
        return new_issues(repo_name)

    iss = issues(repo_name).sort_values(by='created_at').reset_index()[['created_at', 'author']]
    contributors = set()
    i = 0

    iss['contributor'] = False

    for idx, row in iss.iterrows():
        while i < len(cs) and cs.ix[i, 'authored_date'] < row['created_at']:
            contributors.add(cs.ix[i, 'author'])
            i += 1
        if row['author'] in contributors:
            iss.loc[idx, 'contributor'] = True

    return iss[iss['contributor']].groupby(iss["created_at"].str[:7]).count(
        )[['contributor']].rename(columns={'contributor': "non_overlap"})


@scraper_cache('aggregate')
@zeropad(0)
def new_issues(repo_name):
    # type: (str) -> pd.Series
    """New issues aggregated by month"""
    return issue_user_stats(repo_name).groupby('created_at').sum()['new_issues']


    # type: (str) -> pd.DataFrame
    """New issues aggregated by month"""
    return issue_user_stats(repo_name).groupby('created_at').sum()


@scraper_cache('aggregate')
def open_issues(repo_name):
    # type: (str) -> pd.DataFrame
    """Open issues aggregated by month"""
    df = issues(repo_name)
    column = 'closed_at'
    closed_issues = df.loc[df['closed'], [column]].rename(
        columns={column: 'closed_issues'})
    if len(closed_issues) == 0:
        return pd.DataFrame(columns=['open_issues'])
    closed = _zeropad(
        closed_issues.groupby(closed_issues['closed_issues'].str[:7]).count())
    new = new_issues(repo_name)
    df = pd.concat([closed, new], axis=1).fillna(0).cumsum()
    df['open_issues'] = df['new_issues'] - df['closed_issues']
    return df[['open_issues']].astype(np.int)
