#!/usr/bin/env python

import datetime


def unix2str(timestamp, fmt="%Y-%m-%d %H:%M"):
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime(fmt)


def utf8fy(str):
    try:
        return str.encode('utf8')
    except UnicodeDecodeError:
        return '*Garbled*'


def commits_gitpython(repo_path, ref='master', short_message=False):
    """ Parse commits from a cloned git repository using gitphython
    This is a rather slow method since gitpython simply parses cli output of
    native git client
    """
    import git

    try:
        repo = git.Repo(repo_path)
    except git.InvalidGitRepositoryError:
        raise ValueError("Not a git repository: %s" % repo_path)

    for commit in repo.iter_commits(ref, max_count=-1):
        # WTF? example:
        # https://github.com/openssl/openssl/commit/c753e71e0a0aea2c540dab96fb02c9c62c6ba7a2
        hasauthor = hasattr(commit, 'author') or None
        hasdate = hasattr(commit, 'committed_date') or None

        message = commit.message.strip()
        if short_message:
            message = message.split("\n", 1)[0].strip()

        yield {
            'sha': commit.hexsha,
            'deletions': commit.stats.total['deletions'],
            'insertions': commit.stats.total['insertions'],
            'lines': commit.stats.total['lines'],
            'files': commit.stats.total['files'],
            'author.name': hasauthor and utf8fy(commit.author.name),
            'author.email': hasauthor and utf8fy(commit.author.email),
            'authored.unixts': hasauthor and commit.authored_date,
            'authored.date': hasauthor and unix2str(commit.authored_date),
            'committer.name': utf8fy(commit.committer.name),
            'committer.email': utf8fy(commit.committer.email),
            'committed.unixts': hasdate and commit.committed_date,
            'committed.date': hasdate and unix2str(commit.committed_date),
            'message': utf8fy(message),
            'compressed.size': commit.size
        }


def issues_PyGithub(github_token, repo_name):
    """ Iterate issues of a GitHub repository using GitHub API v3
    The library used in this method, PyGithub tries to extensively resolve
    attributes which leads to a number of excessive API calls and computation
    overhead. This implementation tries to avoid this, and was replaced by
    local implementation to have uniform interface and get rid of dependency
    """
    # this is not the same module included with scraper.
    # to install, `pip install PyGithub`
    import github

    g = github.Github(github_token)
    repo = g.get_repo(repo_name)
    try:
        id = repo.id
    except github.GithubException:
        raise ValueError("Repository %s does not exist" % repo_name)

    issues = repo.get_issues(state='all')

    # Response example:
    # https://api.github.com/repos/pandas-dev/pandas/issues?page=62
    for issue in issues:
        raw = issue._rawData  # to prevent resolving usernames into objects
        yield {
            'id': int(raw['id']),
            'title': raw['title'],
            'user': raw['user']['login'],
            'labels': ",".join(l['name'] for l in raw['labels']),
            'state': raw['state'],
            'created_at': raw['created_at'],
            'updated_at': raw['updated_at'],
            'closed_at': raw['closed_at'],
            'body': raw['body']
        }
