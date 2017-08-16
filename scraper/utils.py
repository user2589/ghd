
import logging
from functools import wraps
from collections import defaultdict

import pandas as pd
import numpy as np

from scraper import github
from common import decorators

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
def _commits(repo_name):
    # type: (str) -> pd.DataFrame
    """
    convert old cache files:
    find -type f -name '*.csv' -exec rename 's/(?<=\/)commits\./_commits./' {} +
    """
    return pd.DataFrame(
        github_api.repo_commits(repo_name),
        columns=['sha', 'author', 'author_name', 'author_email', 'authored_date',
                 'committed_date', 'parents']).set_index('sha', drop=True)


@scraper_cache('commits')
def commits(repo_name, max_depth=30):
    # type: (str, int) -> pd.DataFrame
    """ Fix dates in original commits
    ~200ms overhead for 26k commits
    :param repo_name: str, "<owner_login>/<login>"
    :param max_depth: int, max number of steps to look forward/back
            to fix commit dates
    :return: pd.DataFrame with commits
    """
    cs = _commits(repo_name)

    dates = cs['authored_date'].to_dict()
    authors = cs['author'].to_dict()
    parents = defaultdict(set)
    children = defaultdict(set)

    for child, ps in cs['parents'].iteritems():
        if pd.notnull(ps):
            parents[child] = set(ps.split("\n"))
            for parent in parents[child]:
                children[parent].add(child)

    def forward_impact(sha, date, depth=0):
        # commit authors affected if child commit is assumed
        # to be submitted after parent
        res = {authors[sha]}
        if depth == max_depth:
            return res
        return res.union(
            *(forward_impact(c, date, depth + 1) for c in children[sha] if
              dates[c] < date))

    def move_forward(sha, date):
        if dates[sha] < date:
            dates[sha] = date
            [move_forward(c, date) for c in children[sha] if dates[c] < date]

    def backward_impact(sha, date, depth=0):
        # commit authors affected if parent commit is assumed
        # to be submitted before child
        res = {authors[sha]}
        if depth == max_depth:
            return res
        return res.union(
            *(backward_impact(p, date, depth + 1) for p in parents[sha] if
              dates[p] > date))

    def move_back(sha, date):
        if dates[sha] > date:
            dates[sha] = date
            [move_back(p, date) for p in parents[sha] if dates[p] > date]

    for sha, pts in parents.items():
        for p in pts:
            if dates[p] > dates[sha]:
                bi = len(backward_impact(sha, dates[sha]))
                fi = len(forward_impact(p, dates[p]))
                if bi > 5 and fi > 5:
                    # we only fix rather simple cases here, and this one is not
                    # usually high bi/fi is a result of a messed up rebase
                    continue
                elif bi > fi:
                    move_forward(sha, max(dates[p] for p in pts))
                else:
                    move_back(p, dates[sha])

    cs['authored_date'].update(pd.Series(dates))
    return cs.loc[cs['authored_date'] > MIN_DATE]


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
def non_dev_issues(repo_name):
    # type: (str) -> pd.DataFrame
    """Same as new_issues with subtracted issues authored by contributors"""
    cs = commits(repo_name)[['authored_date', 'author']]
    fc = cs.loc[pd.notnull(cs['author'])].groupby(
        'author').min()['authored_date']

    i = issues(repo_name)[['created_at', 'author']].sort_values('created_at')
    i['fc'] = i['author'].map(fc)
    return i.loc[~(i['fc'] < i['created_at']), ['author', 'created_at']]


@scraper_cache('aggregate', 2)
def issue_user_stats(repo_name):
    return user_stats(issues(repo_name), "created_at", "new_issues")


@scraper_cache('aggregate')
@zeropad(0)
def new_issues(repo_name):
    # type: (str) -> pd.Series
    """New issues aggregated by month"""
    return issue_user_stats(repo_name).groupby('created_at').sum()['new_issues']


@scraper_cache('aggregate')
@zeropad(0)
def submitters(repo_name):
    # type: (str) -> pd.Series
    """New issues aggregated by month"""
    return issue_user_stats(repo_name).groupby(
        'created_at').sum()["new_issues"].rename("submitters")


@scraper_cache('aggregate')
@zeropad(0)
def non_dev_issue_stats(repo_name):
    # type: (str) -> pd.Series
    """New issues aggregated by month"""
    i = non_dev_issues(repo_name)
    return i.groupby(i['created_at'].str[:7]).count()['created_at'].rename(
        "non_dev_issues")


@scraper_cache('aggregate')
def closed_issues(repo_name):
    # type: (str) -> pd.DataFrame
    """New issues aggregated by month"""
    df = issues(repo_name)
    closed = df.loc[df['closed'], 'closed_at'].astype(object)
    return _zeropad(closed.groupby(closed.str[:7]).count(),
                    start=df['created_at'].min())


@scraper_cache('aggregate')
def open_issues(repo_name):
    # type: (str) -> pd.DataFrame
    """Open issues aggregated by month"""
    submitted = new_issues(repo_name).cumsum()
    closed = closed_issues(repo_name).cumsum()
    res = submitted - closed
    return res.rename("open_issues")
