
import os

from django.core.management.base import BaseCommand

import settings
from ghtorrent import models


class Command(BaseCommand):
    help = 'Deploy GHTorrent dataset to the database'

    def handle(self, *args, **options):
        engine = settings.DATABASES['default']['ENGINE'].rsplit(".", 1)[-1]
        models.Deployment.objects.all().delete()
        cmd = os.path.join(
            os.path.dirname(__file__), '..', '..', 'ghtorrent.sh')

        if os.system(" ".join([cmd, 'purge', engine])):
            models.Deployment.objects.all().delete()
            print("Done.")
