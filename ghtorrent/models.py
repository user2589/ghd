
from __future__ import unicode_literals

from django.db import models


class User(models.Model):
    login = models.CharField(unique=True, max_length=40)
    company = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField()
    type = models.CharField(max_length=255, choices=(
        ('USR', 'individual'),
        ('ORG', 'organization'),
    ))
    fake = models.BooleanField()  # NONSENSE: https://github.com/egranata/
    deleted = models.BooleanField()  # NONSENSE: https://github.com/rupakg/
    long = models.DecimalField(max_digits=11, decimal_places=8, blank=True,
                               null=True, help_text="Longitude")
    lat = models.DecimalField(max_digits=10, decimal_places=8, blank=True,
                              null=True, help_text="Latitude")
    country_code = models.CharField(max_length=3, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.login

    class Meta:
        db_table = 'users'


class Project(models.Model):
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True, null=141)
    owner = models.ForeignKey(
        User, blank=True, null=True, related_name='owned_projects')
    description = models.CharField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField()
    forked_from = models.ForeignKey("self", blank=True, null=True)
    deleted = models.BooleanField()
    updated_at = models.DateTimeField()

    def __str__(self):
        return self.url

    class Meta:
        db_table = 'projects'


class Commit(models.Model):
    sha = models.CharField(unique=True, max_length=40, blank=True, null=True)
    author = models.ForeignKey(
        User, blank=True, null=True, related_name='authored_commits')
    committer = models.ForeignKey(
        User, blank=True, null=True, related_name='committed_commits')
    project = models.ForeignKey(
        Project, blank=True, null=True, related_name='commits')
    # created_at = models.DateTimeField()
    # parents = models.ManyToManyField("self")

    def __str__(self):
        return self.sha

    class Meta:
        db_table = 'commits'


# class CommitComment(models.Model):
#     commit_id = models.IntegerField()
#     user_id = models.IntegerField()
#     body = models.CharField(max_length=256, blank=True, null=True)
#     line = models.IntegerField(blank=True, null=True)
#     position = models.IntegerField(blank=True, null=True)
#     comment_id = models.IntegerField(unique=True)
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'commit_comments'
#
#
# class CommitParents(models.Model):
#     commit_id = models.IntegerField()
#     parent_id = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'commit_parents'
#
#
# class Followers(models.Model):
#     follower_id = models.IntegerField()
#     user_id = models.IntegerField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'followers'
#         unique_together = (('follower_id', 'user_id'),)
#
#
# class IssueComments(models.Model):
#     issue_id = models.IntegerField()
#     user_id = models.IntegerField()
#     comment_id = models.TextField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'issue_comments'
#
#
# class IssueEvents(models.Model):
#     event_id = models.TextField()
#     issue_id = models.IntegerField()
#     actor_id = models.IntegerField()
#     action = models.CharField(max_length=255)
#     action_specific = models.CharField(max_length=50, blank=True, null=True)
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'issue_events'
#
#
# class IssueLabels(models.Model):
#     label_id = models.IntegerField()
#     issue_id = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'issue_labels'
#         unique_together = (('issue_id', 'label_id'),)
#
#
# class Issues(models.Model):
#     repo_id = models.IntegerField(blank=True, null=True)
#     reporter_id = models.IntegerField(blank=True, null=True)
#     assignee_id = models.IntegerField(blank=True, null=True)
#     pull_request = models.IntegerField()
#     pull_request_id = models.IntegerField(blank=True, null=True)
#     created_at = models.DateTimeField()
#     issue_id = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'issues'
#
#
# class OrganizationMembers(models.Model):
#     org_id = models.IntegerField()
#     user_id = models.IntegerField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'organization_members'
#         unique_together = (('org_id', 'user_id'),)
#
#
# class ProjectCommits(models.Model):
#     project_id = models.IntegerField()
#     commit_id = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'project_commits'
#
#
# class ProjectLanguages(models.Model):
#     project_id = models.IntegerField()
#     language = models.CharField(max_length=255, blank=True, null=True)
#     bytes = models.IntegerField(blank=True, null=True)
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'project_languages'
#
#
# class ProjectMembers(models.Model):
#     repo_id = models.IntegerField()
#     user_id = models.IntegerField()
#     created_at = models.DateTimeField()
#     ext_ref_id = models.CharField(max_length=24)
#
#     class Meta:
#         managed = False
#         db_table = 'project_members'
#         unique_together = (('repo_id', 'user_id'),)
#
#
# class PullRequestComments(models.Model):
#     pull_request_id = models.IntegerField()
#     user_id = models.IntegerField()
#     comment_id = models.TextField()
#     position = models.IntegerField(blank=True, null=True)
#     body = models.CharField(max_length=256, blank=True, null=True)
#     commit_id = models.IntegerField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'pull_request_comments'
#
#
# class PullRequestCommits(models.Model):
#     pull_request_id = models.IntegerField()
#     commit_id = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'pull_request_commits'
#         unique_together = (('pull_request_id', 'commit_id'),)
#
#
# class PullRequestHistory(models.Model):
#     pull_request_id = models.IntegerField()
#     created_at = models.DateTimeField()
#     action = models.CharField(max_length=255)
#     actor_id = models.IntegerField(blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'pull_request_history'
#
#
# class PullRequests(models.Model):
#     head_repo_id = models.IntegerField(blank=True, null=True)
#     base_repo_id = models.IntegerField()
#     head_commit_id = models.IntegerField(blank=True, null=True)
#     base_commit_id = models.IntegerField()
#     pullreq_id = models.IntegerField()
#     intra_branch = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'pull_requests'
#         unique_together = (('pullreq_id', 'base_repo_id'),)
#
#
# class RepoLabels(models.Model):
#     repo_id = models.IntegerField(blank=True, null=True)
#     name = models.CharField(max_length=24)
#
#     class Meta:
#         managed = False
#         db_table = 'repo_labels'
#
#
# class RepoMilestones(models.Model):
#     repo_id = models.IntegerField(blank=True, null=True)
#     name = models.CharField(max_length=24)
#
#     class Meta:
#         managed = False
#         db_table = 'repo_milestones'
#
#
# class Watchers(models.Model):
#     repo_id = models.IntegerField()
#     user_id = models.IntegerField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'watchers'
#         unique_together = (('repo_id', 'user_id'),)
