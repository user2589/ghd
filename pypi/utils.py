#!/usr/bin/env python

"""An abstraction of Python package repository API (PyPi API)."""
from __future__ import print_function, unicode_literals

import pandas as pd

from collections import defaultdict
import json
import logging
import os
import re
import requests
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree

from common import decorators as d
from common import email
from common import threadpool
import scraper

try:
    from settings import PYPI_SAVE_PATH
except ImportError:
    PYPI_SAVE_PATH = None
else:
    if not os.path.isdir(PYPI_SAVE_PATH):
        os.mkdir(PYPI_SAVE_PATH)

PY3 = sys.version_info[0] > 2
if PY3:
    from urllib.request import urlretrieve  # Python3
else:
    from urllib import urlretrieve  # Python2



logger = logging.getLogger("ghd.pypi")

PYPI_URL = "https://pypi.python.org"
# directory where package archives are stored
DEFAULT_SAVE_PATH = tempfile.mkdtemp(prefix="ghd.pypi.")
# default network timeout
TIMEOUT = 10
# path to provided shell scripts
_PATH = os.path.dirname(__file__) or '.'

fs_cache = d.fs_cache('pypi')

# supported formats and extraction commands
unzip = 'unzip -qq -o "%(fname)s" -d "%(dir)s" 2>/dev/null'
untgz = 'tar -C "%(dir)s" --strip-components 1 -zxf "%(fname)s" 2>/dev/null'
untbz = 'tar -C "%(dir)s" --strip-components 1 -jxf "%(fname)s" 2>/dev/null'
# TODO: rpm support
SUPPORTED_FORMATS = {
    '.zip': unzip,
    '.whl': unzip,
    '.egg': unzip,  # can't find a single package to test. Are .eggs extinct?
    '.tar.gz': untgz,
    '.tgz': untgz,
    '.tar.bz2': untbz,
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
    """ Execute shell command and return output

    :param cmd: the command itself, i.e. part until the first space
    :param args: positional arguments, i.e. other space-separated parts
    :param kwargs:
            local: execute relative to package folder directory,
                for internal use only (create docker images)
            raise_on_status: bool, raise exception if command
                exited with non-zero status
            stderr: file-like object to collect stderr output, None by default
    :return: (int status, str shell output)
    """
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
    """ Return set of built-in libraries for Python2/3 respectively
    Intented for parsing imports from source files
    """
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
    _dirs = None  # created directories to cleanup later

    def __init__(self, name):
        self._dirs = []
        self.name = name.lower()
        self.save_path = PYPI_SAVE_PATH or DEFAULT_SAVE_PATH
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
                # str conversion is required because of this shutil bug:
                # https://bugs.python.org/issue24672
                # use tai5_uan5_gian5_gi2_tsu1_liau7_khoo3-tng7_su5_piau1_im1
                # to test this issue
                shutil.rmtree(str(folder))
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
        """Return release labels
        :param include_unstable: bool, whether to include releases including
            symbols other than dots and numbers
        :param include_backports: bool, whether to include releases smaller in
            version than last stable release
        :return list of string release labels
        """
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
        """Get URL to package file of the specified version
        This function takes into account supported file types and their
        relative preference (e.g. wheel files before source packages)

        :param ver: str, version string
        :return: url string if found, None otherwise
        """
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
        os.system('chmod -R u+rwX "%s"' % extract_dir)

        # edge case: zip source archives usually (always?) contain
        # extra level folder. If after extraction there is a single dir in the
        # folder, change extract_dir to that folder
        if download_url.endswith(".zip"):
            single_dir = None
            for entry in os.listdir(extract_dir):
                entry_path = os.path.join(extract_dir, entry)
                if os.path.isdir(entry_path):
                    if single_dir is None:
                        single_dir = entry_path
                    else:
                        single_dir = None
                        break
            if single_dir:
                extract_dir = single_dir

        return extract_dir

    def _info_path(self, ver):
        """
        :return: either xxx.dist-info or xxx.egg-info path, or None

        It is used by dependencies parser and to locate top_level.txt
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

        General idea:
            - look for top_level.txt in the info folder - egg/wheel packages
                for single file packages it's a filename without .py
            - check for a <project name> folder - .zip or tgz archives
            - any folder with __init__.py
            - <project name>.py file - single file packages
            - any folder at all
            - lastly, if nothing worked, it might be a single file package.
                Normally, in this case we need to parse out py_modules from
                setup() parameters, but sandboxing is too expensive. So, the
                first non-setup .py it is
        Tests:
            0.0.1[0.0.1] - tar.gz, dir
            0[0.0.0] - whl, single file
            02exercicio[1.0.0] - tar.gz, no files
            asciaf[1.0.0] - tar.gz, no files
            0805nexter[1.2.0] - zip, single file
            4suite-xml[1.2.0] - tar.bz2, __init__ folder
            a3rt-sdk-py["0.0.3"] - folder not matching canonical name
            abofly["1.4.0"] - single file, using non-canonical name

        >>> p = Package("0.0.1")
        >>> bool(p.top_level_dir("0.0.1"))
        True
        >>> p = Package("0")
        >>> bool(p.top_level_dir("0.0.0"))
        True
        >>> p = Package("02exercicio")
        >>> bool(p.top_level_dir("1.0.0"))
        False
        >>> p = Package("4suite-xml")
        >>> bool(p.top_level_dir("1.0.2"))
        True
        >>> p = Package("0805nexter")
        >>> bool(p.top_level_dir("1.2.0"))
        True
        >>> p = pypi.Package("a3rt-sdk-py")
        >>> bool(p.top_level_dir("0.0.3"))
        True
        >>> p = pypi.Package("abofly")
        >>> bool(p.top_level_dir("1.4.0"))
        True
        """
        logger.debug("Package %s ver %s top folder:", self.name, ver)

        extract_dir = self.download(ver)
        if not extract_dir:
            return None

        info_path = self._info_path(ver)
        dirname = None
        tl_fname = info_path and os.path.join(info_path, 'top_level.txt')
        if tl_fname and os.path.isfile(tl_fname):
            dirname = os.path.basename(open(tl_fname, 'r').read(80).strip())
            logger.debug("    .. assumed from top_level.txt")
            if not os.path.isdir(dirname):
                if os.path.isfile(dirname + ".py"):
                    dirname += ".py"
                    logger.debug("    .. single file package")
                else:
                    dirname = None
                    logger.debug("    .. but doesn't exist")

        if not dirname and os.path.isdir(
                os.path.join(extract_dir, self.canonical_name)):
            # welcome to the darkest year of our adventures, Morti
            dirname = self.canonical_name
            logger.debug("    .. assumed from project name")

        if not dirname:  # getting darker..
            logger.debug("    .. guessing from the first __init__.py")
            for entry in os.listdir(extract_dir):
                if os.path.isfile(
                        os.path.join(extract_dir, entry, "__init__.py")):
                    dirname = entry
                    break

        if not dirname and os.path.isfile(
                os.path.join(extract_dir, self.canonical_name + ".py")):
            dirname = self.canonical_name + ".py"
            logger.debug("    .. assumed from project name (single file)")

        if not dirname:  # any folder at all
            # Py3 doesn't require __init__.py, so it could be a package folder
            # unlike info folders, it can't contain a dot in the name
            logger.debug("    .. any folder at all?")
            for entry in os.listdir(extract_dir):
                if "." not in entry and os.path.isdir(
                        os.path.join(extract_dir, entry)):
                    dirname = entry
                    break

        if not dirname:  # any .py file at all
            logger.debug("    .. any python file?")
            for entry in os.listdir(extract_dir):
                if entry.endswith(".py") and entry != "setup.py" and \
                        os.path.isfile(os.path.join(extract_dir, entry)):
                    dirname = entry
                    break

        if dirname:
            toplevel = os.path.join(extract_dir, dirname)
            if os.path.isdir(toplevel) or os.path.isfile(toplevel):
                logging.debug("    top folder: %s", dirname)
                return toplevel
        logger.info("Top folder was not found or does not exist in package "
                    "%s ver %s", self.name, ver)

    @d.cached_property
    def url(self):
        """Search for a pattern in package info and package content
        Search places:
        - info home page field
        - full info page
        - package content
        :return url if found, None otherwise
        """
        # check home page first
        m = scraper.URL_PATTERN.search(
                      self.info.get('info', {}).get('home_page') or "")
        if m:
            return m.group(0)

        pattern = scraper.named_url_pattern(self.name)

        m = re.search(pattern, str(self.info))
        if m:
            return m.group(0)

        path = self.top_level_dir(self.latest_ver)
        if not path:  # some packages don't have downloadable files
            return None

        _, output = _shell("zgrep.sh", pattern, path, raise_on_status=False)
        return output.strip() or None  # output could be empty


    @d.cached_method
    def dependencies(self, ver=None):
        """Extract dependencies from either wheels metadata or setup.py"""
        ver = ver or self.latest_ver
        logger.debug(
            "Getting dependencies for project %s ver %s", self.name, ver)
        extract_dir = self.download(ver)
        if not extract_dir:
            return {}

        info_path = self._info_path(ver) or ""
        if info_path.endswith(".dist-info"):
            logger.debug("    .. WHEEL package, parsing from metadata.json")
            fname = os.path.join(info_path, 'metadata.json')
            if not os.path.isfile(fname):
                return {}
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
                return {}
            deps = []
            for line in open(fname, 'r'):
                if "[" in line:
                    break
                if line:
                    deps.append(line)
        else:
            if not os.path.isfile(os.path.join(extract_dir, "setup.py")):
                logger.debug("    .. looks to be a malformed package")
                return {}
            logger.debug("    ..generic package, running setup.py in a sandbox")
            _, output = _shell("docker.sh", extract_dir)
            deps = output.split(",")

        def dep_split(dep):
            match = re.match("[\w_-]+", dep)
            if not match:  # invalid dependency
                name = ""
            else:
                name = match.group(0)
            version = dep[len(name):].strip()
            return name, version

        depslist = dict(dep_split(dep.strip()) for dep in deps if dep.strip())

        return depslist

    @d.cached_method
    def size(self, ver):
        """get size in LOC"""
        # TODO: support for a single file
        path = self.top_level_dir(ver)
        if not path:
            return 0  # no downloadable sources == 0 LOC
        return loc_size(path)


@fs_cache
def packages_info():
    tree = ElementTree.fromstring(Package._request("simple/").content)
    package_names = sorted(a.text.lower() for a in tree.iter('a'))

    names = []  # lsit off package names
    urls = {}  # urls[pkgname] = github_url
    authors = {}  # authors[pkgname] = author_email
    licenses = {}
    author_projects = defaultdict(list)
    author_orgs = defaultdict(
        lambda: defaultdict(int))  # orgs[author] = {org: num_packages}

    for package_name in package_names:
        logger.info("Processing %s", package_name)
        try:
            p = Package(package_name)
        except PackageDoesNotExist:
            # some deleted packages aren't removed from the list
            continue
        names.append(package_name)

        if p.url:
            urls[package_name] = p.url

        try:
            author_email = email.clean(p.info["info"].get('author_email'))
        except email.InvalidEmail:
            author_email = None

        if author_email:
            author_projects[author_email].append(package_name)

        authors[package_name] = author_email
        licenses[package_name] = p.info['info']['license']

        if p.url:
            provider, project_url = scraper.parse_url(p.url)
            if provider == "github.com":
                org, _ = project_url.split("/")
                author_orgs[author_email][org] += 1

    # at this point, we have ~54K repos
    # by guessing github account from author affiliations we can get 8K more
    processed = 0
    total = len(author_projects)
    for author, packages in author_projects.items():
        logger.info("Postprocessing authors (%d out of %d): %s",
                    processed, total, author)
        # check all orgs of the author, starting from most used ones
        orgs = [org for org, _ in
                sorted(author_orgs[author].items(), key=lambda x: -x[1])]
        if not orgs:
            continue
        for package in packages:
            if package in urls:
                continue
            for org in orgs:
                url = "%s/%s" % (org, package)
                r = requests.get("https://github.com/" + url)
                if r.status_code == 200:
                    urls[package] = url
                    break

    return pd.DataFrame({"url": urls, "author": authors, 'license': licenses},
                        index=names)


# Note that this method already uses internal cache. However, we probably don't
# want to update this cache every time; thus, we have additional caching with
# @fs_cache instance to make updates in 3 month (d.DEFAULT_EXPIRY) increments
@fs_cache
def dependencies():
    """ Get a bunch of information about npm packages
    This will return pd.DataFrame with package name as index and columns:
        - version: version of release, str
        - date: release date, ISO str
        - deps: names of dependencies, comma separated string
        - raw_dependencies: dependencies, JSON dict name: ver
        - raw_test_dependencies
        - raw_build_dependencies
    """
    deps = {}
    fname = fs_cache.get_cache_fname(".deps_and_size.cache")

    if os.path.isfile(fname):
        logger.info("deps_and_size() cache file already exists. "
                    "Existing records will be reused")

        def gen(df):
            d = {}
            for index, row in df.iterrows():
                item = row.to_dict()
                item["name"] = index[0]
                item["version"] = index[1]
                d[tuple(index)] = item
                return d

        deps = gen(pd.read_csv(fname, index_col=["name", "version"]))

    else:
        logger.info("deps_and_size() cache file doesn't exists. "
                    "Computing everything from scratch is a lengthy process "
                    "and will likely take a week or so")

    tp = threadpool.ThreadPool(16)
    logger.info("Starting a threadppol with %d workers...", tp.n)

    package_names = packages_info().index

    def do(pkg_name, ver, release_date):
        p_deps = Package(pkg_name).dependencies(ver)

        return {
            'name': pkg_name,
            'version': version,
            'date': release_date,
            'deps': ",".join(p_deps.keys()).lower(),
            'raw_dependencies': json.dumps(p_deps)
        }

    def done(output):
        deps[(output["name"], output["version"])] = output

    for package_name in package_names:

        logger.info("Processing %s", package_name)
        try:
            p = Package(package_name)
        except PackageDoesNotExist:
            continue

        for version, release_date in p.releases(True, True):
            if (package_name, version) not in deps:
                logger.info("    %s", version)
                tp.submit(do, package_name, version, release_date, callback=done)
            else:
                logger.info("    %s (cached)", version)

    # save updates
    df = pd.DataFrame(deps.values()).sort_values(["name", "version"])
    df.to_csv(fname)

    return df.set_index(["name", "version"])



