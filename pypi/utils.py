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
import json
import shutil
import logging

from common import decorators as d

# TODO: bugtrack_url support

# TODO: .whl support
# - this is a zip format
# - does not require sandbox
# - need to extract completely (internal path is unknown)
# - dependencies are in <something>.dist-info/metadata.json
#   .run_requires.item.requires: list

logger = logging.getLogger("ghd.pypi")
PY3 = sys.version_info[0] > 2
if PY3:
    from urllib.request import urlretrieve  # Python3
else:
    from urllib import urlretrieve  # Python2

PYPI_URL = "https://pypi.python.org"
# directory where package archives are stored
DEFAULT_SAVE_PATH = tempfile.mkdtemp(prefix="ghd.pypi.")
# default network timeout
TIMEOUT = 10
# path to provided shell scripts
_PATH = os.path.dirname(__file__) or '.'

# supported formats and extraction commands
unzip = 'unzip -qq -o "%(fname)s" -d "%(dir)s" 2>/dev/null'
untgz = 'tar -C "%(dir)s" --strip-components 1 -zxf "%(fname)s" 2>/dev/null'
# TODO: rpm support
SUPPORTED_FORMATS = {
    '.zip': unzip,
    '.whl': unzip,
    '.egg': unzip,
    '.tar.gz': untgz,
    '.tgz': untgz,
    '.tar.bz2': untgz,
}

"""
Notes:
1. There is no reliable source for supported Python version.
    requires-dist format is described here: 
        https://www.python.org/dev/peps/pep-0345/#version-specifiers
    Unfortunately, it is not informative at all:
        - vast majority (99%) of packages doesn't use it
        - many of those who use do not conform to the standard
"""


class PackageDoesNotExist(ValueError):
    pass


def _shell(cmd, *args, **kwargs):
    if kwargs.get('local', True):
        cmd = os.path.join(_PATH, cmd)
    status = 0
    try:
        output = subprocess.check_output(
            (cmd,) + args, stderr=kwargs.get('stderr'))
    except subprocess.CalledProcessError as e:
        if kwargs.get('raise_on_status', True):
            raise
        output = e.output
        status = e.returncode

    if PY3:
        output = output.decode('utf8')
    return status, output


def _parse_ver(version):
    # type: (str) -> list
    """ Transform version string into comparable list
    :param version: version string, e.g. 0.11.23rc1
    :return: list of version chunks, e.g. [0, 11, 23, 'rc1']
    """
    chunks = []
    for chunk in re.findall(r"(\d+|[A-Za-z]\w*)", version):
        try:
            chunk = int(chunk)
        except ValueError:
            pass
        chunks.append(chunk)
    return chunks


def compare_versions(ver1, ver2):
    # type: (str, str) -> int
    """Compares two version string, returning {-1|0|1} just as cmp().
    """
    chunks1 = _parse_ver(str(ver1))
    chunks2 = _parse_ver(str(ver2))
    min_len = min(len(chunks1), len(chunks2))
    for i in range(min_len):
        if chunks1[i] > chunks2[i]:
            return 1
        elif chunks1[i] < chunks2[i]:
            return -1
    if len(chunks1) > min_len and isinstance(chunks1[min_len], str):
        return -1
    if len(chunks2) > min_len and isinstance(chunks2[min_len], str):
        return 1
    return 0


def _get_builtins(python_version):
    """Return set of built-in libraries for Python2/3 respectively"""
    assert python_version in (2, 3)
    url = "https://docs.python.org/%s/library/index.html" % python_version
    text = requests.get(url, timeout=TIMEOUT, verify=False).text
    # text is html and can't be processed with Etree, so regexp it is
    return set(b.lower() for b in re.findall(
        """<span\s+class=["']pre["']\s*>\s*([\w_-]+)\s*</span>""", text))


def loc_size(package_dir):
    status, pylint_out = _shell("pylint", "--py3k", package_dir,
                                local=False, raise_on_status=False,
                                stderr=open(os.devnull, 'w'))
    if status == 2:
        raise EnvironmentError("pylint is not installed (just in case, path is "
                               "%s)" % package_dir)
    m = re.search("\|code\s*\|([\\s\\d]+?)\|", pylint_out)
    match = m and m.group(1).strip()
    if not match:
        return 0
    return int(match)


