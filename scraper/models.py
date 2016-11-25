
from __future__ import unicode_literals

from django.db import models
from django.utils.datastructures import DictWrapper


class FixedCharField(models.CharField):
    def db_type(self, connection):
        data = DictWrapper(self.__dict__, connection.ops.quote_name, "qn_")
        return 'char(%(max_length)s)' % data


STATUS_CHOICES = (
    (0, 'new'),
    (1, 'started'),
    (2, 'scraping error'),
    # Statuses over 16 are kind of successful
    (30, 'deleted'),
    (31, 'done'),
)


class Repo(models.Model):
    url = models.CharField(
        max_length=255, unique=True, help_text='Full url')
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, db_index=True, default=0)
    log = models.CharField(
        default='', max_length=140, help_text='error message')
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    languages = models.TextField(
        default='', help_text='Linguist stats')

    class Meta:
        ordering = ['last_updated']


class User(models.Model):
    """
    This model represents Github user. Users from repos outside of GitHub
    are either ignored (Commit.author is None) or mapped to existing GH user
    """
    # note, we do not support org accounts
    login = models.CharField(primary_key=True, max_length=40)
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, db_index=True, default=0)
    repos = models.ManyToManyField(Repo, related_name='users')
    total_repos = models.PositiveIntegerField(default=0)
    processed_repos = models.PositiveIntegerField(default=0)

    def update_project_count(self):
        self.total_repos = len(self.repos.all())
        self.processed_repos = len(self.repos.filter(status__lt=16))
        if self.total_repos == self.processed_repos:
            self.status = 31
        self.save()


class Commit(models.Model):
    sha = FixedCharField(primary_key=True, max_length=40)
    repo = models.ForeignKey(Repo, blank=True, null=True)
    author_name = models.CharField(max_length=255)
    author_email = models.CharField(max_length=255)
    committer_name = models.CharField(max_length=255)
    committer_email = models.CharField(max_length=255)
    merge = models.BooleanField(default=False)
    headline = models.CharField(
        default='', max_length=255,
        help_text="first line of the commit message")
    full_message = models.TextField()
    created_at = models.DateTimeField()

    # deltas
    inserted = models.PositiveIntegerField(blank=True, null=True)
    deleted = models.PositiveIntegerField(blank=True, null=True)
    files = models.PositiveIntegerField(blank=True, null=True)
    # JSON with detailed file stats
    file_stats = models.TextField(blank=True, default='')

    # Integration with GHTorrent
    author = models.ForeignKey(
        User, blank=True, null=True, related_name='authored_commits')
    committer = models.ForeignKey(
        User, blank=True, null=True, related_name='committed_commits')

    # parent commits sha separated by newline
    parents = models.CharField(max_length=255, default='')

    def __str__(self):
        return self.sha

    def save(self, *args, **kwargs):
        # TODO: sanitize emails
        super(Commit, self).save(*args, **kwargs)

