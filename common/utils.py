
import logging
import importlib

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans

from common import decorators as d
from scraper import utils as scraper_utils

# from so import utils as so_utils
# SO_STATS = so_utils.question_stats()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghd.common")


@d.fs_cache('')
def package_urls(ecosystem):
    # type: (str, str, str) -> (str, str)
    """Get list of packages and their respective GitHub repositories"""
    assert ecosystem in ('pypi', 'npm'), "Ecosystem is not suppoerted"
    pkg = importlib.import_module(ecosystem + '.utils')
    return pd.DataFrame(pkg.packages_info(), columns=['name', 'github_url']
                        ).set_index('name').dropna()


@d.fs_cache('common')
def clustering_data(ecosystem, metric):
    providers = {
        'commits': scraper_utils.commit_stats,
        'contributors': scraper_utils.commit_users,
        'issues': scraper_utils.new_issues,
        'gini': scraper_utils.commit_gini,
        'q50': lambda repo: scraper_utils.contributions_quantile(repo, 0.5),
        'q70': lambda repo: scraper_utils.contributions_quantile(repo, 0.7),
        'non-overlap': scraper_utils.non_overlap,
    }
    assert metric in providers, "Metric is not supported"
    metric_provider = providers[metric]
    packages = package_urls(ecosystem)
    dates = pd.date_range(scraper_utils.MIN_DATE, 'now', freq='M')
    cdf = pd.DataFrame(index=packages.index,
                       columns=np.arange(len(dates)))
    for package, row in packages.iterrows():
        logger.info("Processing %s (%s)", package, row['github_url'])
        monthly_stats = metric_provider(row['github_url'])
        cdf.loc[row.name, :len(monthly_stats)-1] = monthly_stats.values.ravel()
    return cdf.dropna(how='all', axis=1)


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


def tsplot(cdf, classes=None, title="", fname=None, figsize=None, **kwargs):
    # type: (pd.DataFrame, pd.DataFrame, str, str) -> None
    if classes is None:
        classes = pd.DataFrame(0, index=cdf.index, columns=['class'])
    cdf = cdf.loc[classes.index]
    blank = pd.DataFrame(np.array([
        cdf.values.ravel(),  # values
        np.tile(np.arange(len(cdf.columns)), len(cdf)),  # time
        np.repeat(np.arange(len(cdf)), len(cdf.columns)),  # unit
        np.repeat(classes.values, len(cdf.columns))  # condition
    ]).T, columns=['value', 'time', 'unit', 'condition'])
    fig = plt.figure(figsize=figsize)
    sns.tsplot(blank, value='value', time='time', unit='unit',
               condition='condition', **kwargs)
    if title:
        plt.title(title)
    plt.show()
    if fname:
        plt.savefig(fname, bbox_inches='tight')


@d.fs_cache('trajectories')
def get_data(package_name, repo_name, language=""):
    # type: (str, str, str) -> pd.DataFrame
    """Deprecated function that was used for visualization of trajectories
    Now it is replaced by seabobrn tsplot capabilities and clusters"""
    commits = scraper_utils.commit_stats(repo_name)
    new_issues = scraper_utils.new_issues(repo_name)
    open_issues = scraper_utils.open_issues(repo_name)
    df = pd.concat([commits, new_issues, open_issues], axis=1)

    if len(commits) == 0:
        # it is possible that repo has only invalid commits (e.g. invalid date)
        # but has valid issues. In this case we need to truncate issues data
        return df.iloc[:0]

    last_deployment = max(commits.index)
    if not new_issues.empty:
        last_deployment = min(last_deployment, max(new_issues.index))

    lname = language and (language + "-" + package_name)
    so_name = lname if lname and lname in SO_STATS.index else package_name

    if so_name in SO_STATS.index:
        questions = SO_STATS.loc[so_name]
        try:
            df['so'] = questions
        except KeyError:
            # two series don't overlap,
            # e.g. development was started after last deployment
            pass
        else:
            last_deployment = min(last_deployment, max(questions.index))
    if 'so' not in df:
        df['so'] = 0

    idx = [d.strftime("%Y-%m") for d in pd.date_range(
        period='M', start=min(df.index), end=min(max(df.index), last_deployment))]

    df = pd.concat([pd.DataFrame(index=idx), df], axis=1)
    df['open_issues'] = df['open_issues'].fillna(method='ffill')
    return df.loc[df.index <= last_deployment].fillna(0).astype(np.int)


class Plot(object):
    """Helper object to visualize a trajectory. Deprecated in favor of tsplot"""
    def __init__(self, title, x, y, z=None,
                 figure_params=None, plot_defaults=None, log=''):
        # type: (str, str, str, str, dict, dict, str) -> None
        figure_params = figure_params or {}
        self.plot_defaults = plot_defaults or {}
        self.fig = plt.figure(**figure_params)
        if z:
            from mpl_toolkits.mplot3d import Axes3D
            self.ax = self.fig.add_subplot(111, projection='3d')
            self.ax.set_xlabel(x.replace("_", " "))
            self.ax.set_ylabel(y.replace("_", " "))
            self.ax.set_zlabel(z.replace("_", " "))
        else:
            plt.xlabel(x.replace("_", " "))
            plt.ylabel(y.replace("_", " "))
            self.ax = self.fig.add_subplot(111)

        [getattr(self.ax, 'set_'+s+'scale')('log') for s in log]

        if title:
            plt.title(title)

    def plot(self, x, y, z=None, annotation=None, delay=0.001, **plot_params):
        data = (x, y) if z is None else (x, y, z)
        params = self.plot_defaults
        params.update(plot_params)
        self.ax.plot(*data, **params)
        if annotation:
            xy = tuple(d[-1] for d in data)
            self.ax.annotate(annotation, xy=xy)
        plt.pause(delay)

    @staticmethod
    def save(fname):
        plt.savefig(fname, bbox_inches='tight')
