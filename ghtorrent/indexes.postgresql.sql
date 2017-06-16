
/* Comparing to MySQL:
- indexes cannot be added by ALTER TABLE
- quotes removed
- indexes on foreign key fields are not created automatically
 */

-- 21s
ALTER TABLE ght_users ADD PRIMARY KEY (id);
-- 1m 44s
CREATE UNIQUE INDEX IF NOT EXISTS user_login_i ON public.ght_users (login);

--10:01
ALTER TABLE ght_repositories
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT repository_owner_fk FOREIGN KEY (owner_id) REFERENCES ght_users(id),
  ADD CONSTRAINT repository_forked_from_fk FOREIGN KEY (forked_from) REFERENCES ght_repositories (id)
;
--11:48
CREATE INDEX IF NOT EXISTS repository_name_i ON public.ght_repositories (name);
-- ~7:00
CREATE INDEX IF NOT EXISTS repository_owner_i ON public.ght_repositories (owner_id);
CREATE INDEX IF NOT EXISTS repository_forked_from_i ON public.ght_repositories (forked_from);

ALTER TABLE ght_commits
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT commit_author_fk FOREIGN KEY (author_id)  REFERENCES ght_users (id),
  ADD CONSTRAINT commit_committer_fk FOREIGN KEY (committer_id) REFERENCES ght_users (id),
  ADD CONSTRAINT commit_repository_fk FOREIGN KEY (repository_id)  REFERENCES ght_repositories (id)
;
CREATE UNIQUE INDEX IF NOT EXISTS commit_sha ON public.ght_commits (sha);

CREATE INDEX IF NOT EXISTS commit_author_i ON ght_commits (author_id);
CREATE INDEX IF NOT EXISTS commit_committer_i ON ght_commits(committer_id);
CREATE INDEX IF NOT EXISTS commit_repository_fk_fk ON ght_commits(repository_id);


ALTER TABLE ght_commit_comments
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT commit_comment_commit_fk FOREIGN KEY (commit_id) REFERENCES ght_commits (id),
  ADD CONSTRAINT commit_comments_author_fk FOREIGN KEY (user_id)  REFERENCES ght_users (id)
;
CREATE UNIQUE INDEX IF NOT EXISTS comment_id ON ght_commit_comments (comment_id);
CREATE INDEX IF NOT EXISTS commit_comment_commit_i ON ght_commit_comments (commit_id);
CREATE INDEX IF NOT EXISTS commit_comments_author_i ON ght_commit_comments (user_id);

ALTER TABLE ght_commit_parents
  ADD CONSTRAINT commit_id_fk FOREIGN KEY (commit_id) REFERENCES ght_commits (id),
  ADD CONSTRAINT commit_parent_fk FOREIGN KEY (parent_id) REFERENCES ght_commits (id)
;
CREATE INDEX IF NOT EXISTS commit_id_i ON ght_commit_parents (commit_id);
CREATE INDEX IF NOT EXISTS commit_parent_i ON ght_commit_parents (parent_id);

ALTER TABLE ght_followers
  ADD PRIMARY KEY (follower_id, user_id),
  ADD CONSTRAINT follower_follower_fk FOREIGN KEY (follower_id) REFERENCES ght_users (id),
  ADD CONSTRAINT follower_user_fk FOREIGN KEY (user_id) REFERENCES ght_users (id)
;
CREATE INDEX IF NOT EXISTS follower_follower_fk ON ght_followers(follower_id);
CREATE INDEX IF NOT EXISTS follower_user_fk ON ght_followers(user_id);


