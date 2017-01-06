
import logging

from django.core.management.base import BaseCommand, CommandError

from scraper import utils
from scraper import models


class Command(BaseCommand):
    help = 'Scrape arbitrary repository'

    def add_arguments(self, parser):
        parser.add_argument('repo', nargs='?',
                            help='Repository URL to override the queue')

    def handle(self, *args, **options):
        logging.basicConfig(
            format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
        logger = logging.getLogger('ghd.scraper.utils')
        logger.setLevel(40 - 10*options['verbosity'])

        repo = None
        if options.get('repo'):
            try:
                repo = models.Repo.objects.get(pk=int(options['repo']))
            except ValueError:
                repo_urls, new = utils.create_repos([options['repo']])
                repo = repo_urls[0]  # might through IndexError if invalid url
            except models.Repo.DoesNotExist:
                raise CommandError('Repository with the specified id ({}) '
                                   'does not exist'.format(options['repo']))

        err, message = utils.scrape(repo=repo)
        if err:
            raise CommandError(message)

        return message
