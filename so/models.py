
from __future__ import unicode_literals

from django.db import models


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

    class Meta:
        db_table = 'so_users'


class Tag(models.Model):
    name = models.CharField(max_length=25)
    count = models.PositiveIntegerField()
    # these are safe to ignore
    excerpt_post_id = models.IntegerField(blank=True, null=True)
    wiki_post_id = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'so_tag_names'


class Post(models.Model):
    question = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User)
    accepted_answer = models.IntegerField(
        blank=True, null=True, help_text="only for questions")
    created_at = models.DateTimeField()
    score = models.SmallIntegerField(blank=True, null=True)
    parent = models.ForeignKey(
        "self", blank=True, null=True, help_text="only for answers")
    views = models.IntegerField()
    last_editor = models.ForeignKey(User, blank=True, null=True)
    last_edited_at = models.DateTimeField()
    last_activity_at = models.DateTimeField()
    community_owned_at = models.DateTimeField()
    answers_count = models.PositiveIntegerField()
    comments_count = models.PositiveIntegerField()
    favorites_count = models.PositiveIntegerField()

    class Meta:
        db_table = 'so_posts'


class SoTags(models.Model):
    tag_id = models.IntegerField()
    post_id = models.IntegerField()

    class Meta:
        db_table = 'so_tags'
