
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from common import decorators as d
from scraper import utils as scraper_utils
from so import utils as so_utils

SO_STATS = so_utils.question_stats()


@d.fs_cache('trajectories')
def get_data(package_name, repo_name, language=""):
    # type: (str, str, str) -> pd.DataFrame
    commits = scraper_utils.commit_stats(repo_name)
    new_issues = scraper_utils.new_issues(repo_name)
    open_issues = scraper_utils.open_issues(repo_name)
    last_deployment = max(commits.index)
    if not new_issues.empty:
        last_deployment = min(last_deployment, max(new_issues.index))

    df = pd.concat([commits, new_issues, open_issues], axis=1)

    lname = language and language + "-" + package_name
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
    if df.empty:
        return df

    idx = [d.strftime("%Y-%m") for d in pd.date_range(
        period='M', start=min(df.index), end=min(max(df.index), last_deployment))]

    df = pd.concat([pd.DataFrame(index=idx), df], axis=1)
    df['open_issues'] = df['open_issues'].fillna(method='ffill')
    return df.loc[df.index <= last_deployment].fillna(0).astype(np.int)


class Plot(object):
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
