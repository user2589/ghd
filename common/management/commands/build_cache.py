
from __future__ import print_function, unicode_literals

import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from common import threadpool
from common import utils
from scraper import utils as scraper

logging.basicConfig()
logger = logging.getLogger('ghd')


def collect_scraper(package, url):
    logger.info("Processing %s", package)
    scraper.commits(url)
    scraper.issues(url)
    scraper.open_issues(url)
    scraper.commit_stats(url)


def collect_common(ecosystem, metric):
    logger.info("Processing %s", metric)
    utils.clustering_data(ecosystem, metric)


class Command(BaseCommand):
    requires_system_checks = False
    help = "Download and store commit and issues data for all packages in " \
           "the specified ecosystem repositories."

    def add_arguments(self, parser):
        parser.add_argument('ecosystem', type=str,
                            help='Ecosystem to process, {pypi|npm}')
        num_tokens = len(getattr(settings, 'SCRAPER_GITHUB_API_TOKENS', []))
        parser.add_argument('-w', '--workers', default=1+num_tokens//2,
                            type=int, help='Number of workers to use')

    def handle(self, *args, **options):
        loglevel = 40 - 10*options['verbosity']
        logger.setLevel(loglevel)

        import sys
        sys.setrecursionlimit(20000)

        workers = min(max(options['workers'], 1), threadpool.CPU_COUNT * 2)
        tp = threadpool.ThreadPool(workers)

        urls = utils.package_urls(options['ecosystem'])
        for package, url in urls.iteritems():
            tp.submit(collect_scraper, package, url)

        for metric in utils.SUPPORTED_METRICS:
            tp.submit(collect_common, options['ecosystem'], metric)

        tp.shutdown()
