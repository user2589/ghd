
import requests
import time
from datetime import datetime
import json
import logging
from typing import Iterable

try:
    import settings
except ImportError:
    settings = object()

_tokens = getattr(settings, "SCRAPER_GITHUB_API_TOKENS", [])

logger = logging.getLogger('ghd.scraper')


class RepoDoesNotExist(requests.HTTPError):
    pass


class GitHubAPI(object):
    """ This is a convenience class to pool GitHub API keys and update their
    limits after every request. Actual work is done by outside classes, such
    as _IssueIterator and _CommitIterator
    """
    _instance = None  # instance of API() for Singleton pattern implementation
    api_url = "https://api.github.com/"
    api_v4_url = api_url + "graphql"

    tokens = None  # token: remaining limit, reset timestamp
    usernames = {}  # token: username, checked in check/limits

    def __new__(cls):
        # basic Singleton implementation
        if not isinstance(cls._instance, cls):
            cls._instance = super(GitHubAPI, cls).__new__(cls)
        return cls._instance

    def __init__(self, tokens=_tokens, timeout=30):
        if not tokens:
            raise EnvironmentError("No GitHub API tokens found in settings.py."
                                   "Please add some.")
        self.timeout = timeout
        self.tokens = {t: (None, None) for t in tokens}

    def _request(self, url, method='get', data=None, **params):
        # type: (str, str, str) -> dict
        """ Generic, API version agnostic request method """
        # TODO: use coroutines, perhaps Tornado (as PY2/3 compatible)
        while True:
            # TODO: sort keys to use next to expire first
            for token, (remaining, reset_time) in self.tokens.items():
                if remaining == 0 and reset_time > time.time():
                    continue  # try another token
                # Exact API version can be specified by Accept header:
                # "Accept": "application/vnd.github.v3+json"}
                try:
                    r = requests.request(
                        method, url, params=params, timeout=self.timeout,
                        data=data, headers={"Authorization": "token " + token})
                except requests.exceptions.Timeout:
                    continue  # i.e. try again

                if 'X-RateLimit-Remaining' in r.headers:
                    remaining = int(r.headers['X-RateLimit-Remaining'])
                    reset_time = int(r.headers['X-RateLimit-Reset'])
                    self.tokens[token] = (remaining, reset_time)
                    if r.status_code == 403 and remaining == 0:
                        continue  # retry with another token

                if r.status_code in (404, 451):  # API v3 only
                    raise RepoDoesNotExist
                elif r.status_code == 409:
                    # repository is empty https://developer.github.com/v3/git/
                    return {}
                r.raise_for_status()
                return r.json()

            next_res = min(reset_time for _, reset_time in self.tokens.values()
                           if reset_time is not None)
            sleep = int(next_res - time.time()) + 1
            if sleep > 0:
                logger.info(
                    "%s: out of keys, resuming in %d minutes, %d seconds",
                    datetime.now().strftime("%H:%M"), *divmod(sleep, 60))
                time.sleep(sleep)
                logger.info(".. resumed")

    def v3(self, url, method='get', data=None, **params):
        # type: (str, str, str) -> Iterable[dict]
        return self._request(self.api_url + url, method, data, **params)

    def v4(self, query, **params):
        # type: (str) -> Iterable[dict]
        payload = json.dumps({"query": query, "variables": params})
        return self._request(self.api_v4_url, 'post', payload)

    def check_limits(self):
        # type: () -> dict
        for token in self.tokens:
            r = requests.get(self.api_url + "user",
                             headers={"Authorization": "token " + token})
            remaining = int(r.headers.get('X-RateLimit-Remaining', 0))
            reset_time = r.headers.get('X-RateLimit-Reset')
            if reset_time is not None:  # otherwise prevent from using
                reset_time = int(reset_time)
            self.tokens[token] = (remaining, reset_time)
            self.usernames[token] = r.json().get('login', "<unknown>")

        return self.tokens

    def repo_issues(self, repo_name, page=1):
        # type: (str, int) -> Iterable[dict]
        url = "repos/%s/issues" % repo_name
        while True:
            try:
                data = self.v3(url, per_page=100, page=page, state='all')
            except RepoDoesNotExist:  # repository not found
                break

            if not data:
                break

            for issue in data:
                if 'pull_request' not in issue:
                    yield {
                        'author': issue['user']['login'],
                        'closed': issue['state'] != "open",
                        'created_at': issue['created_at'],
                        'updated_at': issue['updated_at'],
                        'closed_at': issue['closed_at'],
                        'number': issue['number'],
                        'title': issue['title']
                    }
            page += 1

    def repo_issues_v4(self, repo_name, cursor=None):
        # type: (str, str) -> Iterable[dict]
        owner, repo = repo_name.split("/")
        query = """query ($owner: String!, $repo: String!, $cursor: String) {
        repository(name: $repo, owner: $owner) {
          hasIssuesEnabled
            issues (first: 100, after: $cursor, 
              orderBy: {field:CREATED_AT, direction: ASC}) {
                nodes {author {login}, closed, createdAt, 
                       updatedAt, number, title}
                pageInfo {endCursor, hasNextPage}
        }}}"""

        while True:
            data = self.v4(query, owner=owner, repo=repo, cursor=cursor
                           )['data']['repository']
            if not data:  # repository is empty, deleted or moved
                break

            for issue in data["issues"]:
                yield {
                    'author': issue['author']['login'],
                    'closed': issue['closed'],
                    'created_at': issue['createdAt'],
                    'updated_at': issue['updatedAt'],
                    'closed_at': None,
                    'number': issue['number'],
                    'title': issue['title']
                }

            cursor = data["issues"]["pageInfo"]["endCursor"]

            if not data["issues"]["pageInfo"]["hasNextPage"]:
                break

    def repo_commits(self, repo_name, page=1):
        # type: (str, int) -> Iterable[dict]
        # check repo_name follows pattern %owner/%repo
        _, _ = repo_name.split("/")
        url = "repos/%s/commits" % repo_name
        while True:
            try:
                data = self.v3(url, per_page=100, page=page)
            except RepoDoesNotExist:
                break

            if not data:
                # no commits or page is too high. Last call could be saved  by
                # checking response.headers['Link'], but it'll violate the
                # abstraction
                break

            for commit in data:
                # might be None for commits authored outside of github
                github_author = commit['author'] or {}
                commit_author = commit['commit'].get('author') or {}
                yield {
                    'sha': commit['sha'],
                    'author': github_author.get('login'),
                    'author_name': commit_author.get('name'),
                    'author_email': commit_author.get('email'),
                    'authored_date': commit_author.get('date'),
                    'message': commit['commit']['message'],
                    'committed_date': commit['commit']['committer']['date'],
                    'parents': "\n".join(p['sha'] for p in commit['parents']),
                    'verified': commit.get('verification', {}).get('verified')
                }
            page += 1

    def repo_commits_v4(self, repo_name, cursor=None):
        # type: (str, str) -> Iterable[dict]
        """As of June 2017 GraphQL API does not allow to get commit parents
        Until this issue is fixed this method is only left for a reference
        Please use commits() instead"""
        owner, repo = repo_name.split("/")
        query = """query ($owner: String!, $repo: String!, $cursor: String) {
        repository(name: $repo, owner: $owner) {
          ref(qualifiedName: "master") {
            target { ... on Commit {
              history (first: 100, after: $cursor) {
                nodes {sha:oid, author {name, email, user{login}}
                       message, committedDate}
                pageInfo {endCursor, hasNextPage}
        }}}}}}"""

        while True:
            data = self.v4(query, owner=owner, repo=repo, cursor=cursor
                           )['data']['repository']
            if not data:
                break

            for commit in data["ref"]["target"]["history"]["nodes"]:
                yield {
                    'sha': commit['sha'],
                    'author': commit['author']['user']['login'],
                    'author_name': commit['author']['name'],
                    'author_email': commit['author']['email'],
                    'authored_date': None,
                    'message': commit['message'],
                    'committed_date': commit['committedDate'],
                    'parents': None,
                    'verified': None
                }

            cursor = data["ref"]["target"]["history"]["pageInfo"]["endCursor"]
            if not data["ref"]["target"]["history"]["pageInfo"]["hasNextPage"]:
                break

    @staticmethod
    def activity(repo_name):
        # type: (str) -> dict
        url = "https://github.com/%s/graphs/contributors" % repo_name
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept-Encoding': "gzip,deflate,br",
            'Accept': "application/json",
            'Origin': 'https://github.com',
            'Referer': url,
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) "
                          "Gecko/20100101 Firefox/53.0",
            "Host": 'github.com',
            "Accept-Language": 'en-US,en;q=0.5',
            "Connection": "keep-alive",
            "Cache-Control": 'max-age=0',
        }
        cookies = requests.get(url).cookies
        r = requests.get(url + "-data", cookies=cookies, headers=headers)
        r.raise_for_status()
        return r.json()
