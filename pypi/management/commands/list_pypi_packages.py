
from __future__ import print_function

import os
import csv
import argparse
import tempfile

from django.core.management.base import BaseCommand

import settings
from pypi import models
from pypi import utils


class Command(BaseCommand):
    help = "Download a list of PyPi packages and their properties in CSV format"

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output', default="-",
                            type=argparse.FileType('w'),
                            help='Output filename, "-" or skip for stdout')
        parser.add_argument('-s', '--save-path',
                            default=os.path.join(settings.DATASET_PATH, 'pypi'),
                            help='Save path, where to put downloaded files')

    def handle(self, *args, **options):
        tempdir = tempfile.mkdtemp()
        writer = csv.writer(options['output'])

        for package_name in utils.list_packages():
            writer.writerow([package_name])
            # p = utils.Package(package_name, tempdir=tempdir,
            #                   save_path=options.savepath)