ALTER TABLE ght_pull_requests
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT pull_requests_head_repo_fk FOREIGN KEY (head_repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT pull_requests_base_repo_fk FOREIGN KEY (base_repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT pull_requests_head_commit_fk FOREIGN KEY (head_commit_id) REFERENCES ght_commits (id),
  ADD CONSTRAINT pull_requests_base_commit_fk FOREIGN KEY (base_commit_id) REFERENCES ght_commits (id)
;
CREATE UNIQUE INDEX IF NOT EXISTS pullreq_id ON ght_pull_requests (pullreq_id, base_repo_id);
CREATE INDEX IF NOT EXISTS pull_requests_head_repo_i ON ght_pull_requests (head_repo_id);
CREATE INDEX IF NOT EXISTS pull_requests_base_repo_i ON ght_pull_requests(base_repo_id);
CREATE INDEX IF NOT EXISTS pull_requests_head_commit_i ON ght_pull_requests(head_commit_id);
CREATE INDEX IF NOT EXISTS pull_requests_base_commit_i ON ght_pull_requests(base_commit_id);


ALTER TABLE ght_issues
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT issue_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT issues_reporter_fk FOREIGN KEY (reporter_id) REFERENCES ght_users (id),
  ADD CONSTRAINT issues_assignee_fk FOREIGN KEY (assignee_id) REFERENCES ght_users (id),
  ADD CONSTRAINT issues_pullrequest_fk FOREIGN KEY (pull_request_id) REFERENCES ght_pull_requests (id)
;
CREATE INDEX IF NOT EXISTS issue_repo_i ON ght_issues (repo_id);
CREATE INDEX IF NOT EXISTS issues_reporter_i ON ght_issues(reporter_id);
CREATE INDEX IF NOT EXISTS issues_assignee_i ON ght_issues(assignee_id);
CREATE INDEX IF NOT EXISTS issues_pullrequest_i ON ght_issues(pull_request_id);

ALTER TABLE ght_issue_comments
  ADD CONSTRAINT issue_comments_issue_fk FOREIGN KEY (issue_id) REFERENCES ght_issues (id),
  ADD CONSTRAINT issue_comments_user_fk FOREIGN KEY (user_id) REFERENCES ght_users (id)
;
CREATE INDEX IF NOT EXISTS issue_comments_issue_i ON ght_issue_comments(issue_id);
CREATE INDEX IF NOT EXISTS issue_comments_user_i ON ght_issue_comments(user_id);

ALTER TABLE ght_issue_events
  ADD CONSTRAINT issue_events_issue_fk FOREIGN KEY (issue_id) REFERENCES ght_issues (id),
  ADD CONSTRAINT issue_events_actor_fk FOREIGN KEY (actor_id) REFERENCES ght_users (id)
;
CREATE INDEX IF NOT EXISTS issue_events_issue_i ON ght_issue_events(issue_id);
CREATE INDEX IF NOT EXISTS issue_events_actor_i ON ght_issue_events(actor_id);

ALTER TABLE ght_repo_labels
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT repo_labels_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id)
;
CREATE INDEX IF NOT EXISTS repo_labels_repo_i ON ght_repo_labels(repo_id);

ALTER TABLE ght_issue_labels
  ADD PRIMARY KEY (issue_id, label_id),
  ADD CONSTRAINT issue_labels_label_fk FOREIGN KEY (label_id) REFERENCES ght_repo_labels (id),
  ADD CONSTRAINT issue_labels_issue_fk FOREIGN KEY (issue_id) REFERENCES ght_issues (id)
;
CREATE INDEX IF NOT EXISTS issue_labels_label_i ON ght_issue_labels(label_id);
CREATE INDEX IF NOT EXISTS issue_labels_issue_i ON ght_issue_labels(issue_id);

ALTER TABLE ght_organization_members
  ADD PRIMARY KEY (org_id, user_id),
  ADD CONSTRAINT organization_members_org_fk FOREIGN KEY (org_id) REFERENCES ght_users (id),
  ADD CONSTRAINT organization_members_user_fk FOREIGN KEY (user_id) REFERENCES ght_users (id)
;
CREATE INDEX IF NOT EXISTS organization_members_org_i ON ght_organization_members(org_id);
CREATE INDEX IF NOT EXISTS organization_members_user_i ON ght_organization_members(user_id);

ALTER TABLE ght_repository_commits
  ADD CONSTRAINT repository_commits_repository_fk FOREIGN KEY (repository_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT repository_commits_commit_fk FOREIGN KEY (commit_id) REFERENCES ght_commits (id)
;
CREATE INDEX IF NOT EXISTS commit_id ON ght_repository_commits (commit_id);
CREATE INDEX IF NOT EXISTS repository_commits_repository_i ON ght_repository_commits(repository_id);

CREATE INDEX IF NOT EXISTS repository_commits_commit_i ON ght_repository_commits(commit_id);

ALTER TABLE ght_repository_members
  ADD PRIMARY KEY (repo_id, user_id) ,
  ADD CONSTRAINT repository_members_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT repository_members_ibfk_user_fk FOREIGN KEY (user_id) REFERENCES ght_users (id)
;
CREATE INDEX IF NOT EXISTS repository_members_repo_i ON ght_repository_members(repo_id);
CREATE INDEX IF NOT EXISTS repository_members_user_i ON ght_repository_members(user_id);

ALTER TABLE ght_repository_languages
  ADD CONSTRAINT repository_languages_repository_fk FOREIGN KEY (repository_id) REFERENCES ght_repositories (id)
;
CREATE INDEX IF NOT EXISTS repository_languages_repository_i ON ght_repository_languages(repository_id);

-- ALTER TABLE ght_pull_request_comments
--   ADD CONSTRAINT pull_request_comments_pullrequest_fk FOREIGN KEY (pull_request_id) REFERENCES ght_pull_requests (id),
--   ADD CONSTRAINT pull_request_comments_user_fk FOREIGN KEY (user_id) REFERENCES ght_users (id),
--   ADD CONSTRAINT pull_request_comments_commit_fk FOREIGN KEY (commit_id) REFERENCES ght_commits (id)
-- ;
-- -- TODO
-- CREATE INDEX IF NOT EXISTS pull_request_comments_pullrequest_i ON ght_pull_request_comments (pull_request_id);
-- CREATE INDEX IF NOT EXISTS pull_request_comments_user_i ON ght_pull_request_comments(user_id);
-- CREATE INDEX IF NOT EXISTS pull_request_comments_commit_i ON ght_pull_request_comments(commit_id);

ALTER TABLE ght_pull_request_commits
  ADD PRIMARY KEY (pull_request_id, commit_id),
  ADD CONSTRAINT pull_request_commits_pullrequest_fk FOREIGN KEY (pull_request_id) REFERENCES ght_pull_requests (id),
  ADD CONSTRAINT pull_request_commits_commit_fk FOREIGN KEY (commit_id) REFERENCES ght_commits (id)
;
CREATE INDEX IF NOT EXISTS pull_request_commits_pullrequest_i ON ght_pull_request_commits (pull_request_id);
CREATE INDEX IF NOT EXISTS pull_request_commits_commit_i ON ght_pull_request_commits(commit_id);

ALTER TABLE ght_pull_request_history
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT pull_request_history_pullrequest_fk FOREIGN KEY (pull_request_id) REFERENCES ght_pull_requests (id),
  ADD CONSTRAINT pull_request_history_actor_fk FOREIGN KEY (actor_id) REFERENCES ght_users (id)
;
CREATE INDEX IF NOT EXISTS pull_request_history_pullrequest_i ON ght_pull_request_history (pull_request_id);
CREATE INDEX IF NOT EXISTS pull_request_history_actor_i ON ght_pull_request_history(actor_id);

ALTER TABLE ght_repo_milestones
  ADD PRIMARY KEY (id),
  ADD CONSTRAINT repo_milestones_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id)
;
CREATE INDEX IF NOT EXISTS repo_milestones_repo_i ON ght_repo_milestones (repo_id);

ALTER TABLE ght_watchers
  ADD PRIMARY KEY (repo_id, user_id),
  ADD CONSTRAINT watchers_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT watchers_user_fk FOREIGN KEY (user_id) REFERENCES ght_users (id)
;
CREATE INDEX IF NOT EXISTS watchers_repo_i ON ght_watchers (repo_id);
CREATE INDEX IF NOT EXISTS watchers_user_i ON ght_watchers(user_id);

