
from __future__ import print_function, unicode_literals

import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from common import mapreduce
from common import utils as common
import scraper


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
        # -v 3: DEBUG, 2: INFO, 1: WARNING (default), 0: ERROR
        loglevel = 40 - 10 * options['verbosity']
        logging.basicConfig(level=loglevel)
        logger = logging.getLogger('ghd')

        num_workers = min(max(options['workers'], 1), 128)

        urls = common.package_urls(options['ecosystem'])

        def collect_scraper(package, url):
            logger.info(package)
            try:
                scraper.commits(url)
            except scraper.RepoDoesNotExist:
                logger.info("    %s: repo doesn't exist" % package)
                return
            scraper.issues(url)

        mapreduce.map(urls, collect_scraper, num_workers=num_workers)
