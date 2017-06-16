
from __future__ import print_function

import os
import re
import csv  # pd.read_csv doesn't work for large files
import datetime
import requests
import urllib
import xml.sax
import logging
import subprocess
import gzip  # workaround for libarchive

import pandas as pd
import numpy as np
import libarchive.public as libarchive

import settings

DATASET_PATH = settings.DATASET_PATH
DATASET_PARTS = {
    'Comments', 'PostHistory', 'PostLinks', 'Posts', 'Tags', 'Users', 'Votes'}

logger = logging.getLogger('ghd.so')


def get_fname(dataset_part):
    """Returns path to the specified part of the dataset"""
    assert dataset_part in DATASET_PARTS, "Unexpected SO dataset part"
    # Workaround for libarchive bug: replace later
    return os.path.join(DATASET_PATH, "%s.xml.gz" % dataset_part)
    # return os.path.join(DATASET_PATH, "stackoverflow.com-%s.7z" % dataset_part)


def get_mtime(dataset_part):
    """Return modification time of corresponding StackOverflow dataset part or
    None if file does not exist. This method is used to check if dataset needs
    to be updated
    """
    fname = get_fname(dataset_part)
    if not os.path.isfile(fname):
        return None
    return datetime.datetime.fromtimestamp(
        os.path.getmtime(fname)).strftime("%Y-%m-%d")


def online_ver():
    """Get last available version of StackOverflow Archive
    This method parses dataset page on archive.org and thus requires Internet
    connection"""
    r = requests.get("https://archive.org/details/stackexchange")
    if not r.ok:
        logger.warning("can't retrieve SO Archive page, assuming up to date")
        return None

    m = re.search("Published.+?search\.php\?query=date:(\d{4}-\d\d-\d\d)",
                  r.text)
    if not m:
        logger.warning("Can't find release date, assuming up to date")
        return None
    return m.group(1)


def is_stale(dataset_part):
    """Check if dataset part is out of date."""
    mtime = get_mtime(dataset_part)
    if mtime is None:
        logger.debug("Dataset file is missing, the dataset is stalled")
        return True

    available_ver = online_ver()
    if available_ver is None:
        return False

    stalled = available_ver > mtime
    logger.debug("Dataset is stalled: %s (file modified %s, online ver is %s",
                 stalled, mtime, available_ver)
    return stalled


def get_path(dataset_part, update=True):
    """Get path to the dataset part. This method will automatically update the
    data if a newer version is available."""
    fname = get_fname(dataset_part)
    if not os.path.isfile(fname) or update and is_stale(dataset_part):
        logger.info('StackOverflow %s are stalled, refreshing', dataset_part)
        filename7z = os.path.join(DATASET_PATH, "stackoverflow.com-%s.7z" % dataset_part)
        if not os.path.isfile(fname):
            os.unlink(filename7z)
            url = "https://archive.org/download/stackexchange/" \
                  "stackoverflow.com-%s.7z" % dataset_part
            logger.info('downloading %s -> %s...', url, fname)
            urllib.urlretrieve(url, filename7z)

        # Workaround for a libarchive bug - convert to .gz
        # https://github.com/libarchive/libarchive/issues/913
        logger.info('converting to gzip')
        convertor = os.path.join(os.path.dirname(__file__) or '.', "7z2gz.sh")
        fname = subprocess.check_output([convertor, filename7z]).strip()

        logger.info('..done')
    return fname


def parse(parserobj):
    """Get dataset part and process contained archive by specified SAX parser"""
    dataset_part = parserobj.dataset_part
    xml_parser = xml.sax.make_parser(['xml.sax.xmlreader.IncrementalParser'])
    sax_parser = parserobj()
    xml_parser.setContentHandler(sax_parser)

    fname = get_path(dataset_part)
    if fname.endswith('7z'): # use libarchive
        entry_fname = dataset_part + '.xml'
        with libarchive.file_reader(fname) as archive:
            for entry in archive:
                if str(entry) == entry_fname:
                    for block in entry.get_blocks():
                        xml_parser.feed(block)
                    xml_parser.close()
    elif fname.endswith('gz'):
        stream = gzip.open(fname)
        xml_parser.parse(stream)
    else:
        raise ValueError('The provided file format is not supported')
    return sax_parser


def iNone(attr):
    """parse passed string as integer, return None if it is not"""
    try:
        return int(attr)
    except (ValueError, TypeError) as _:
        return None


