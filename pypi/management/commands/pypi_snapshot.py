
import logging
import datetime

from django.core.management.base import BaseCommand, CommandError

from pypi import models
from pypi import utils


class Command(BaseCommand):
    help = 'Make a snapshot of PyPi data'

    def add_arguments(self, parser):
        parser.add_argument('repo', nargs='?',
                            help='Repository URL to override the queue')

    def handle(self, *args, **options):
        logger = logging.getLogger('ghd.pypi')
        logger.setLevel(40 - 10*options['verbosity'])

        packages = utils.list_packages()
        n = len(packages)
        for i, package_name in enumerate(packages):
            logger.debug('processing (%d/%d): %s', i+1, n, package_name)
            try:
                p = utils.Package(package_name)
            except utils.PackageDoesNotExist:
                # some deleted packages aren't removed from the list
                continue
            snapshot = models.Snapshot(
                package=package_name, info=p.info,
                date_accessed=datetime.datetime.utcnow()
            )
            snapshot.save()
        logger.info('Done')
