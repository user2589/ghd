
import csv
import argparse
import logging
import multiprocessing

from django.core.management.base import BaseCommand

import settings
from pypi import utils
from common import decorators
from common import threadpool

logging.basicConfig()
logger = logging.getLogger('ghd.scraper')
CPU_COUNT = multiprocessing.cpu_count()


class Command(BaseCommand):
    requires_system_checks = False
    help = 'TBD'

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output', default="-",
                            type=argparse.FileType('w'),
                            help='Output filename, "-" or skip for stdout')
        parser.add_argument('-w', '--workers', default=1, type=int,
                            help='Number of workers to use (1 by default)')

    def handle(self, *args, **options):
        loglevel = 40 - 10*options['verbosity']
        logger.setLevel(loglevel)

        writer = csv.DictWriter(
            options['output'],
            fieldnames=['name', 'version', 'date', 'dependencies', 'size'])
        save_path = decorators.mkdir(settings.DATASET_PATH, 'pypi')

        def target(p):
            return [{
                'name': p.name,
                'version': label,
                'date': date,
                'dependencies': ",".join(p.dependencies(label)),
                'size': p.size(label)
            } for label, date in p.releases()]

        def callback(rows):
            writer.writerows(rows)
            options['output'].flush()

        workers = min(max(options['workers'], 1), CPU_COUNT)
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
