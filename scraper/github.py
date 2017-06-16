
import requests
import time
import json

import settings


class API(object):
    """ This is a convenience class to pool GitHub API keys and update their
    limits after every request. Actual work is done by outside classes, such
    as _IssueIterator and _CommitIterator
    """
    _instance = None
    api_url = "https://api.github.com/"
    api_v4_url = api_url + "graphql"

    tokens = None  # token: remaining limit, reset timestamp

    def __new__(cls, *args, **kwargs):
        # basic Singleton implementation
        if not isinstance(cls._instance, cls):
            cls._instance = super(API, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, tokens=None):
        tokens = tokens or settings.SCRAPER_GITHUB_API_TOKENS
        self.tokens = {t: (None, None) for t in tokens}

    def _request(self, url, method='get', data=None, **params):
        """ Generic, API version agnostic request method """
        while True:
            for token, (remaining, reset_time) in self.tokens.items():
                if remaining == 0 and reset_time < time.time():
                    continue  # try another token
                # Exact API version can be specified by Accept header:
                # "Accept": "application/vnd.github.v3+json"}
                r = requests.request(method, url, data=data, params=params,
                                     headers={"Authorization": "token " + token})

                if 'X-RateLimit-Remaining' in r.headers:
                    remaining = int(r.headers['X-RateLimit-Remaining'])
                    reset_time = int(r.headers['X-RateLimit-Reset'])
                    self.tokens[token] = (remaining, reset_time)
                    if r.status_code == 403 and remaining == 0:
                        continue  # retry with another token

                r.raise_for_status()
                return r.json()

            next_res = min(reset_time for _, reset_time in self.tokens.values())
            sleep = int(next_res - time.time()) + 1
            if sleep > 0:
                time.sleep(sleep)

    def v3(self, url, method='get', data=None, **params):
        return self._request(self.api_url + url, method, data, **params)

    def v4(self, query, **params):
        payload = json.dumps({"query": query, "variables": params})
        return self._request(self.api_v4_url, 'post', payload)

    def repo_issues(self, repo_name, page=None):
        url = "repos/%s/issues" % repo_name
        page = page or 1
        while True:
            data = self.v3(url, per_page=100, page=page, state='all')
            if not data:
                break

            for issue in data:
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
            if not data:  # repository deleted or moved
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

    def repo_commits(self, repo_name, page=None):
        url = "repos/%s/commits" % repo_name
        page = page or 1
        while True:
            data = self.v3(url, per_page=100, page=page)
            if not data:
                # no commits or page is too high. Last call could be saved  by
                # checking response.headers['Link'], but it'll violate the
                # abstraction
                break

            for commit in data:
                yield {
                    'sha': commit['sha'],
                    'author': commit['author']['login'],
                    'author_name': commit['commit']['author']['name'],
                    'author_email': commit['commit']['author']['email'],
                    'authored_date': commit['commit']['author']['date'],
                    'message': commit['commit']['message'],
                    'committed_date': commit['commit']['committer']['date'],
                    'parents': "\n".join(p['sha'] for p in commit['parents']),
                    'verified': commit.get('verification', {}).get('verified')
                }
            page += 1

    def repo_commits_v4(self, repo_name, cursor=None):
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