class Package(object):
    name = None  # package name
    path = None  # path of the file, used to find zgrep
    info = None  # stores cached package info
    _dirs = []  # created directories to cleanup later

    def __init__(self, name, save_path=None):
        self.name = name.lower()
        self.save_path = save_path or DEFAULT_SAVE_PATH
        try:
            r = self._request("pypi", self.name, "json")
            self.info = r.json()
        except IOError:
            raise PackageDoesNotExist(
                "Package %s does not exist on PyPi" % name)
        except ValueError:  # simplejson.scanner.JSONDecodeError is a subclass
            # malformed json
            raise ValueError("PyPi package description is invalid")

        self.canonical_name = self.info['info']['name']
        self.latest_ver = self.info['info'].get('version')

    def __del__(self):
        if DEFAULT_SAVE_PATH != self.save_path:
            return
        for folder in self._dirs:
            try:
                shutil.rmtree(folder)
            except OSError:
                logger.debug("Error removing temp dir after package %s: %s",
                             self.name, folder)

    def __str__(self):
        return self.canonical_name

    def __repr__(self):
        return "<PyPi package: %s>" % self.name

    @staticmethod
    def _request(*path):
        for i in range(3):
            try:
                r = requests.get("/".join((PYPI_URL,) + path), timeout=TIMEOUT)
            except requests.exceptions.Timeout:
                continue
            r.raise_for_status()
            return r
        raise IOError("Failed to reach PyPi. Check your Internet connection.")

    def releases(self, include_unstable=False, include_backports=False):
        releases = sorted([
            (label, min(f['upload_time'][:10] for f in files))
            for label, files in self.info['releases'].items()
            if files],  # skip empty releases
            key=lambda r: r[1])  # sort by date
        if not include_unstable:
            releases = [(label, date)
                        for label, date in releases
                        if re.match("^\d+(\.\d+)*$", label)]
        if not include_backports and releases:
            _rel = []
            for label, date in releases:
                if not _rel or compare_versions(label, _rel[-1][0]) >= 0:
                    _rel.append((label, date))
            releases = _rel
        return releases

    def download_url(self, ver):
        assert ver in self.info['releases']
        for pkgtype in ("bdist_wheel", "sdist"):
            for info in self.info['releases'][ver]:
                if info['packagetype'] == pkgtype and \
                    any(info['url'].endswith(ext)
                        for ext in SUPPORTED_FORMATS):
                    return info['url']
        # no downloadable files in supported format
        logger.info("No downloadable files in supported formats "
                    "for package %s ver %s found", self.name, ver)
        return None

    @d.cached_method
    def download(self, ver=None):
        """Download and extract specified package version from PyPi
        :param ver - Version of package
        """
        ver = ver or self.latest_ver
        logger.debug("Attempting to download package: %s", self.name)
        # ensure there is a downloadable package release
        download_url = self.download_url(ver)
        if download_url is None:
            return None

        # check if extraction folder exists
        extract_dir = os.path.join(self.save_path, self.name + "-" + ver)
        if os.path.isdir(extract_dir):
            if any(os.path.isdir(d) for d in os.listdir(extract_dir)):
                logger.debug(
                    "Package %s was downloaded already, skipping", self.name)
                return extract_dir  # already extracted
        else:
            os.mkdir(extract_dir)
            self._dirs.append(extract_dir)

        # download file to the folder
        fname = os.path.join(extract_dir, download_url.rsplit("/", 1)[-1])
        try:
            # TODO: timeout handling
            urlretrieve(download_url, fname)
        except IOError:  # missing file, very rare but happens
            logger.warning("Broken PyPi link: %s", download_url)
            return None

        # extract using supported format
        extension = ""
        for ext in SUPPORTED_FORMATS:
            if fname.endswith(ext):
                extension = ext
                break
        if not extension:
            raise ValueError("Unexpected archive format: %s" % fname)

        cmd = SUPPORTED_FORMATS[extension] % {
            'fname': fname, 'dir': extract_dir}
        os.system(cmd)

        # fix permissions (+X = traverse dirs)
        os.system('chmod -R u+rX "%s"' % extract_dir)

        return extract_dir

    def _info_path(self, ver):
        """
        :return: either xxx.dist-info or xxx.egg-info path, or None
        """
        extract_dir = self.download(ver)
        if not extract_dir:
            return None

        dist_info_path = "%s-%s.dist-info" % (self.canonical_name, ver)
        egg_info_path = "%s.egg-info" % self.canonical_name
        for info_path in (dist_info_path, egg_info_path, "EGG-INFO"):
            path = os.path.join(extract_dir, info_path)
            if os.path.isdir(path):
                logger.debug("Project has info folder: %s", path)
                return path
        logger.debug(
            "Neither dist-info nor egg-info folders found in %s", self.name)

    @d.cached_method
    def top_level_dir(self, ver):
        """ Return path to wheel dist-info path and main folder
        :param ver: str version
        :return: (.dist-info path, top dir path)
        """
        logger.debug("Package %s ver %s top folder:", self.name, ver)

        extract_dir = self.download(ver)
        if not extract_dir:
            return None

        info_path = self._info_path(ver)
        dirname = info_path
        tl_fname = info_path and os.path.join(info_path, 'top_level.txt')
        if tl_fname and os.path.isfile(tl_fname):
            dirname = os.path.basename(open(tl_fname, 'r').read(80).strip())
            logger.debug("    .. assumed from top_level.txt")
        elif os.path.isdir(os.path.join(extract_dir, self.name)):
            # welcome to the darkest year of our adventures, Morti
            dirname = self.name
            logger.debug("    .. assumed from project name")
        else:  # getting darker..
            for entry in os.listdir(extract_dir):
                logger.debug("    .. guessing from the first match")
                if os.path.isfile(
                        os.path.join(extract_dir, entry, "__init__.py")):
                    dirname = entry
                    break

        if dirname:
            toplevel = os.path.join(extract_dir, dirname)
            if os.path.isdir(toplevel):
                logging.debug("    top folder: %s", dirname)
                return toplevel
        logger.info("Top folder was not found or does not exist in package "
                    "%s ver %s", self.name, ver)

    def _search(self, pattern):
        """Search for a pattern in package info and package content"""
        m = re.search(pattern, str(self.info))
        if m:
            return m.group()

        path = self.top_level_dir(self.latest_ver)
        if not path:  # some packages don't have downloadable files
            return None

        _, output = _shell("zgrep.sh", pattern, path, raise_on_status=False)
        return output.strip() or None  # output could be empty

    @d.cached_property
    def github_url(self):
        # check home page first
        m = re.search("github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+",
                      self.info.get('info', {}).get('home_page', ''))
        if m:
            url = m.group(0)
        else:
            url = self._search("github\.com/[a-zA-Z0-9_-]+/" + self.name)
        return url and url[11:] or ''

    @d.cached_property
    def google_group(self):
        return self._search("groups\.google\.com/forum/#!forum/[a-zA-Z0-9_-]*")

    @d.cached_method
    def dependencies(self, ver=None):
        """Extract dependencies from either wheels metadata or setup.py"""
        ver = ver or self.latest_ver
        logger.debug(
            "Getting dependencies for project %s ver %s", self.name, ver)
        extract_dir = self.download(ver)
        if not extract_dir:
            return []

        info_path = self._info_path(ver) or ""
        if info_path.endswith(".dist-info"):
            logger.debug("    .. WHEEL package, parsing from metadata.json")
            fname = os.path.join(info_path, 'metadata.json')
            if not os.path.isfile(fname):
                return []
            info = json.load(open(fname))
            # only unconditional dependencies are considered
            # http://legacy.python.org/dev/peps/pep-0426/#dependency-specifiers
            deps = []
            for dep in info.get('run_requires', []):
                if 'extra' not in dep and 'environment' not in dep:
                    deps.extend(dep['requires'])
        elif info_path.endswith(".egg-info"):
            logger.debug("    .. egg package with info, parsing requires.txt")
            fname = os.path.join(info_path, 'requires.txt')
            if not os.path.isfile(fname):
                return []
            deps = []
            for line in open(fname, 'r'):
                if "[" in line:
                    break
                if line:
                    deps.append(line)
        else:
            if not os.path.isfile(os.path.join(extract_dir, "setup.py")):
                logger.debug("    .. looks to be a malformed package")
                return []
            logger.debug("    ..generic package, running setup.py in a sandbox")
            _, output = _shell("docker.sh", extract_dir)
            deps = output.split(",")

        depslist = [re.split("[^\w._-]", dep.strip(), 1)[0].lower()
                    for dep in deps if dep]
        return set(dep for dep in depslist if dep)

    @d.cached_method
    def size(self, ver):
        """get size in LOC"""
        # TODO: support for a single file
        path = self.top_level_dir(ver)
        if not path:
            return 0  # no downloadable sources == 0 LOC
        return loc_size(path)


@d.fs_cache("pypi")
def list_packages():
    # type: () -> pd.Series
    tree = ElementTree.fromstring(Package._request("simple/").content)
    s = pd.Series(sorted(a.text.lower() for a in tree.iter('a')),
                  name="packages")
    s.index = s
    return s


def packages_info():
    for pkgname in list_packages():
        try:
            p = Package(pkgname)
        except PackageDoesNotExist:
            # some deleted packages aren't removed from the list
            continue

        yield {'name': pkgname, 'github_url': p.github_url}

