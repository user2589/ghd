
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


class TokenNotReady(requests.HTTPError):
    pass


class GitHubAPIToken(object):
    api_url = "https://api.github.com/"

    token = None
    timeout = None
    _user = None
    _headers = None

    limit = None  # see __init__ for more details

    def __init__(self, token=None, timeout=None):
        if token is not None:
            self.token = token
            self._headers = {"Authorization": "token " + token}
        self.limit = {}
        for api_class in ('core', 'search'):
            self.limit[api_class] = {
                'limit': None,
                'remaining': None,
                'reset_time': None
            }
        self.timeout = timeout
        super(GitHubAPIToken, self).__init__()

    @property
    def user(self):
        if self._user is None:
            r = self.request('user')
            self._user = r.json().get('login', '')
        return self._user

    def _check_limits(self):
        # regular limits will be updaated automatically upon request
        # we only need to take care about search limit
        s = self.request('rate_limit').json()['resources']['search']
        self.limit['search'] = {
            'remaining': s['remaining'],
            'reset_time': s['reset'],
            'limit': s['limit']
        }

    @staticmethod
    def api_class(url):
        return 'search' if url.startswith('search') else 'core'

    def ready(self, url):
        t = self.when(url)
        return not t or t <= time.time()

    def legit(self):
        if self.limit['core']['limit'] is None:
            self._check_limits()
        return self.limit['core']['limit'] < 100

    def when(self, url):
        key = self.api_class(url)
        if self.limit[key]['remaining'] != 0:
            return 0
        return self.limit[key]['reset_time']

    def request(self, url, method='get', data=None, **params):
        # TODO: use coroutines, perhaps Tornado (as PY2/3 compatible)

        if not self.ready(url):
            raise TokenNotReady
        # Exact API version can be specified by Accept header:
        # "Accept": "application/vnd.github.v3+json"}

        # might throw a timeout
        r = requests.request(
            method, self.api_url + url, params=params, data=data,
            headers=self._headers,  timeout=self.timeout)

        if 'X-RateLimit-Remaining' in r.headers:
            remaining = int(r.headers['X-RateLimit-Remaining'])
            self.limit[self.api_class(url)] = {
                'remaining': remaining,
                'reset_time': int(r.headers['X-RateLimit-Reset']),
                'limit': int(r.headers['X-RateLimit-Limit'])
            }

            if r.status_code == 403 and remaining == 0:
                raise TokenNotReady
        return r


class GitHubAPI(object):
    """ This is a convenience class to pool GitHub API keys and update their
    limits after every request. Actual work is done by outside classes, such
    as _IssueIterator and _CommitIterator
    """
    _instance = None  # instance of API() for Singleton pattern implementation
    tokens = None

    def __new__(cls):  # Singleton
        if not isinstance(cls._instance, cls):
            cls._instance = super(GitHubAPI, cls).__new__(cls)
        return cls._instance

    def __init__(self, tokens=_tokens, timeout=30):
        if not tokens:
            raise EnvironmentError(
                "No GitHub API tokens found in settings.py. Please add some.")
        self.tokens = [GitHubAPIToken(t, timeout=timeout) for t in tokens]

    def request(self, url, method='get', paginate=False, data=None, **params):
        # type: (str, str, bool, str) -> dict
        """ Generic, API version agnostic request method """
        timeout_counter = 0
        if paginate:
            paginated_res = []
            params['page'] = 1
            params['per_page'] = 100

        while True:
            for token in sorted(self.tokens, key=lambda t: t.when(url)):
                if not token.ready(url):
                    continue

                try:
                    r = token.request(url, method=method, data=data, **params)
                except TokenNotReady:
                    continue
                except requests.exceptions.Timeout:
                    timeout_counter += 1
                    if timeout_counter > len(self.tokens):
                        raise
                    continue  # i.e. try again

                if r.status_code in (404, 451):  # API v3 only
                    raise RepoDoesNotExist(
                        "GH API returned status %s" % r.status_code)
                elif r.status_code == 409:
                    # repository is empty https://developer.github.com/v3/git/
                    return {}
                r.raise_for_status()
                res = r.json()
                if paginate:
                    paginated_res.extend(res)
                    has_next = 'rel="next"' in r.headers.get("Link", "")
                    if not res or not has_next:
                        return paginated_res
                    else:
                        params["page"] += 1
                        continue
                else:
                    return res

            next_res = min(token.when(url) for token in self.tokens)
            sleep = int(next_res - time.time()) + 1
            if sleep > 0:
                logger.info(
                    "%s: out of keys, resuming in %d minutes, %d seconds",
                    datetime.now().strftime("%H:%M"), *divmod(sleep, 60))
                time.sleep(sleep)
                logger.info(".. resumed")

    def repo_issues(self, repo_name, page=None):
        # type: (str, int) -> Iterable[dict]
        url = "repos/%s/issues" % repo_name

        # might throw RepoDoesNotExist
        if page is None:
            data = self.request(url, paginate=True, state='all')
        else:
            data = self.request(url, page=page, per_page=100, state='all')

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

    def repo_commits(self, repo_name, page=None):
        # type: (str, int) -> Iterable[dict]
        # check repo_name follows pattern %owner/%repo
        _, _ = repo_name.split("/")
        url = "repos/%s/commits" % repo_name

        # might throw RepoDoesNotExist
        if page is None:
            data = self.request(url, paginate=True)
        else:
            data = self.request(url, page=page, per_page=100)

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

    def user_info(self, user):
        # TODO: support pagination
        # might throw RepoDoesNotExist:
        # Docs: https://developer.github.com/v3/users/#response
        return self.request("users/" + user)

    def org_members(self, org):
        # TODO: support pagination
        return self.request("orgs/%s/members" % org)

    def user_orgs(self, user):
        # TODO: support pagination
        return self.request("users/%s/orgs" % user)

    @staticmethod
    def activity(repo_name):
        # type: (str) -> dict
        """Unofficial method to get top 100 contributors commits by week"""
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


class GitHubAPIv4(GitHubAPI):

    def v4(self, query, **params):
        # type: (str) -> dict
        payload = json.dumps({"query": query, "variables": params})
        return self.request("graphql", 'post', data=payload)

    def repo_issues(self, repo_name, cursor=None):
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

    def repo_commits(self, repo_name, cursor=None):
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
