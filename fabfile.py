
from __future__ import print_function

import os

from fabric import api as fab

import settings

fab.env.hosts = settings.DEPLOY_HOSTS


def test():
    with fab.settings(warn_only=True):
        fab.local("python -m unittest common.test")
        fab.local("python -m doctest common/email.py")
        fab.local("python -m doctest common/utils.py")
        fab.local("python -m doctest common/mapreduce.py")
        fab.local("python -m doctest common/versions.py")
        fab.local("python -m doctest pypi/utils.py")
        fab.local("python -m doctest scraper/utils.py")


def clean():
    fab.local("find -type d -name __pycache__ -exec rm -rf {} +")


def install():
    # see requirements.txt for details
    reqs = (
        "libarchive-dev",
        "docker-compose",
        "yajl-tools"
    )
    for req in reqs:
        if os.system("dpkg -l %s > /dev/null 2> /dev/null" % req) > 0:
            fab.sudo("apt-get -y install " + req)
    fab.local("pip install --user -r requirements.txt")


def deploy():
    test()
    fab.local('git push')
    # TODO: check whether ghd folder exists
    fab.run('cd ghd && git pull')
    fab.put('settings.py', 'ghd/')
