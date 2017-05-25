
from __future__ import unicode_literals

from django.db import models
from django.contrib.postgres.fields import JSONField


class Snapshot(models.Model):
    """ A snapshot of package information obtained via PyPi API
    """
    package = models.CharField(db_index=True, max_length=255)
    date_accessed = models.DateTimeField(auto_created=True)
    info = JSONField()


