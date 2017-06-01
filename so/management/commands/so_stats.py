
import argparse
import logging

from django.core.management.base import BaseCommand

from so import utils


class Command(BaseCommand):
    help = "Monthly StackOverflow question stats by tags"

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output', default="-",
                            type=argparse.FileType('w'),
                            help='Output filename, "-" or skip for stdout')

    def handle(self, *args, **options):
        logging.basicConfig()
        logger = logging.getLogger('ghd.so')
        logger.setLevel(40 - 10*options['verbosity'])

        logger.warning("Note: it will take 4..5 hours to execute")

        utils.question_stats().to_csv(options['output'])
