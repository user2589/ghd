
from __future__ import print_function, unicode_literals

import logging
import argparse
import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from common import threadpool
from scraper import utils

logging.basicConfig()
logger = logging.getLogger('ghd.scraper')


def collect(package, url):
    logger.info("Processing %s %s", package, url)
    utils.open_issues(url)
    utils.commit_stats(url)


class Command(BaseCommand):
    requires_system_checks = False
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

        workers = min(max(options['workers'], 1), threadpool.CPU_COUNT * 2)
        tp = threadpool.ThreadPool(workers)

        for package_name in utils.list_packages():
            try:
                p = utils.Package(package_name, save_path=save_path)
            except utils.PackageDoesNotExist:
                # some deleted packages aren't removed from the list
                continue

            logger.info("Processing %s", package_name)
            tp.submit(target, p, callback=callback)

        tp.shutdown()


        if options['workers'] > 1:
            executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=options['workers'])
        else:
            executor = MyExecutor()

        for package in reader:
            if not package['github_url']:
                continue
            executor.submit(collect, package)
