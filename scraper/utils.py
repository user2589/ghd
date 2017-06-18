
import os
import time

import pandas as pd
import numpy as np

import settings
from scraper import github

# TODO: number of contributors with different windows
# TODO: percentage of core dev contributions with different windows

CACHE_PERIOD = getattr(settings, 'SCRAPER_CACHE_PERIOD', 3600 * 24 * 30 * 3)
CACHE_PATH = os.path.join(settings.DATASET_PATH, "scraper")
if not os.path.isdir(CACHE_PATH):
    os.mkdir(CACHE_PATH)
CACHE_TYPES = {'raw': None, 'aggregate': None}
for t in CACHE_TYPES:
    path = os.path.join(CACHE_PATH, t)
    if not os.path.isdir(path):
        os.mkdir(path)
    CACHE_TYPES[t] = path

github_api = github.API()


def scraper_cache(cache_type):
    assert cache_type in CACHE_TYPES

    def decorator(func):
        def wrapper(*args):
            cache_fname = ".".join([
                "_".join([arg.replace("/", ".") for arg in args]),
                func.__name__, "csv"])
            cache_fpath = os.path.join(CACHE_TYPES[cache_type], cache_fname)
            if os.path.isfile(cache_fpath):
                if time.time() - os.path.getmtime(cache_fpath) < CACHE_PERIOD:
                    return pd.read_csv(cache_fpath, index_col=0)

            df = func(*args)
            df.to_csv(cache_fpath)
            return df

        return wrapper
    return decorator


@scraper_cache('raw')
def commits(repo_name):
    return pd.DataFrame(
        github_api.repo_commits(repo_name),
        columns=['sha', 'author', 'author_name', 'author_email', 'authored_date',
                 'committed_date', 'parents', 'message', 'verified'])


@scraper_cache('aggregate')
def commit_stats(repo_name):
    """Commits aggregated by month"""
    column = 'authored_date'
    df = commits(repo_name)[[column]]
    return df.groupby(df[column].str[:7]).count().rename(
        columns={column: 'commits'}).astype(np.int)


@scraper_cache('raw')
def issues(repo_name):
    return pd.DataFrame(
        github_api.repo_issues(repo_name),
        columns=['number', 'author', 'closed', 'created_at', 'updated_at',
                 'closed_at', 'title'])


@scraper_cache('aggregate')
def new_issues(repo_name):
    """New issues aggregated by month"""
    column = 'created_at'
    df = issues(repo_name)
    return df[[column]].groupby(df[column].str[:7]).count().rename(
        columns={column: 'new_issues'}).astype(np.int)


@scraper_cache('aggregate')
def open_issues(repo_name):
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


