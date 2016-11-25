
from django.core.management.base import BaseCommand, CommandError

from scraper import utils
from scraper import models


class Command(BaseCommand):
    help = 'Scrape arbitrary repository'

    def handle(self, *args, **options):
        err, message = utils.scrape()
        if err:
            raise CommandError(message)

        return message
