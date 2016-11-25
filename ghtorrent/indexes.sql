CREATE UNIQUE INDEX `login` ON `users` (`login` ASC);
CREATE UNIQUE INDEX `sha` ON `commits` (`sha` ASC);
CREATE UNIQUE INDEX `comment_id` ON `commit_comments` (`comment_id` ASC);
CREATE INDEX `follower_id` ON `followers` (`follower_id` ASC) COMMENT '';
CREATE UNIQUE INDEX `pullreq_id` ON `pull_requests` (`pullreq_id` ASC, `base_repo_id` ASC);
CREATE INDEX `name` ON `projects` (`name` ASC);
CREATE INDEX `commit_id` ON `project_commits` (`commit_id` ASC);
CREATE INDEX `project_id` ON `project_languages` (`project_id`) COMMENT '';
