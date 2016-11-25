#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script processes stackoverflow dump obtained from stackexchange dump
and produces a set of CSV files suitable for use with mysqlimport

The StackExchange data dump can be downloaded here:
    https://archive.org/details/stackexchange


"""

import sys
import argparse
import csv
import xml.sax
import re

PY3 = sys.version_info > (3,)


def iNone(attr):
    try:
        return int(attr)
    except (ValueError, TypeError) as e:
        return None


class DictWriter(object):
    # custom writer with utf8 conversion for Python 2
    init = False

    def _escape(self, value):
        return re.sub('([\\\\"])', "\\\\\\1", value)

    def _convert(self, value):
        if isinstance(value, basestring):
            return '"{}"'.format(self._escape(value.encode('utf8')))
        elif value is None:
            return ''
        return str(value)

    def _convert3(self, value):
        if isinstance(value, bytes):
            return '"{}"'.format(self._escape(value.decode('utf8')))
        if isinstance(value, str):
            return '"{}"'.format(self._escape(value))
        elif value is None:
            return ''
        return str(value)

    def __init__(self, fh, fields):
        self.stream = fh
        self.fields = fields
        if PY3:
            self._convert = self._convert3

    def writerow(self, row):
        pass
        if not self.init:
            self.init = True
        else:
            self.stream.write("\r\n")

        for i, field in enumerate(self.fields):
            self.stream.write(self._convert(row[field]))
            self.stream.write(",")


class SOHandler(xml.sax.ContentHandler):

    writer = None
    tags_fname = None
    tagwriter_fname = None
    tagwriter = None
    tags = None

    def row_handler(self): pass

    def __init__(self, tags_fname=None, tagwriter_fname=None):
        self.writer = csv.writer(sys.stdout)
        self.tags_fname = tags_fname or "so_tag_names.csv"
        self.tagwriter_fname = tagwriter_fname or "tags.csv"
        # this is an old-style class, so explicit __init__ instead of super()
        xml.sax.ContentHandler.__init__(self)

    def _post_tags(self, tagline):
        """ example of a tag line:
        <c#><winforms><type-conversion><decimal><opacity>
        """
        return set([tag.lstrip("<") for tag in tagline.split(">") if tag])

    def _parse_post(self, attrs):
        post_id = int(attrs['Id'])
        is_question = int(attrs.get('PostTypeId') == "1")
        if is_question:
            for tag in self._post_tags(attrs.get('Tags')):
                tag_id = self.tags[tag]
                self.tagwriter.writerow({
                    'post_id': post_id,
                    'tag_id': tag_id
                })
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
        }

    def _parse_user(self, attrs):
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

    def _parse_tag(self, attrs):
        return {
            'id': int(attrs['Id']),
            'name': attrs['TagName'],
            'count': int(attrs.get('Count'), 0),
            'excerpt_post_id': iNone(attrs.get('ExcerptPostId')),
            'wiki_post_id': iNone(attrs.get('WikiPostId'))
        }

    def _parse_vote(self, attrs):
        return {
            'id': int(attrs['Id']),
            'post_id': attrs['PostId'],
            'vote_type': int(attrs.get('VoteTypeId')),
            'created_at': attrs['CreationDate']
        }

    def deferred_init(self, name):
        if name == 'posts':
            self.tags = {
                row[1]: int(row[0]) for row in csv.reader(
                    open(self.tags_fname, 'r'))}
            columns = ['id', 'question', 'title', 'body', 'owner_id',
                       'accepted_answer', 'created_at', 'score', 'parent_id',
                       'views', 'last_editor_id', 'last_edited_at',
                       'last_activity_at', 'community_owned_at',
                       'answers_count', 'comments_count', 'favorites_count']
            self.row_handler = self._parse_post
            self.tagwriter = DictWriter(
                open(self.tagwriter_fname, 'w'), ['post_id', 'tag_id'])
        elif name == 'users':
            columns = ['id', 'name', 'email_hash', 'reputation', 'created_at',
                       'website_url', 'location', 'age', 'views', 'upvotes',
                       'downvotes', 'about_me']
            self.row_handler = self._parse_user
        elif name == 'tags':
            columns = ['id', 'name', 'count', 'excerpt_post_id', 'wiki_post_id']
            self.row_handler = self._parse_tag
        elif name == 'votes':
            columns = ['id', 'post_id', 'vote_type', 'created_at']
            self.row_handler = self._parse_vote
        else:
            raise ValueError('posts, users, tags or votes tag expected')

        self.writer = DictWriter(sys.stdout, columns)

    def startElement(self, name, attrs):
        if name in ('posts', 'tags', 'users', 'votes'):
            self.deferred_init(name)
        elif name == 'row':  # ignore all other tags
            # if any(attrs.get(k) != v for k, v in self.filters.items()):
            #     return
            self.writer.writerow(self.row_handler(attrs))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Transform stackexchange dump to csv format. The script "
                    "accept XML file on standard input and prints CSV to "
                    "the standard output")
    args = parser.parse_args()

    parser = xml.sax.make_parser()
    parser.setContentHandler(SOHandler())
    parser.parse(sys.stdin)
    # parser.parse(open('Posts2200.xml', 'r'))  # sys.stdin)
