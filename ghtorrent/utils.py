
from __future__ import unicode_literals

from collections import OrderedDict

from ghtorrent import models

try:
    LAST_DEPLOYMENT = models.Deployment.objects.latest('version').version[:7]
except models.Deployment.DoesNotExist:
    raise EnvironmentError("GHTorrent is not deployed")


def date_range(sequence):
    if isinstance(sequence, dict):
        keys = sequence.keys()
    else:
        keys = sequence

    if not keys:
        return []

    ymonth = min(keys)
    year, month = [int(c) for c in ymonth.split('-')]
    ymonths = []
    while True:
        ymonths.append(ymonth)
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        ymonth = "%04d-%02d" % (year, month)
        if ymonth >= LAST_DEPLOYMENT:
            return ymonths


class GitHubRepository(object):
    r = None

    def __init__(self, repo_name):
        try:
            user, repo = repo_name.split('/')
        except ValueError:
            raise ValueError("Repository name is expected in format: user/repo")

        try:
            self.r = models.Repository.objects.get(owner__login=user, name=repo)
        except models.Repository.DoesNotExist:
            raise ValueError("GitHub repository %s does not exist" % repo)

    @staticmethod
    def _query(manager):
        stats = dict(manager.values_list('month', 'num'))
        return OrderedDict((ymonth, stats.get(ymonth, 0))
                           for ymonth in date_range(stats))

    def commit_stats(self):
        return self._query(self.r.monthly_commits)

    def new_issues(self):
        return self._query(self.r.new_issues)

    def closed_issues(self):
        return self._query(self.r.closed_issues)
