#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import datetime


def unix2str(timestamp, fmt="%Y-%m-%d %H:%M"):
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime(fmt)


def utf8fy(str):
    try:
        return str.encode('utf8')
    except UnicodeDecodeError:
        return '*Garbled*'


if __name__ == '__main__':
    import os
    import sys
    import argparse

    columns = ['hexsha', 'deletions', 'insertions', 'lines', 'files',
               'author.name', 'author.email', 'authored.date', 'authored.unixts',
               'committer.name', 'committer.email', 'committed.date',
               'committed.unixts',
               'seconds.till.next.commit', 'message', 'compressed.size']

    parser = argparse.ArgumentParser(
        description="Export git commits from a repository to a CSV file.\n"
                    "   CSV file columns:\n" + ", ".join(columns) )

    parser.add_argument('repo_path', default=os.getcwd(), nargs='?',
                        help='path to repository, default: current dir')

    parser.add_argument('-s', '--short-message', action='store_true',
                        help='store only first line of commit message')

    parser.add_argument('-n', '--max_count', default=-1,
                        help='store only last N commits, default for no limit')

    parser.add_argument('-i', '--item', default='master',
                        help='Item to iterate. Could be a branch name, commit '
                             'hash (parent commits will be iterated), or tag.')

    args = parser.parse_args()

    if not os.path.isdir(args.repo_path):
        parser.exit(1, "path is not a directory to git repository (not a dir)")

    try:
        import git
    except ImportError:
        parser.exit(2, "please install GitPython:\n"
                       "    pip install gitpython")

    try:
        repo = git.Repo(args.repo_path)
    except git.InvalidGitRepositoryError:
        parser.exit(1, "path is not a directory to a git repository "
                       "(not a repo)")

    writer = csv.DictWriter(sys.stdout, columns)
    writer.writeheader()
    last_commits = {}

    for commit in repo.iter_commits(args.item, max_count=-1):
        if not hasattr(commit, 'author') or \
                not hasattr(commit, 'committed_date'):
            # WTF? example:
            # https://github.com/openssl/openssl/commit/c753e71e0a0aea2c540dab96fb02c9c62c6ba7a2
            sys.stderr.write(commit.hexsha + "\n")
            continue

        if not commit.author.email:  # sometimes None
            commit.author.email = ''
            # these commits do not contribute to stats as it is not possible
            # to identify the author
            continue
        elif commit.author.email in last_commits:
            time_till_next_commit = \
                last_commits[commit.author.email] - commit.committed_date
        else:
            time_till_next_commit = ''

        last_commits[commit.author.email] = commit.committed_date

        message = commit.message.strip()
        if args.short_message:
            message = message.split("\n", 1)[0].strip()

        writer.writerow({
            'hexsha': commit.hexsha,
            'deletions': commit.stats.total['deletions'],
            'insertions': commit.stats.total['insertions'],
            'lines': commit.stats.total['lines'],
            'files': commit.stats.total['files'],
            'author.name': utf8fy(commit.author.name),
            'author.email': utf8fy(commit.author.email),
            'authored.unixts': commit.authored_date,
            'authored.date': unix2str(commit.authored_date),
            'committer.name': utf8fy(commit.committer.name),
            'committer.email': utf8fy(commit.committer.email),
            'committed.unixts': commit.committed_date,
            'committed.date': unix2str(commit.committed_date),
            'seconds.till.next.commit': time_till_next_commit,
            'message': utf8fy(message),
            'compressed.size': commit.size
        })
