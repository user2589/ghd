
import sys
import logging

from django.core.management.base import BaseCommand

from scraper import utils


class Command(BaseCommand):
    help = 'Scrape the specified repository(ies). \n' \
           '    Repo URL is accepted either as a first arguments or from the' \
           ' standard input. '

    def add_arguments(self, parser):
        parser.add_argument('url', nargs='?', help='repository url')

    def handle(self, *args, **options):
        logging.basicConfig()
        logger = logging.getLogger('ghd.scraper.utils')
        logger.setLevel(40 - 10*options['verbosity'])

        if options['url']:
            urls = (options['url'],)
        else:
            urls = sys.stdin

        repos, total = utils.create_repos(urls)

        return utils.format_res(len(repos), total)

