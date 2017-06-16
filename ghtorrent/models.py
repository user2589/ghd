
from __future__ import unicode_literals

from django.db import models
from django.utils.datastructures import DictWrapper


class FixedCharField(models.CharField):
    def db_type(self, connection):
        data = DictWrapper(self.__dict__, connection.ops.quote_name, "qn_")
        return 'char(%(max_length)s)' % data


class GHTModel(models.Model):

    def save(self, *args, **kwargs):
        return

    def delete(self, *args, **kwargs):
        return

    class Meta:
        abstract = True


class CommitStats(GHTModel):
    repository = models.ForeignKey('Repository', related_name='monthly_commits',
                                   db_column='repo_id')
    month = FixedCharField(max_length=7)
    num = models.IntegerField()

    class Meta:
        db_table = 'ght_commit_stats'
        managed = False


class ClosedIssueStats(GHTModel):
    repository = models.ForeignKey('Repository', related_name='closed_issues',
                                   db_column='repo_id')
    month = FixedCharField(max_length=7)
    num = models.IntegerField()

    class Meta:
        db_table = 'ght_closed_issues'
        managed = False


class NewIssueStats(GHTModel):
    repository = models.ForeignKey('Repository', related_name='new_issues',
                                   db_column='repo_id')
    month = FixedCharField(max_length=7)
    num = models.IntegerField()

    class Meta:
        db_table = 'ght_new_issues'
        managed = False


class IssueStatus(GHTModel):
    issue = models.ForeignKey('Issue', related_name='status')
    repository = models.ForeignKey('Repository', related_name='issue_statuses',
                                   db_column='repo_id')
    created_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    reopened_at = models.DateTimeField(null=True, blank=True)
    closed = models.BooleanField()

    class Meta:
        db_table = 'ght_issue_status'
        managed = False


class Deployment(models.Model):
    """Class to keep records about deployment of different dataset versions"""
    version = models.CharField(max_length=10)

    def __str__(self):
        return self.version


class User(models.Model):
    login = models.CharField(unique=True, max_length=40)
    company = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField()
    # Unfortunately, there is no ENUM field in Django and the original
    # dataset stores it as char
    type = models.CharField(max_length=255, choices=(
        ('USR', 'individual'),
        ('ORG', 'organization'),
    ))
    fake = models.BooleanField()  # inaccurate: https://github.com/egranata/
    deleted = models.BooleanField()  # inaccurate: https://github.com/rupakg/
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
        db_table = 'ght_users'
        managed = False


class Repository(GHTModel):
    """This is a repository model which by some reason called projects
    in GHTorrent. Fixing it here"""
    # full API URL, e.g. https://api.github.com/repos/tosch/ruote-kit
    url = models.CharField(max_length=255, blank=True, null=141)
    owner = models.ForeignKey(User, blank=True, null=True,
                              related_name='repositories')
    # just the last part of the url
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    forked_from = models.ForeignKey("self", db_column='forked_from',
                                    blank=True, null=True)
    deleted = models.BooleanField()
    updated_at = models.DateTimeField(auto_now_add=True)
    commits = models.ManyToManyField("Commit", through='ProjectCommit')
    # dataset contains one more undocumented field. It is here for compatibility
    noop = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.url[12:]

    class Meta:
        db_table = 'ght_repositories'
        managed = False


class Commit(GHTModel):
    sha = models.CharField(unique=True, max_length=40, blank=True, null=True)
    author = models.ForeignKey(
        User, blank=True, null=True, related_name='authored_commits')
    committer = models.ForeignKey(
        User, blank=True, null=True, related_name='committed_commits')
    # a project where this commit was initially created
    # Because of forks it can be used by many projects, which is trackable
    # trhough project_commits
    original_repository = models.ForeignKey(
        Repository, blank=True, null=True,
        db_column='repository_id', related_name='original_commits')
    created_at = models.DateTimeField(auto_now_add=True)
    relatives = models.ManyToManyField("self", through='CommitParents',
                                       symmetrical=False)

    def __str__(self):
        return self.sha

    class Meta:
        db_table = 'ght_commits'
        managed = False
        ordering = ['created_at']


class CommitParents(GHTModel):
    commit = models.ForeignKey(Commit, related_name='children')
    parent = models.ForeignKey(Commit, related_name='parents')

    class Meta:
        db_table = 'ght_commit_parents'
        managed = False


class Issue(GHTModel):
    repository = models.ForeignKey(Repository,
                                   related_name='issues', db_column='repo_id')
    reporter = models.ForeignKey(User, related_name='reported_issues')
    assignee = models.ForeignKey(User, blank=True, null=True,
                                 related_name='assigned_issues')
    pull_request = models.BooleanField(
        help_text="Boolean indicating if this issue is tied to a pull request")
    pull_request_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    issue_id = models.IntegerField()

    class Meta:
        db_table = 'ght_issues'
        managed = False


