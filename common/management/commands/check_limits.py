
from __future__ import print_function, unicode_literals

import datetime

from django.core.management.base import BaseCommand

import scraper


class Command(BaseCommand):
    requires_system_checks = False
    help = "Check limits on registered GitHub API keys"

    def handle(self, *args, **options):
        api = scraper.GitHubAPI()
        now = datetime.datetime.now()
        for key, (remaining, next_update) in api.check_limits().items():
            if next_update is None:
                renew = '..not going to happen'
            else:
                timediff = datetime.datetime.fromtimestamp(next_update) - now
                renew = "in %d minutes %d seconds" % divmod(timediff.seconds, 60)
            print("{0}: {1: >4} requests remaining, renew in {2}".format(
                  key, remaining, renew))
