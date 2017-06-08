#!/usr/bin/env python

"""An abstraction of Python package repository API (PyPi API)."""
from __future__ import print_function

import os
import sys
import subprocess
import tempfile
import requests
from xml.etree import ElementTree
import re
import shutil

# TODO: .whl support
# - this is a zip format
# - does not require sandbox
# - need to extract completely (internal path is unknown)
# - dependencies are in <something>.dist-info/metadata.json
#   .run_requires.item.requires: list

PY3 = sys.version_info[0] > 2
if PY3:
    from urllib.request import urlretrieve  # Python3
else:
    from urllib import urlretrieve  # Python2

SAVE_PATH = None
try:
    import settings
    if hasattr(settings, 'DATASET_PATH'):
        SAVE_PATH = os.path.join(settings.DATASET_PATH, 'pypi')
except ImportError:
    pass

PYPI_URL = "https://pypi.python.org"
_PATH = os.path.dirname(__file__) or '.'


class PackageDoesNotExist(ValueError):
    pass


def cache(key):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            value = getattr(self, key, None)
            if value is None:
                value = func(self, *args, **kwargs)
                setattr(self, key, value)
            return value
        return wrapper
    return decorator


def _shell(cmd, *args, **kwargs):
    if kwargs.get('local', True):
        cmd = os.path.join(_PATH, cmd)
    output = subprocess.check_output((cmd,) + args)
    if PY3:
        output = output.decode('utf8')
    return output


def dependencies(package_path):
    # package_path could be either folder or file
    deps = _shell("docker.sh", package_path)
    depslist = [re.split("[^\w._-]", d.strip(), 1)[0].lower()
                for d in deps.strip().split(",") if d]
    return [d for d in depslist if d]


def loc_size(package_dir):
    pylint_out = _shell("pylint", "--py3k", package_dir, local=False)
    m = re.search("\|code\s*\|([\\s\\d]+?)\|", pylint_out)
    match = m and m.group(1).strip()
    if not match:
        return 0
    return int(match)


class Package(object):
    name = None  # package name
    path = None  # path of the file, used to find zgrep
    _tempdir = None  # path to a temprorary folder
    _tempdir_created = False
    info = None  # stores cached package info
    raw_info = None  # text representation of info
    source = None  # info about package source download path and filename
    # supported formats
    unzip = 'unzip -qq "%(fname)s" "%(bname)s/*" -d "%(dir)s" 2>/dev/null'
    untgz = 'tar -C "%(dir)s" -zxf "%(fname)s" "%(bname)s" 2>/dev/null'
    formats = {
        '.zip': unzip,
        '.tar.gz': untgz,
        '.tgz': untgz,
        '.tar.bz2': untgz,
    }

    def __init__(self, name, save_path=SAVE_PATH):
        self.name = name.lower()
        self.path = os.path.dirname(__file__) or '.'
        self._tempdir = save_path
        try:
            r = self._request("pypi", self.name, "json")
        except IOError:
            raise PackageDoesNotExist("Package %s does not exist on PyPi" % name)

        self.info = r.text
        try:
            self.info = r.json()
        except ValueError:  # simplejson.scanner.JSONDecodeError is a subclass
            pass  # malformed json

        for f in self.info["urls"]:
            if f['python_version'] == 'source' and \
                    any(f["url"].endswith(ext) for ext in self.formats):
                self.source = f
                break

    def __del__(self):
        if self._tempdir_created:
            shutil.rmtree(self._tempdir)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<PyPi package: %s>" % self.name

    @staticmethod
    def _request(*path):
        for i in range(3):
            try:
                r = requests.get("/".join((PYPI_URL,) + path), timeout=10)
            except requests.exceptions.Timeout:
                continue
            r.raise_for_status()
            return r
        raise IOError("Failed to reach PyPi. Check your Internet connection.")

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

    @property
    def tempdir(self):
        """Lazy tempdir init"""
        if not self._tempdir:
            self._tempdir = tempfile.mkdtemp()
            self._tempdir_created = True
        return self._tempdir

    def download(self, filename=None):
        """Download package archive from PyPi to the specified filename"""
        if filename and os.path.isfile(filename):
            return filename
        if not self.source:
            return None

        if not filename:
            filename = os.path.join(self.tempdir, self.source['filename'])

        if not os.path.isfile(filename):
            try:
                urlretrieve(self.source['url'], filename)
            except IOError:  # missing file (likely due to PyPi bug, very rare)
                return None
        return filename

    @cache('_pkgdir')
    def extract(self):
        fname = self.download()
        if fname is None:
            return None

        extension = ""
        for ext in self.formats:
            if fname.endswith(ext):
                extension = ext
                break
        if not extension:
            raise ValueError("Unexpected archive format: %s" % fname)

        basename = os.path.basename(fname[:-len(extension)])
        pkgdir = os.path.join(self.tempdir, basename)
        cmd = self.formats[extension] % {
            'fname': fname, 'bname': basename, 'dir': self.tempdir}
        if not os.path.isdir(pkgdir):
            os.system(cmd)
        if not os.path.isdir(pkgdir):
            # usually mistyped folder name. pip/setuptools won't install them
            return None
        return pkgdir

    def _search(self, pattern):
        """Search for a pattern in package info and package content"""
        m = re.search(pattern, str(self.info))
        if m:
            return m.group()

        filename = self.extract()
        if not filename:  # some packages don't have downloadable files
            return None

        try:
            output = _shell("zgrep.sh", pattern, filename)
        except subprocess.CalledProcessError:
            return None
        return output.strip() or None  # output could be empty

    @property
    @cache('_github_url')
    def github_url(self):
        m = re.search("github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+",
                      self.info.get('home_page', ''))
        if m:
            url = m.group(0)
        else:
            url = self._search("github\.com/[a-zA-Z0-9_-]+/" + self.name)
        return url and url[11:] or ''

    @property
    @cache('_google_group')
    def google_group(self):
        return self._search("groups\.google\.com/forum/#!forum/[a-zA-Z0-9_-]*")

    @property
    @cache('_dependencies')
    def dependencies(self):
        """Extract dependencies from setup.py"""
        dirname = self.extract()
        if not dirname:
            return []
        return dependencies(dirname)

    @property
    @cache('_LOC')
    def size(self):
        """get size in LOC"""
        dirname = self.extract()
        if not dirname:
            return 0  # no downloadable sources == 0 LOC
        package_path = os.path.join(dirname, self.name)
        if os.path.isdir(package_path):
            package_path += '.py'
            if not os.path.isfile(package_path):
                return 0
        return loc_size(package_path)


def list_packages():
    tree = ElementTree.fromstring(Package._request("simple/").text)
    return [a.text for a in tree.iter('a')]
