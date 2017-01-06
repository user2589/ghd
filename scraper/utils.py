
import re
import logging

from ghtorrent import models as ght_models
import models

logger = logging.getLogger('ghd.scraper.utils')


def format_res(scheduled, total):
    return '%(scheduled)s out of %(total)s repos scheduled' % \
           {'scheduled': scheduled, 'total': total}


def create_repos(urls):
    new = 0
    repos = []
    for repo_url in urls:
        repo_url = repo_url.strip()
        if not repo_url:
            logger.info('Empty repository url, ignored')
            continue

        if '/' not in repo_url:
            logger.warning('Invalid repo url, ignored: %s', repo_url)
            continue

        if re.match("[a-zA-Z0-9_-]{1,40}/[a-zA-Z0-9_.-]{1,100}$", repo_url):
            repo_url = "git://github.com/%(gh_url)s.git" % {'gh_url': repo_url}

        repo, created = models.Repo.objects.get_or_create(url=repo_url)

        if created:
            logger.debug("New repo scheduled for scraping: %s", repo_url)
        else:
            logger.debug("Repo already scheduled, ignored: %s", repo_url)

        repos.append(repo)
        new += created
    logger.debug("Total %s new repos scheduled out of %s", len(repos), new)
    return repos, new


def queue_user(login):
    try:
        ght_user = ght_models.User.objects.get(login=login)
    except ght_models.User.DoesNotExist:
        # TODO: add github api fallback
        logger.warning("User is not in GHTorrent, ignored: %s", login)
        return 0, 0

    if ght_user.type == 'organization':
        logger.warning("The specified login belongs to an organization, "
                       "ignored: %s", login)
        return 0, 0

    user, created = models.User.objects.get_or_create(login=login)
    gh_urls = ght_models.Project.objects.filter(
        commits__author__id=ght_user.id).distinct(
        ).values_list('url', flat=True)
    logger.debug("%s repositories discovered in GHTorrent commits history",
                 len(gh_urls))

    repos, scheduled = create_repos(gh_urls)
    user.repos.add(*repos)
    user.status = 1  # started
    user.update_project_count()  # will also save changes
    return scheduled, len(repos)


def scrape(repo=None):
    # usually this method is called for one repo only
    import scraper
    import pygit2
    import datetime
    import time
    import json

    start_time = time.time()
    # select repository to scrape
    if not repo:
        repo = models.Repo.objects.filter(status=0).first()
        if repo is None:
            two_hrs_ago = datetime.datetime.now() - datetime.timedelta(hours=2)
            repo = models.Repo.objects.filter(
                status=1, last_updated__lt=two_hrs_ago).first()
        if repo is None:
            logger.debug("No repositories to scrape, quit")
            return 0, ""
        else:
            logger.debug("Scraping an autoselected repo: %s", repo.url)
    else:
        logger.debug("Scraping the specified repo: %s", repo.url)

    # scrape
    # this is generator, no exceptions will be thrown
    repo.status = 1  # started
    repo.save()

    logger.debug(".. cloning repository to collect commits")
    try:
        commits = scraper.get_commits(repo.url)
    except pygit2.GitError as e:
        repo.log = str(e)
        repo.status = 30  # deleted
        repo.save()
        return 1, 'Failed to clone repository {url}'.format(url=repo.url)
    except Exception as e:
        msg = "Error scraping {url}: {e}".format(e=str(e), url=repo.url)
        repo.log = msg[:255]
        repo.status = 2  # scrape error
        repo.save()
        raise e

    logger.debug(".. updating commits")
    processed_commits = 0
    total_commits = len(commits)
    ght_commits = 0
    for cd in commits:
        if models.Commit.objects.filter(sha=cd['sha']).exists():
            continue

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
            ght_commits += 1

        headline = cd['message'].split("\n", 1)[0][:255]
        timestamp = datetime.datetime.fromtimestamp(cd['time'])
        if len(cd['parent_ids']) > 250:
            cd['parent_ids'] = cd['parent_ids'][:250] + ', ...'

        commit = models.Commit(  # what a mess
            sha=cd['sha'], repo=repo, author_name=cd['author'],
            author_email=cd['author_email'], committer_name=cd['committer'],
            committer_email=cd['committer_email'],
            merge=len(cd['parent_ids']) > 42, headline=headline,
            full_message=cd['message'], created_at=timestamp,
            inserted=cd['ins'], deleted=cd['del'], files=cd['files'],
            file_stats=json.dumps(cd['fstats']), author=author,
            committer=committer, parents=cd['parent_ids']
        )
        # MySQL doesn't support 4-byte unicode in utf, so this will fail
        # sometimes. It is possible to work around with
        # ALTER TABLE scraper_commit CONVERT TO CHARACTER SET utf8mb4;
        # but who knows how much time it will take
        # also see the commented part in local_settings.db.options
        commit.save()
        processed_commits += 1

    err = 0
    message = "Done: {url}".format(url=repo.url)
    repo.status = 31  # done
    repo.save()

    # update users involved
    logger.debug(".. updating repo contributors status")
    for user in repo.users.all():
        user.update_project_count()

    end_time = time.time()

    logger.debug("... SCRAPING COMPLETE, %s cps",
                 float(processed_commits/(end_time - start_time)))
    logger.debug("Scraping stats: %s total commits, %s processed, %s GHT hits",
                 total_commits, processed_commits, ght_commits)
    return err, message
