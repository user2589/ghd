
import re

from ghtorrent import models as ght_models
import models


def format_res(scheduled, total):
    return '%(scheduled)s out of %(total)s repos scheduled' % \
           {'scheduled': scheduled, 'total': total}


def create_repos(urls):
    new = 0
    repos = []
    for repo_url in urls:
        repo_url = repo_url.strip()
        if not repo_url:
            continue
        if re.match("[a-zA-Z0-9_-]{1,40}/[a-zA-Z0-9_-]{1,100}", repo_url):
            repo_url = "git://github.com/%(gh_url)s.git" % {'gh_url': repo_url}
        repo, created = models.Repo.objects.get_or_create(url=repo_url)
        repos.append(repo)
        new += created
    return repos, new


def queue_repos(urls):
    repos, scheduled = create_repos(urls)
    return scheduled, len(repos)


def queue_user(login):
    try:
        ght_user = ght_models.User.objects.get(login=login)
    except ght_models.User.DoesNotExist:
        raise ValueError

    if ght_user.type == 'organization':
        return 0, 0

    user, created = models.User.objects.get_or_create(login=login)
    gh_urls = ght_models.Project.objects.filter(
        commits__author__id=ght_user.id).distinct(
        ).values_list('url', flat=True)

    repos, scheduled = create_repos(gh_urls)
    user.repos.add(*repos)
    user.update_project_count()
    user.status = 1  # started
    return scheduled, len(repos)


def scrape():
    # usually this method is called for one repo only
    import scraper
    import pygit2
    import datetime
    import time
    import json

    # select repository to scrape
    repo = models.Repo.objects.filter(status=0).first()
    if repo is None:
        two_hrs_ago = datetime.datetime.now() - datetime.timedelta(hours=2)
        repo = models.Repo.objects.filter(
            status=1, last_updated__lt=two_hrs_ago).first()
    if repo is None:
        return 0, "Nothing to do"

    # scrape
    # this is generator, no exceptions will be thrown
    commits = scraper.get_commits(repo.url)
    repo.status = 1  # started
    repo.save()

    try:
        for cd in commits:
            if models.Commit.objects.filter(sha=cd['sha']).exists():
                continue

            commit = models.Commit(sha=cd['sha'])

            # TODO: get list of commits before hand and use dict to check
            try:
                ght_commit = ght_models.Commit.objects.get(sha=cd['sha'])
            except ght_models.Commit.DoesNotExist:
                author = None
                committer = None
            else:
                author, created = models.User.objects.get_or_create(
                    login=ght_commit.author.login)
                committer, created = models.User.objects.get_or_create(
                    login=ght_commit.committer.login)

            headline = cd['message'].split("\n", 1)[0][:255]
            timestamp = datetime.datetime.fromtimestamp(cd['time'])

            commit.repo = repo
            commit.author_name = cd['author']
            commit.author_email = cd['author_email']
            commit.committer_name = cd['committer']
            commit.committer_email = cd['committer_email']
            commit.merge = len(cd['parent_ids']) > 42
            commit.headline = headline
            commit.full_message = cd['message']
            commit.created_at = timestamp
            commit.inserted = cd['ins']
            commit.deleted = cd['del']
            commit.files = cd['files']
            commit.file_stats = json.dumps(cd['fstats'])
            commit.author = author
            commit.committer = committer
            commit.parents = cd['parent_ids']
            commit.save()
        err = 0
        message = "Done: {url}".format(url=repo.url)
        repo.status = 31  # done

    except pygit2.GitError as e:
        repo.log = str(e)
        repo.status = 30  # deleted
        return 1, 'Failed to clone repository {url}'.format(url=repo.url)

    except Exception as e:
        repo.log = "Error: {e} on repo {url}".format(e=str(e), url=repo.url)
        repo.status = 2  # scrape error
        raise e

    finally:
        repo.save()

    # update users involved
    for user in repo.users.all():
        user.update_project_count()

    return err, message
