
ALTER TABLE ght_users
  ADD PRIMARY KEY (id),
  ADD UNIQUE INDEX user_login (login)
;

ALTER TABLE ght_repositories
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT repository_owner FOREIGN KEY (owner_id) REFERENCES ght_users(id),
  ADD CONSTRAINT repository_forked_from FOREIGN KEY (forked_from) REFERENCES ght_repositories (id),
  ADD INDEX repository_name (`name`)
;

ALTER TABLE ght_commits
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT commit_author FOREIGN KEY (author_id)  REFERENCES ght_users (id),
  ADD CONSTRAINT commit_committer FOREIGN KEY (committer_id) REFERENCES ght_users (id),
  ADD CONSTRAINT commit_repository FOREIGN KEY (repository_id)  REFERENCES ght_repositories (id),
  ADD UNIQUE INDEX commit_sha (sha)
;

ALTER TABLE ght_commit_comments
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT commit_comment_commit FOREIGN KEY (commit_id) REFERENCES ght_commits (id),
  ADD CONSTRAINT commit_comments_author FOREIGN KEY (user_id)  REFERENCES ght_users (id),
  ADD UNIQUE INDEX comment_id (comment_id)  COMMENT '';
;

ALTER TABLE ght_commit_parents
  ADD CONSTRAINT commit_id FOREIGN KEY (commit_id) REFERENCES ght_commits (id),
  ADD CONSTRAINT commit_parent FOREIGN KEY (parent_id) REFERENCES ght_commits (id)
;

ALTER TABLE ght_followers
  ADD PRIMARY KEY (follower_id, user_id),
  ADD CONSTRAINT follower_follower FOREIGN KEY (follower_id) REFERENCES ght_users (id),
  ADD CONSTRAINT follower_user FOREIGN KEY (user_id) REFERENCES ght_users (id)
;

ALTER TABLE ght_pull_requests
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT pull_requests_head_repo FOREIGN KEY (head_repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT pull_requests_base_repo FOREIGN KEY (base_repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT pull_requests_head_commit FOREIGN KEY (head_commit_id) REFERENCES ght_commits (id),
  ADD CONSTRAINT pull_requests_base_commit FOREIGN KEY (base_commit_id) REFERENCES ght_commits (id)
#   ADD UNIQUE INDEX pullreq_id (pullreq_id, base_repo_id)
;

ALTER TABLE ght_issues
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT issue_repo FOREIGN KEY (repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT issues_reporter FOREIGN KEY (reporter_id) REFERENCES ght_users (id),
  ADD CONSTRAINT issues_assignee FOREIGN KEY (assignee_id) REFERENCES ght_users (id),
  ADD CONSTRAINT issues_pullrequest FOREIGN KEY (pull_request_id) REFERENCES ght_pull_requests (id)
;

ALTER TABLE ght_issue_comments
  ADD CONSTRAINT issue_comments_issue FOREIGN KEY (issue_id) REFERENCES ght_issues (id),
  ADD CONSTRAINT issue_comments_user FOREIGN KEY (user_id) REFERENCES ght_users (id)
;

ALTER TABLE ght_issue_events
  ADD CONSTRAINT issue_events_issue FOREIGN KEY (issue_id) REFERENCES ght_issues (id),
  ADD CONSTRAINT issue_events_actor FOREIGN KEY (actor_id) REFERENCES ght_users (id)
;

ALTER TABLE ght_repo_labels
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT repo_labels_repo FOREIGN KEY (repo_id) REFERENCES ght_repositories (id)
;

ALTER TABLE ght_issue_labels
  ADD PRIMARY KEY (issue_id, label_id),
  ADD CONSTRAINT issue_labels_label FOREIGN KEY (label_id) REFERENCES ght_repo_labels (id),
  ADD CONSTRAINT issue_labels_issue FOREIGN KEY (issue_id) REFERENCES ght_issues (id)
;

ALTER TABLE ght_organization_members
  ADD PRIMARY KEY (org_id, user_id),
  ADD CONSTRAINT organization_members_org FOREIGN KEY (org_id) REFERENCES ght_users (id),
  ADD CONSTRAINT organization_members_user FOREIGN KEY (user_id) REFERENCES ght_users (id)
;


ALTER TABLE ght_repository_commits
  ADD CONSTRAINT repository_commits_repository FOREIGN KEY (repository_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT repository_commits_commit FOREIGN KEY (commit_id) REFERENCES ght_commits (id),
  ADD INDEX commit_id (commit_id)
;

ALTER TABLE ght_repository_members
  ADD PRIMARY KEY (repo_id, user_id) ,
  ADD CONSTRAINT repository_members_repo FOREIGN KEY (repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT repository_members_ibfk_user FOREIGN KEY (user_id) REFERENCES ght_users (id)
;

ALTER TABLE ght_repository_languages
  ADD CONSTRAINT repository_languages_repository FOREIGN KEY (repository_id) REFERENCES ght_repositories (id)
;

ALTER TABLE ght_pull_request_comments
  ADD CONSTRAINT pull_request_comments_pullrequest FOREIGN KEY (pull_request_id) REFERENCES ght_pull_requests (id),
  ADD CONSTRAINT pull_request_comments_user FOREIGN KEY (user_id) REFERENCES ght_users (id),
  ADD CONSTRAINT pull_request_comments_commit FOREIGN KEY (commit_id) REFERENCES ght_commits (id)
;

ALTER TABLE ght_pull_request_commits
  ADD PRIMARY KEY (pull_request_id, commit_id),
  ADD CONSTRAINT pull_request_commits_pullrequest FOREIGN KEY (pull_request_id) REFERENCES ght_pull_requests (id),
  ADD CONSTRAINT pull_request_commits_commit FOREIGN KEY (commit_id) REFERENCES ght_commits (id)
;

ALTER TABLE ght_pull_request_history
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT pull_request_history_pullrequest FOREIGN KEY (pull_request_id) REFERENCES ght_pull_requests (id),
  ADD CONSTRAINT pull_request_history_actor FOREIGN KEY (actor_id) REFERENCES ght_users (id)
;

ALTER TABLE ght_repo_milestones
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT repo_milestones_repo FOREIGN KEY (repo_id) REFERENCES ght_repositories (id)
;

ALTER TABLE ght_watchers
  ADD PRIMARY KEY (repo_id, user_id),
  ADD CONSTRAINT watchers_repo FOREIGN KEY (repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT watchers_user FOREIGN KEY (user_id) REFERENCES ght_users (id)
;
