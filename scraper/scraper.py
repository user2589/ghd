#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import argparse
import tempfile
import pygit2
import re
import shutil


def get_repo_name(repo_url):
    assert(repo_url.endswith(".git"))
    chunks = [c for c in re.split("[:/]", repo_url[:-4]) if c]
    org = "" if len(chunks) < 2 else chunks[-2]
    repo = chunks[-1]
    return org, repo


def get_commits(repo_url):
    org, repo_name = get_repo_name(repo_url)
    folder = tempfile.mkdtemp(prefix='_'.join(('ghd', org, repo_name, '')))
    repo = pygit2.clone_repository(repo_url, folder, bare=True)

    commits = []
    try:
        for commit in repo.walk(repo.head.target):
            # http://www.pygit2.org/objects.html#commits
            deletions = insertions = files = None
            fstats = []  # detailed per-file delta stats
            if len(commit.parent_ids) == 1:
                diff = repo.diff(str(commit.oid), str(commit.parent_ids[0]))
                diff.find_similar()  # handle renamed files
                deletions = diff.stats.deletions
                insertions = diff.stats.insertions
                files = diff.stats.files_changed
                fstats = {p.delta.new_file.path: p.line_stats
                          for p in list(diff)}
            commits.append({
                'sha': commit.oid,
                'author': commit.author.name,
                'author_email': commit.author.email,
                'committer': commit.committer.name,
                'committer_email': commit.committer.email,
                'message': commit.message.strip(),
                'parent_ids': "\n".join(str(pid) for pid in commit.parent_ids),
                'time': commit.commit_time,
                'del': deletions,
                'ins': insertions,
                'files': files,
                'fstats': fstats,
            })
    finally:
        os.chdir('/tmp')
        shutil.rmtree(folder)

    return commits

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Retrieve commit information using libgit2")
    parser.add_argument(
        'url', help='repo url to scrape, e.g. git://github.com/user/repo.git')
    args = parser.parse_args()

    import sys, csv

    writer = csv.DictWriter(
        sys.stdout,
        ['sha', 'author', 'author_email', 'committer', 'committer_email',
         'message', 'parent_ids', 'time', 'del', 'ins', 'files', 'fstats'])
    writer.writeheader()

    writer.writerows(get_commits(args.url))
