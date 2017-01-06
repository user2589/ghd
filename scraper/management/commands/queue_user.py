
import sys
import logging

from django.core.management.base import BaseCommand, CommandError

from scraper import utils


class Command(BaseCommand):
    help = 'Schedule to scrape repositories of the specified GitHub user ' \
           '(i.e. all repos he/she contributed to, at least one commit).'

    def add_arguments(self, parser):
        parser.add_argument('login', nargs='?', help='GitHub username')

    def handle(self, *args, **options):
        logging.basicConfig()
        logger = logging.getLogger('ghd.scraper.utils')
        logger.setLevel(40 - 10*options['verbosity'])

        if options['login']:
            scheduled, total = utils.queue_user(options['login'])
        else:
            scheduled = total = 0
            for login in sys.stdin:
                l = login.strip()
                if l:
                    s, t = utils.queue_user(l)
                    scheduled += s
                    total += t

        return utils.format_res(scheduled, total)

