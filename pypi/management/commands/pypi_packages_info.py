
import csv
import argparse
import shutil

from django.core.management.base import BaseCommand

from pypi import utils


class Command(BaseCommand):
    help = 'Produce a CSV list of PyPi packages including their dependencies,' \
           'Github repositories, Google Groups and LOC size'

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output', default="-",
                            type=argparse.FileType('w'),
                            help='Output filename, "-" or skip for stdout')

    def handle(self, *args, **options):
        writer = csv.writer(options['output'])
        writer.writerow([
            'name', 'github_url', 'google_group', 'dependencies'
        ])

        # TODO: workers pool
        for package_name in utils.list_packages():
            try:
                p = utils.Package(package_name)
            except utils.PackageDoesNotExist:
                # some deleted packages aren't removed from the list
                continue

            writer.writerow([
                package_name,
                p.github_url,
                p.google_group,
                ",".join(p.dependencies)
                # p.size  # takes a lot of time to process
            ])
            options['output'].flush()
            if getattr(p, '_pkgdir', None):
                try:
                    # some archives have broken permissions, looks like tar bug
                    shutil.rmtree(p._pkgdir)
                except:
                    pass