class SOHandler(xml.sax.ContentHandler):
    """Parent class for parsing StackOverflow dataset"""
    handlers = {}

    def __init__(self):
        self.handlers = {
            'posts': self._parse_post,
            'users': self._parse_user,
            'tags': self._parse_tag,
            'votes': self._parse_vote
        }
        xml.sax.ContentHandler.__init__(self)

    @staticmethod
    def _parse_post(attrs):
        post_id = int(attrs['Id'])
        is_question = int(attrs.get('PostTypeId') == "1")
        tags = [t.lstrip("<") for t in attrs.get('Tags', "").split(">") if t] \
            if is_question else []
        return {
            'id': post_id,
            'question': is_question,
            'title': attrs.get('Title'),  # no title for answers
            'body': attrs['Body'],
            'owner_id': iNone(attrs.get('OwnerUserId')),
            'accepted_answer': attrs.get('accepted_answer'),
            'created_at': attrs['CreationDate'],
            'score': int(attrs.get('Score', 0)),
            'parent_id': iNone(attrs.get('ParentId')),
            'views': int(attrs.get('ViewCount', 0)),
            'last_editor_id': iNone(attrs.get('OwnerUserId')),
            'last_edited_at': attrs.get('LastEditDate'),
            'last_activity_at': attrs.get('LastEditDate'),
            'community_owned_at': attrs.get('CommunityOwnedDate'),
            'answers_count': int(attrs.get('AnswerCount', 0)),
            'comments_count': int(attrs.get('CommentCount', 0)),
            'favorites_count': int(attrs.get('FavoriteCount', 0)),
            'tags': tags,
        }

    @staticmethod
    def _parse_user(attrs):
        return {
            'id': int(attrs['Id']),
            'name': attrs['DisplayName'],
            'email_hash': None,
            'reputation': int(attrs.get('Reputation'), 0),
            'created_at': attrs['CreationDate'],
            'website_url': attrs.get('WebsiteUrl'),
            'location': attrs.get('Location'),
            'age': iNone(attrs.get('Age')),
            'views': int(attrs.get('Views', 0)),
            'upvotes': int(attrs.get('UpVotes', 0)),
            'downvotes': int(attrs.get('DownVotes', 0)),
            'about_me': attrs.get('AboutMe')
        }

    @staticmethod
    def _parse_tag(attrs):
        return {
            'id': int(attrs['Id']),
            'name': attrs['TagName'],
            'count': int(attrs.get('Count'), 0),
            'excerpt_post_id': iNone(attrs.get('ExcerptPostId')),
            'wiki_post_id': iNone(attrs.get('WikiPostId'))
        }

    @staticmethod
    def _parse_vote(attrs):
        return {
            'id': int(attrs['Id']),
            'post_id': attrs['PostId'],
            'vote_type': int(attrs.get('VoteTypeId')),
            'created_at': attrs['CreationDate']
        }

    def parse(self): pass

    def startElement(self, name, attrs):
        if name in self.handlers:
            self.parse = self.handlers[name]
            return None
        assert name == 'row', "Unexpected tag: %s" % name
        return self.parse(attrs)


class TagReader(SOHandler):
    """Class to generate list of tags. It is not supposed to be used directly,
    call tags() instead"""
    dataset_part = 'Tags'
    tags = None

    def __init__(self):
        self.tags = []
        SOHandler.__init__(self)

    def startElement(self, name, attrs):
        tag = SOHandler.startElement(self, name, attrs)
        if tag is not None:
            self.tags.append(tag['name'])


def tags():
    """Get list of StackOverflow tags"""
    # takes ~2 seconds, no caching needed
    return parse(TagReader).tags


class PostReader(SOHandler):
    """Class to generate monthly statistics for StackOverflow tags.
    This class is not supposed to be used directly, but rather through call of
    question_stats() or ./manage.py so_stats
    """
    dataset_part = 'Posts'
    stats = None  # resulting dataframe

    def __init__(self):
        idx = ['ALL'] + tags()
        # tags() will check whether the dataset is stalled, so at this
        # point Tags mtime is up to date
        columns = [ts.strftime("%Y-%m") for ts in
                   pd.date_range('2008-07-1', get_mtime('Tags'), freq='M')][:-1]
        self.stats = pd.DataFrame(0, columns=columns, index=idx, dtype=np.int32)
        SOHandler.__init__(self)

    def startElement(self, name, attrs):
        post = SOHandler.startElement(self, name, attrs)
        if post is None or not post['question']:
            return
        month = post['created_at'][:7]
        for tag in post['tags']:  # questions have at least one tag
            self.stats.loc[tag, month] += 1
            self.stats.loc['ALL', month] += 1


def question_stats():
    """Get Pandas dataframe with monthly question statistics. Index is tags,
    columns are months in %Y-%m format"""
    return parse(PostReader).stats


class AdjacencyHandler(SOHandler):
    """Class to generate ajacency matrix. It is not supposed to be used directly
    Please use adjacency_matrix() instead.
    Note that this class generates 100kx100k dataframe that takes around 4Gb of
    RAM to hold and quite a bit of time to process and save."""
    dataset_part = 'Posts'
    matrix = None

    def __init__(self):
        idx = tags()
        # SparseDataFrame.to_csv() doesn't as of 0.20.1.
        # Consider changing from DataFrame when it is fixed
        self.matrix = pd.DataFrame(0, columns=idx, index=idx, dtype=np.int32)
        SOHandler.__init__(self)

    def startElement(self, name, attrs):
        post = SOHandler.startElement(self, name, attrs)
        if post is None or not post['question']:
            return
        for t1 in post['tags']:
            for t2 in post['tags']:
                self.matrix.loc[t1, t2] += 1


def adjacency_matrix():
    return parse(AdjacencyHandler).matrix


def read_adjacency_matrix(fname):
    reader = csv.reader(open(fname))
    names = reader.next()[1:]
    # somehow float assignment + int conversion is faster
    # https://stackoverflow.com/questions/41644059/
    df = pd.DataFrame(0, dtype=np.float32, columns=names, index=names)
    for row in reader:
        tag = row[0]
        df.loc[tag] = np.array(row[1:], dtype=np.float32)
    return df.astype(np.int32)
