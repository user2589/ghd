
from __future__ import print_function, unicode_literals

import datetime

from django.core.management.base import BaseCommand
import pandas as pd

import scraper


class Command(BaseCommand):
    requires_system_checks = False
    help = "Check limits on registered GitHub API keys"

    def handle(self, *args, **options):
        api = scraper.GitHubAPI()
        now = datetime.datetime.now()
        df = pd.DataFrame(columns=("requests", "renews in", "key"))

        for key, (remaining, next_update) in api.check_limits().items():
            if next_update is None:
                renew = 'never'
            else:
                timediff = datetime.datetime.fromtimestamp(next_update) - now
                renew = "%dm%ds" % divmod(timediff.seconds, 60)

            df.loc[api.usernames[key]] = {
                'requests': remaining,
                'renews in': renew,
                'key': key
            }

        print(df)
