
import logging

logger = logging.getLogger('ghd.scraper.utils')


def scrape(repo=None):
    # usually this method is called for one repo only
    import scraper
    import pygit2
    import datetime
    import time
    import json

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
