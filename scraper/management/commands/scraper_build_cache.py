
from __future__ import print_function, unicode_literals
import concurrent.futures

import logging
import argparse
import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from scraper import utils

logging.basicConfig()
logger = logging.getLogger('ghd.scraper')


def collect(package):
    logger.info("Processing %s %s", package['name'], package['github_url'])
    utils.open_issues(package['github_url'])
    utils.commit_stats(package['github_url'])


class MyExecutor(object):
    def submit(self, fn, *args):
        fn(*args)

    def shutdown(self):
        pass


class Command(BaseCommand):
    help = "Download and store commit and issues data for specified GitHub " \
           "repositories. Repositories are accepted as CSV records in the " \
           "format produced by ./manage.py pypi_packages_info"

    def add_arguments(self, parser):
        parser.add_argument('-i', '--input', default="-",
                            type=argparse.FileType('r'),
                            help='File to use as input, empty or "-" for stdin')
        num_tokens = len(getattr(settings, 'SCRAPER_GITHUB_API_TOKENS', []))
        parser.add_argument('-w', '--workers', default=1+num_tokens//2,
                            type=int, help='Number of workers to use')

    def handle(self, *args, **options):
        loglevel = 40 - 10*options['verbosity']
        logger.setLevel(20 if loglevel == 30 else loglevel)

        reader = csv.DictReader(options['input'])

        if options['workers'] > 1:
            executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=options['workers'])
        else:
            executor = MyExecutor()

        for package in reader:
            if not package['github_url']:
                continue
            executor.submit(collect, package)
