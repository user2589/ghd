
from django.core.management.base import BaseCommand, CommandError

from scraper import utils


class Command(BaseCommand):
    help = 'Scrape the specified GitHub user ' \
           '(i.e. all repos where he/she contributed at least one commit).'

    def add_arguments(self, parser):
        parser.add_argument('login',help='GitHub username')

    def handle(self, *args, **options):
        scheduled, total = utils.queue_user(options['login'])

        return utils.format_res(scheduled, total)

