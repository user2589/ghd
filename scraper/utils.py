
import os
import time

import pandas as pd
import numpy as np

import settings
from scraper import github
import common

# TODO: number of contributors with different windows
# TODO: percentage of core dev contributions with different windows

CACHE_PERIOD = getattr(settings, 'SCRAPER_CACHE_PERIOD', 3600 * 24 * 30 * 3)
CACHE_TYPES = {'raw', 'aggregate'}

github_api = github.API()

scraper_cache = common.cache('scraper', CACHE_TYPES, CACHE_PERIOD)


@scraper_cache('raw')
def commits(repo_name):
    # type: (str) -> pd.DataFrame
    return pd.DataFrame(
        github_api.repo_commits(repo_name),
        columns=['sha', 'author', 'author_name', 'author_email', 'authored_date',
                 'committed_date', 'parents', 'message', 'verified'])


@scraper_cache('aggregate')
def commit_stats(repo_name):
    # type: (str) -> pd.DataFrame
    """Commits aggregated by month"""
    column = 'authored_date'
    df = commits(repo_name)[[column]]
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
