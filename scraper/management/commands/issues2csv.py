
"""
Deprecated. use scraper.github.API().issues() instead

"""

import sys
import csv
import argparse
import github  # to install, `pip install PyGithub`

from django.core.management.base import BaseCommand, CommandError
import settings


class DictWriter(csv.DictWriter):

    def _convert(self, value):
        if isinstance(value, basestring):
            return value.encode('utf8')
        return value

    def _convert3(self, value):
        # Python3 DictWriter is unicode-aware
        return value

    def __init__(self, *args, **kwargs):
        if sys.version_info > (3,):
            self._convert = self._convert3
        csv.DictWriter.__init__(self, *args, **kwargs)

    def writerow(self, row):
        for key, value in row.items():
            row[key] = self._convert(value)
        csv.DictWriter.writerow(self, row)


class Command(BaseCommand):
    help = 'Scrape issues of the specified repository from github'

    def add_arguments(self, parser):
        parser.add_argument('repo', help='repository name, <user>/<repo>')
        parser.add_argument('--include-body', action='store_true',
                            help='include issue body as the last column')
        parser.add_argument('-o', '--output', default="-",
                            type=argparse.FileType('w'),
                            help='Output filename, "-" or skip for stdout')

    def handle(self, *args, **options):

        # TODO: replace with local github API implementation
        g = github.Github(settings.SCRAPER_GITHUB_API_TOKEN)
        repo = g.get_repo(options['repo'])
        try:
            id = repo.id
        except github.GithubException:
            raise CommandError("Repository %s does not exist" % options['repo'])

        issues = repo.get_issues(state='all')

        columns = ['id', 'title', 'user', 'labels', 'state',
                   'created_at', 'updated_at', 'closed_at']
        if options['include_body']:
            columns += ['body']
        writer = DictWriter(options['output'], columns)
        writer.writeheader()

        # Response example:
        # https://api.github.com/repos/pandas-dev/pandas/issues?page=62
        for issue in issues:
            raw = issue._rawData  # to prevent resolving usernames into objects
            row = {
                'id': int(raw['id']),
                'title': raw['title'],
                'user': raw['user']['login'],
                'labels': ",".join(l['name'] for l in raw['labels']),
                'state': raw['state'],
                'created_at': raw['created_at'],
                'updated_at': raw['updated_at'],
                'closed_at': raw['closed_at'],
            }
            if options['include_body']:
                row['body'] = raw['body']
            writer.writerow(row)


