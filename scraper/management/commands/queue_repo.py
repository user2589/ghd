
import sys

from django.core.management.base import BaseCommand

from scraper import utils


class Command(BaseCommand):
    help = 'Scrape the specified repository(ies). \n' \
           '    Repo URL is accepted either as a first arguments or from the' \
           ' standard input. '

    def add_arguments(self, parser):
        parser.add_argument('url', nargs='?', help='repository url')

    def handle(self, *args, **options):
        if options['url']:
            urls = (options['url'],)
        else:
            urls = sys.stdin

        scheduled, total = utils.queue_repos(urls)

        return utils.format_res(scheduled, total)

