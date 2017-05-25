#!/usr/bin/env python

import os
import argparse
import logging
import requests
import urllib
import re

from ghd import settings


def download(path=settings.DATASET_PATH, force=False):
    r = requests.get("http://ghtorrent.org/downloads.html")
    urls = re.findall(
        "https://ghtstorage.blob.core.windows.net/downloads/"
        "mysql-20\d\d-\d\d-\d\d.tar.gz", r.text)
    url = max(urls)
    filename = os.path.join(path, url.rsplit("/", 1)[-1])
    if force or not os.path.isfile(filename):
        logging.info("Downloading %s.."%filename)
        urllib.urlretrieve(url, filename)
        logging.info("Downloading %s.." % filename)
    return filename


if __name__ == '__main__':
    download(".")
