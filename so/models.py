
from __future__ import unicode_literals

from django.db import models
from django.contrib.postgres.fields import ArrayField


class User(models.Model):
    name = models.CharField(max_length=64, blank=True, null=True)
    email_hash = models.CharField(
        max_length=32, blank=True, null=True, help_text='MD5 email hash')
    reputation = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    website_url = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    views = models.PositiveIntegerField(blank=True, null=True)
    upvotes = models.PositiveIntegerField(blank=True, null=True)
    downvotes = models.PositiveIntegerField(blank=True, null=True)
    about_me = models.TextField(blank=True, null=True)


class Tag(models.Model):
    name = models.CharField(max_length=25)
    count = models.PositiveIntegerField(default=0)
    # these are safe to ignore
    excerpt_post_id = models.IntegerField(blank=True, null=True)
    wiki_post_id = models.IntegerField(blank=True, null=True)


class Post(models.Model):
    question = models.BooleanField(default=False)
    title = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, related_name='owned_posts')
    accepted_answer = models.IntegerField(
        blank=True, null=True, help_text="only for questions")
    created_at = models.DateTimeField()
    score = models.SmallIntegerField(blank=True, null=True)
    parent = models.ForeignKey(
        "self", blank=True, null=True, help_text="only for answers",
        related_name='answers')
    views = models.IntegerField(default=0)
    last_editor = models.ForeignKey(
        User, blank=True, null=True, related_name='edited_posts')
    last_edited_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    community_owned_at = models.DateTimeField(null=True, blank=True)
    answers_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    favorites_count = models.PositiveIntegerField(default=0)
    tags = ArrayField(models.CharField(max_length=25))
    # tags = models.ManyToManyField(Tag, related_name='posts')

    class Meta:
        ordering = ['created_at']
