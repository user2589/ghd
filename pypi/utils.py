#!/usr/bin/env python

"""An abstraction of Python package repository API (PyPi API)."""
from __future__ import print_function
import operator

import os
import subprocess
import tempfile
import requests
import urllib
from xml.etree import ElementTree
import re
import json


PYPI_URL = "https://pypi.python.org"
PYTHON_VERSIONS = ['3.6', '3.5', '3.4', '3.3', '2.7']
# some packages haven't update in a while, so the older the better
DEFAULT_PYTHON = min(PYTHON_VERSIONS)

# TODO:
# Add method to match Python version constraints
# Check out what is available from pylint
# AST dependencies parsing
# monkeypatching of setuptools setup and Command
# monkeypatch distutils.core in the same way
# Docker processing


class PackageDoesNotExist(ValueError):
    pass


def satisfy(constraint, ver):
    """Check if the specified version matches the constraint.
    Constraints could be in one of forms:
        !=ver - not this version
        >=ver
    """
    operators = {
        '!=': operator.ne,
        '>=': operator.ge,
        '<=': operator.le
    }
    op, target = constraint[:2], constraint[2:]
    if op in operators:
        return operators[op](ver, target)

    return ver == target


def parse_constraints(cstring):
    """Parse PyPi requires_python string and return a list of constraints
    This function only uses major/minor version (i.e. 2.x or 3.x)
    Example of cstring: ">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*",
    """
    return


def python_version(cstring):
    """Return Python version that satisfies all the constraints"""
    if not cstring:
        return DEFAULT_PYTHON
    constraints = [".".join(c.split(".")[:2]) for c in cstring.split(",") if c]
    for ver in PYTHON_VERSIONS:
        if all(satisfy(constraint, ver) for constraint in constraints):
            return ver
    return DEFAULT_PYTHON


class Package(object):
    name = None  # package name
    path = None  # path of the file, used to find zgrep
    _save_path = None  # folder to save package files
    _tempdir = None  # path to a temprorary folder
    info = None  # stores cached package info
    raw_info = None  # text representation of info
    source = None  # info about package source download path and filename

    def __init__(self, name, save_path=None, tempdir=None):
        self.name = name
        self.path = os.path.dirname(__file__) or '.'
        self._tempdir = tempdir
        self._save_path = save_path
        try:
            r = self._request("pypi", self.name, "json")
        except IOError:
            raise PackageDoesNotExist("Package %s does not present on PyPi")

        self.info = r.text
        try:
            self.info = r.json()
        except ValueError:  # simplejson.scanner.JSONDecodeError is a subclass
            pass  # malformed json

        for f in self.info["urls"]:
            if f['python_version'] == 'source':
                self.source = f
                break

    @staticmethod
    def _request(*path):
        for i in range(3):
            try:
                r = requests.get("/".join((PYPI_URL,) + path), timeout=10)
            except requests.exceptions.Timeout:
                continue
            r.raise_for_status()
            return r

    @property
    def tempdir(self):
        """Lazy tempdir init"""
        if not self._tempdir:
            self._tempdir = tempfile.mkdtemp()
        return self._tempdir

    @property
    def save_path(self):
        return self._save_path or self.tempdir

    def download(self, filename=None):
        # we need this method to grep package content for github urls
        if filename and os.path.isfile(filename):
            return filename
        if not self.source:
            return None

        if not filename:
            filename = os.path.join(self.tempdir, self.source['filename'])

        if not os.path.isfile(filename):
            urllib.urlretrieve(self.source["url"], filename)
        return filename

    def __del__(self):
        if self._tempdir:
            os.unlink(self._tempdir)

    def _search(self, pattern):
        """Search for a pattern in package info and package content"""
        # TODO: Replace depsgrep with native zip/tgz support
        m = re.search(pattern, str(self.info))
        if m:
            return m.group()

        filename = self.download()
        if not filename:  # some packages don't have downloadable files
            return None

        try:
            output = subprocess.check_output(
                [os.path.join(self.path, "zgrep.sh"), pattern, filename])
        except subprocess.CalledProcessError:
            return None
        return output.strip() or None  # output could be empty

    def github_url(self):
        url = self._search("github\.com/[a-zA-Z0-9_-]+/" + self.name)
        return url and url[11:]  # return only username/repo

    def google_group(self):
        return self._search("groups\.google\.com/forum/#!forum/[a-zA-Z0-9_-]*")

    def releases(self, include_unstable=False):
        releases = sorted([
            (label, min(f['upload_time'][:10] for f in files))
            for label, files in self.info['releases'].items()
            if files],  # skip empty releases
            key=lambda r: r[1])  # sort by date
        if not include_unstable:
            releases = [(label, date)
                        for label, date in releases
                        if re.match("^\d+(\.\d+)*$", label)]
        # TODO: add capability to remove backports
        return releases

    def dependencies(self):
        """This is a dummy to extract dependencies from setup.py
        
        It is not robust because in many cases dependencies are either loaded
        from file (requirements.txt) or formed dynamically "mylib>%s" % min_ver
        """
        fname = self.download()
        if not fname:
            return []
        setup_py = subprocess.check_output(
            [os.path.join(self.path, "depsgrep.sh"), fname])
        m = re.search("\[.*\]", setup_py)
        if not m:
            return []
        try:
            requirements = json.loads(m.group().replace("'", '"'))
        except ValueError:
            return ['unintelligible']
        return requirements


def list_packages():
    tree = ElementTree.fromstring(Package._request("simple/").text)
    return [a.text for a in tree.iter('a')]

