
/* Comparing to MySQL:
- removed `
- TINYINT(1) -> BOOLEAN
- INT NOT NULL AUTO_INCREMENT -> SERIAL
- PRIMARY KEY (fields) -> CONSTRAINT <table_name>_pk PRIMARY KEY (fields)
- MEDIUMTEXT -> TEXT
*/

CREATE TABLE IF NOT EXISTS ght_users (
  id           SERIAL,
  login        VARCHAR(255) NOT NULL,
  company      VARCHAR(255) NULL     DEFAULT NULL,
  created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  type         CHAR(3)      NOT NULL DEFAULT 'USR',
  fake         BOOLEAN   NOT NULL DEFAULT '0',
  deleted      BOOLEAN   NOT NULL DEFAULT '0',
  long         DECIMAL(11, 8),
  lat          DECIMAL(10, 8),
  country_code CHAR(3),
  state        VARCHAR(255),
  city         VARCHAR(255),
  location     VARCHAR(255) NULL     DEFAULT NULL
--   , CONSTRAINT users_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_repositories (
  id          SERIAL,
  url         VARCHAR(255) NULL     DEFAULT NULL,
  owner_id    INT          NULL     DEFAULT NULL,
  name        VARCHAR(255) NOT NULL,
  description VARCHAR(255) NULL     DEFAULT NULL,
  language    VARCHAR(255) NULL     DEFAULT NULL,
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  forked_from INT          NULL     DEFAULT NULL,
  deleted     BOOLEAN   NOT NULL DEFAULT '0',
  updated_at  TIMESTAMP    NOT NULL DEFAULT '1970-01-01 00:00:00',
  noop        INT          NULL     DEFAULT NULL -- strange undocumented field
--   , CONSTRAINT repositories_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_commits (
  id            SERIAL,
  sha           CHAR(40)  NULL     DEFAULT NULL,
  author_id     INT       NULL     DEFAULT NULL,
  committer_id  INT       NULL     DEFAULT NULL,
  repository_id INT       NULL     DEFAULT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
--   , CONSTRAINT commits_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_commit_comments (
  id         SERIAL,
  commit_id  INT          NOT NULL,
  user_id    INT          NOT NULL,
  body       VARCHAR(256) NULL     DEFAULT NULL,
  line       INT          NULL     DEFAULT NULL,
  position   INT          NULL     DEFAULT NULL,
  comment_id INT          NOT NULL,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
--   , CONSTRAINT commit_comments_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_commit_parents (
  commit_id INT NOT NULL,
  parent_id INT NOT NULL
);

CREATE TABLE IF NOT EXISTS ght_followers (
  follower_id INT       NOT NULL,
  user_id     INT       NOT NULL,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
--   , CONSTRAINT followers_pk PRIMARY KEY (follower_id, user_id)
);

CREATE TABLE IF NOT EXISTS ght_pull_requests (
  id             SERIAL,
  head_repo_id   INT        NULL     DEFAULT NULL,
  base_repo_id   INT        NOT NULL,
  head_commit_id INT        NULL     DEFAULT NULL,
  base_commit_id INT        NOT NULL,
  pullreq_id     INT        NOT NULL,
  intra_branch   BOOLEAN NOT NULL
--   , CONSTRAINT pull_requests_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_issues (
  id              SERIAL,
  repo_id         INT        NULL     DEFAULT NULL,
  reporter_id     INT        NULL     DEFAULT NULL,
  assignee_id     INT        NULL     DEFAULT NULL,
  pull_request    BOOLEAN NOT NULL,
  pull_request_id INT        NULL     DEFAULT NULL,
  created_at      TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  issue_id        INT        NOT NULL
--   , CONSTRAINT issues_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_issue_comments (
  issue_id   INT        NOT NULL,
  user_id    INT        NOT NULL,
  comment_id TEXT NOT NULL,
  created_at TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ght_issue_events (
  event_id        TEXT   NOT NULL,
  issue_id        INT          NOT NULL,
  actor_id        INT          NOT NULL,
  action          VARCHAR(255) NOT NULL,
  action_specific VARCHAR(50)  NULL     DEFAULT NULL,
  created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ght_repo_labels (
  id      SERIAL,
  repo_id INT         NULL     DEFAULT NULL,
  name    VARCHAR(24) NOT NULL
--   , CONSTRAINT repo_labels_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_issue_labels (
  label_id INT NOT NULL,
  issue_id INT NOT NULL
--   , CONSTRAINT issue_labels_pk PRIMARY KEY (issue_id, label_id)
);

CREATE TABLE IF NOT EXISTS ght_organization_members (
  org_id     INT       NOT NULL,
  user_id    INT       NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
--   , CONSTRAINT org_members_pk PRIMARY KEY (org_id, user_id)
);

CREATE TABLE IF NOT EXISTS ght_repository_commits (
  repository_id INT NOT NULL DEFAULT '0',
  commit_id     INT NOT NULL DEFAULT '0'
);

CREATE TABLE IF NOT EXISTS ght_repository_members (
  repo_id    INT         NOT NULL,
  user_id    INT         NOT NULL,
  created_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ext_ref_id VARCHAR(24) NOT NULL DEFAULT '0'
--   , CONSTRAINT repo_members_pk PRIMARY KEY (repo_id, user_id)
);

CREATE TABLE IF NOT EXISTS ght_repository_languages (
  repository_id INT          NOT NULL,
  language      VARCHAR(255) NULL     DEFAULT NULL,
  bytes         INT,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ght_pull_request_comments (
  pull_request_id INT          NOT NULL,
  user_id         INT          NOT NULL,
  comment_id      TEXT   NOT NULL,
  position        INT          NULL     DEFAULT NULL,
  body            VARCHAR(256) NULL     DEFAULT NULL,
  commit_id       INT          NOT NULL,
  created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ght_pull_request_commits (
  pull_request_id INT NOT NULL,
  commit_id       INT NOT NULL
--   , CONSTRAINT pull_request_commits_pk PRIMARY KEY (pull_request_id, commit_id)
);

CREATE TABLE IF NOT EXISTS ght_pull_request_history (
  id              SERIAL,
  pull_request_id INT          NOT NULL,
  created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  action          VARCHAR(255) NOT NULL,
  actor_id        INT          NULL     DEFAULT NULL
--   , CONSTRAINT pull_request_history_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_repo_milestones (
  id      SERIAL,
  repo_id INT         NULL     DEFAULT NULL,
  name    VARCHAR(24) NOT NULL
--   , CONSTRAINT repo_milestones_pk PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS ght_watchers (
  repo_id    INT       NOT NULL,
  user_id    INT       NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
--   , CONSTRAINT watchers_pk PRIMARY KEY (repo_id, user_id)
);
