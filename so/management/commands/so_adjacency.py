
import argparse

from django.core.management.base import BaseCommand

from so import utils


class Command(BaseCommand):
    help = 'Produce adjacency matrix of StackOverflow tags'

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output', default="-",
                            type=argparse.FileType('w'),
                            help='Output filename, "-" or skip for stdout')

    def handle(self, *args, **options):
        utils.adjacency_matrix().to_csv(options['output'])

