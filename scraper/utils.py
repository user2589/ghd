
import pandas as pd
import numpy as np

from scraper import github
from common import decorators

# TODO: number of contributors with different windows
# TODO: percentage of core dev contributions with different windows

github_api = github.API()
scraper_cache = decorators.typed_fs_cache('scraper')


@scraper_cache('raw')
def commits(repo_name):
    # type: (str) -> pd.DataFrame
    return pd.DataFrame(
        github_api.repo_commits(repo_name),
        columns=['sha', 'author', 'author_name', 'author_email', 'authored_date',
                 'committed_date', 'parents'])  # , 'message', 'verified'])


@scraper_cache('aggregate')
def commit_stats(repo_name):
    # type: (str) -> pd.DataFrame
    """Commits aggregated by month"""
    column = 'authored_date'
    df = commits(repo_name)[[column]]
    # filter out first commits without date (1970-01-01)
    # Git was created in 2005 but we need some slack because of imported repos
    df = df.loc[df[column] > '1998']
    return df.groupby(df[column].str[:7]).count().rename(
        columns={column: 'commits'}).astype(np.int)


@scraper_cache('raw')
def issues(repo_name):
    # type: (str) -> pd.DataFrame
    return pd.DataFrame(
        github_api.repo_issues(repo_name),
        columns=['number', 'author', 'closed', 'created_at', 'updated_at',
                 'closed_at', 'title'])


@scraper_cache('aggregate')
def new_issues(repo_name):
    # type: (str) -> pd.DataFrame
    """New issues aggregated by month"""
    column = 'created_at'
    df = issues(repo_name)
    return df[[column]].groupby(df[column].str[:7]).count().rename(
        columns={column: 'new_issues'}).astype(np.int)


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
    closed = closed_issues.groupby(closed_issues['closed_issues'].str[:7]).count()
    new = new_issues(repo_name)
    df = pd.concat([closed, new], axis=1).fillna(0).cumsum()
    df['open_issues'] = df['new_issues'] - df['closed_issues']
    return df[['open_issues']].astype(np.int)