class IssueEvent(GHTModel):
    # Originally text, trying to convert to integer
    event_id = models.IntegerField()
    issue_id = models.IntegerField()
    actor_id = models.IntegerField()
    action = models.CharField(max_length=255)
    # choices=(
    # "closed", "reopened", "assigned", "merged", "renamed", "deployed",
    # "converted_note_to_issue", "unsubscribed", "locked", "base_ref_changed",
    # "labeled", "base_ref_force_pushed", "removed_from_project",
    # "review_requested", "moved_columns_in_project", "head_ref_cleaned",
    # "mentioned", "demilestoned", "added_to_project", "milestoned",
    # "unlabeled", "head_ref_force_pushed", "subscribed", "unassigned",
    # "head_ref_restored", "referenced", "unlocked", "head_ref_deleted"))
    action_specific = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'ght_issue_events'
        managed = False


class ProjectCommit(GHTModel):
    repository = models.ForeignKey(Repository)
    commit = models.ForeignKey(Commit, related_name='repositories')

    class Meta:
        db_table = 'ght_repository_commits'
        managed = False

# class CommitComment(GHTModel):
#     ghtable = 'commit_comments'
#     commit = models.ForeignKey(Commit, related_name='comments')
#     user = models.ForeignKey(User, related_name='commit_comments')
#     body = models.CharField(max_length=256, blank=True, null=True)
#     # no idea what the other three fields are used for
#     line = models.IntegerField(blank=True, null=True)
#     position = models.IntegerField(blank=True, null=True)
#     comment_id = models.IntegerField(unique=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#
#
# class Followers(GHTModel):
#     follower_id = models.IntegerField()
#     user_id = models.IntegerField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'ght_followers'
#         unique_together = (('follower_id', 'user_id'),)
#
#
# class IssueComments(GHTModel):
#     issue_id = models.IntegerField()
#     user_id = models.IntegerField()
#     comment_id = models.TextField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'ght_issue_comments'
#
#
# class IssueLabels(GHTModel):
#     label_id = models.IntegerField()
#     issue_id = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'ght_issue_labels'
#         unique_together = (('issue_id', 'label_id'),)
#
#
#
# class OrganizationMembers(GHTModel):
#     org_id = models.IntegerField()
#     user_id = models.IntegerField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'ght_organization_members'
#         unique_together = (('org_id', 'user_id'),)
#
#
# class ProjectLanguages(GHTModel):
#     project_id = models.IntegerField()
#     language = models.CharField(max_length=255, blank=True, null=True)
#     bytes = models.IntegerField(blank=True, null=True)
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'ght_repository_languages'
#
#
# class ProjectMembers(GHTModel):
#     repo_id = models.IntegerField()
#     user_id = models.IntegerField()
#     created_at = models.DateTimeField()
#     ext_ref_id = models.CharField(max_length=24)
#
#     class Meta:
#         managed = False
#         db_table = 'ght_repository_members'
#         unique_together = (('repo_id', 'user_id'),)
#
#
# class PullRequestComments(GHTModel):
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
#         db_table = 'ght_pull_request_comments'
#
#
# class PullRequestCommits(GHTModel):
#     pull_request_id = models.IntegerField()
#     commit_id = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'ght_pull_request_commits'
#         unique_together = (('pull_request_id', 'commit_id'),)
#
#
# class PullRequestHistory(GHTModel):
#     pull_request_id = models.IntegerField()
#     created_at = models.DateTimeField()
#     action = models.CharField(max_length=255)
#     actor_id = models.IntegerField(blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'ght_pull_request_history'
#
#
# class PullRequests(GHTModel):
#     head_repo_id = models.IntegerField(blank=True, null=True)
#     base_repo_id = models.IntegerField()
#     head_commit_id = models.IntegerField(blank=True, null=True)
#     base_commit_id = models.IntegerField()
#     pullreq_id = models.IntegerField()
#     intra_branch = models.IntegerField()
#
#     class Meta:
#         managed = False
#         db_table = 'ght_pull_requests'
#         unique_together = (('pullreq_id', 'base_repo_id'),)
#
#
# class RepoLabels(GHTModel):
#     repo_id = models.IntegerField(blank=True, null=True)
#     name = models.CharField(max_length=24)
#
#     class Meta:
#         managed = False
#         db_table = 'ght_repo_labels'
#
#
# class RepoMilestones(GHTModel):
#     repo_id = models.IntegerField(blank=True, null=True)
#     name = models.CharField(max_length=24)
#
#     class Meta:
#         managed = False
#         db_table = 'ght_repo_milestones'
#
#
# class Watchers(GHTModel):
#     repo_id = models.IntegerField()
#     user_id = models.IntegerField()
#     created_at = models.DateTimeField()
#
#     class Meta:
#         managed = False
#         db_table = 'ght_watchers'
#         unique_together = (('repo_id', 'user_id'),)
