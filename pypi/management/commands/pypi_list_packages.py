
from __future__ import print_function

import argparse

from django.core.management.base import BaseCommand

from pypi import utils


class Command(BaseCommand):
    requires_system_checks = False
    help = "Download a list of PyPi packages and their properties in CSV format"

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output', default="-",
                            type=argparse.FileType('w'),
                            help='Output filename, "-" or skip for stdout')

    def handle(self, *args, **options):
        output = options['output']
        output.write("\n".join(utils.list_packages()))
