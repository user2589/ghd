
from __future__ import print_function

import os
import requests
import urllib
import re

from django.core.management.base import BaseCommand

import settings
from ghtorrent import models

DATASET_PATH = getattr(settings, 'DATASET_PATH', '.')


def latest_link():
    r = requests.get("http://ghtorrent.org/downloads.html")
    r.raise_for_status()

    links = re.findall("https?://ghtstorage\.blob\.core\.windows\.net/"
                       "downloads/mysql-20\d\d-\d\d-\d\d\.tar\.gz", r.text)

    assert links, "GHTorrent page retrieved successfully, but no valid links " \
                  "were found. Please update this software."
    return max(links)


class Command(BaseCommand):
    help = 'Deploy GHTorrent dataset to the database'

    def handle(self, *args, **options):
        try:
            url = latest_link()
        except IOError:
            print("Can't reach GHTorrent page. "
                  "Please check your network connection")
            exit(1)

        latest_available = url[-17:-7]
        assert re.match("20\d\d-\d\d-\d\d", latest_available), \
            "Can't parse the archive date. Please update this software."

        latest_deployment = models.Deployment.objects.first('date')
        deployed_version = latest_deployment and latest_deployment.version

        if deployed_version < latest_available:
            print("New(er) version of the dataset is available (%s), "
                  "starting deployment" % latest_available)

            engine = settings.DATABASES['default']['ENGINE'].rsplit(".", 1)[-1]
            cmd = os.path.join(
                os.path.dirname(__file__), '..', '..', 'ghtorrent.sh')

            models.Deployment.objects.all().delete()
            if os.system(" ".join([cmd, 'deploy', engine, url, DATASET_PATH])):
                models.Deployment(version=latest_available).save()
                print("Done.")
            else:
                print("There was some problem deploying the dataset.")
        else:
            print("Deployed version (%s) is already up to date" %
                  deployed_version)
