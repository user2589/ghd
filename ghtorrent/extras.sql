/* EXTENSIONS OF THE ORIGINAL DATASET TO SIMPLIFY ROUTING QUERIES
 */

/* =====================================================
    ISSUE STATUS AGGREGATED FROM ISSUE EVENTS
    ~15minutes total
====================================================== */

DROP TABLE ght_issue_status CASCADE;
-- less than 1 hour to create table, load with data and create indexes
CREATE TABLE IF NOT EXISTS ght_issue_status (
  issue_id    INT,
  repo_id     INT,
  created_at  TIMESTAMP NOT NULL,
  closed_at   TIMESTAMP NULL     DEFAULT NULL,
  reopened_at TIMESTAMP NULL     DEFAULT NULL,
  closed      BOOLEAN   NOT NULL DEFAULT FALSE
);

-- 11:24
INSERT INTO ght_issue_status
select i.id, i.repo_id, i.created_at, max(iec.created_at) as date_closed, max(ier.created_at) as date_reopened,
  (max(iec.created_at) is not NULL) AND ((max(ier.created_at) is NULL) or max(iec.created_at) > max(ier.created_at))
from ght_issues i
left OUTER JOIN ght_issue_events iec
  ON (i.id = iec.issue_id and iec.action='closed')
left OUTER JOIN ght_issue_events ier
  ON (i.id = ier.issue_id and ier.action='reopened')
where NOT i.pull_request
group by i.id;

-- 03:54
ALTER TABLE ght_issue_status
  ADD CONSTRAINT issue_status_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id),
  ADD CONSTRAINT issue_status_issue_fk FOREIGN KEY (issue_id)  REFERENCES ght_issues (id)
;
-- 00:53
CREATE INDEX IF NOT EXISTS issue_status_repo_i ON ght_issue_status(repo_id);
CREATE INDEX IF NOT EXISTS issue_status_issue_i ON ght_issue_status(issue_id);


/* =====================================================
    MONTHLY COMMIT STATS
    17+ hours of processing (but it worth it)
====================================================== */

CREATE TABLE IF NOT EXISTS ght_commit_stats (
  repo_id INT,
  month   CHAR(7), -- YYYY-MM date string
  num     INT
);

-- 17:26:08
INSERT INTO ght_commit_stats
select rc.repository_id, to_char(c.created_at, 'YYYY-MM') as month, count(c.id)
from ght_commits c, ght_repository_commits rc
where c.id = rc.commit_id
group by rc.repository_id, month;
-- 03:03
ALTER TABLE ght_commit_stats
  ADD CONSTRAINT commit_stats_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id);
-- 03:57
CREATE INDEX IF NOT EXISTS commit_stats_repo_i ON ght_commit_stats(repo_id);

/* =====================================================
    MONTHLY NEW ISSUE STATS
    ~3minutes total (otherwise 3 minutes per repository)
====================================================== */

CREATE TABLE IF NOT EXISTS ght_new_issues (
  repo_id INT,
  month   CHAR(7), -- YYYY-MM date string
  num     INT
);

-- 01:08
INSERT INTO ght_new_issues
select i.repo_id, to_char(i.created_at, 'YYYY-MM') as month, count(issue_id)
from ght_issue_status i
group by i.repo_id, month;
-- 01:37
ALTER TABLE ght_new_issues
  ADD CONSTRAINT new_issues_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id);
-- 00:06
CREATE INDEX IF NOT EXISTS new_issues_repo_i ON ght_new_issues(repo_id);
select current_timestamp;


/* =====================================================
    MONTHLY CLOSED ISSUES
    ~2.5 min
====================================================== */
CREATE TABLE IF NOT EXISTS ght_closed_issues (
  repo_id INT,
  month   CHAR(7), -- YYYY-MM date string
  num     INT
);

INSERT INTO ght_closed_issues
select i.repo_id, to_char(i.closed_at, 'YYYY-MM'), count(issue_id)
from ght_issue_status i
where i.closed
group by i.repo_id, to_char(i.closed_at, 'YYYY-MM');

ALTER TABLE ght_closed_issues
  ADD CONSTRAINT closed_issues_repo_fk FOREIGN KEY (repo_id) REFERENCES ght_repositories (id);
--
CREATE INDEX IF NOT EXISTS closed_issues_repo_i ON ght_closed_issues(repo_id);




