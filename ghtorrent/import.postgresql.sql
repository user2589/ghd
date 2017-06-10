

-- ~1:00:00to before buffer adjustment
-- 2:10 with primary key
-- 01:15 without + 21s to add primary key
\copy ght_users FROM PROGRAM 'cat users.csv | sed "s/\\\\$//"' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;

-- 5 hours before adjustment
-- 07:18 wo pk
\copy ght_repositories FROM PROGRAM 'cat projects.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 39:00
\copy ght_commits FROM PROGRAM 'cat commits.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 00:25
\copy ght_commit_comments FROM PROGRAM 'cat commit_comments.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 12:19
\copy ght_commit_parents FROM PROGRAM 'cat commit_parents.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 00:34
\copy ght_followers FROM PROGRAM 'cat followers.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 01:04
\copy ght_pull_requests FROM PROGRAM 'cat pull_requests.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 02:47
\copy ght_issues FROM PROGRAM 'cat issues.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 04:55
\copy ght_issue_comments FROM PROGRAM 'cat issue_comments.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 04:18
\copy ght_issue_events FROM PROGRAM 'cat issue_events.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 05:22
\copy ght_repo_labels FROM PROGRAM 'cat repo_labels.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 00:15
\copy ght_issue_labels FROM PROGRAM 'cat issue_labels.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 00:02
\copy ght_organization_members FROM PROGRAM 'cat organization_members.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 37:27
\copy ght_repository_commits FROM PROGRAM 'cat project_commits.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 00:28
\copy ght_repository_members FROM PROGRAM 'cat project_members.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 00:01
\copy ght_repository_languages FROM PROGRAM 'cat project_lanaguages.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- THIS ONE FAILS BECAUSE OF MYSQL EXCESSIVE ESCAPING
-- TODO: write a filter for it
\copy ght_pull_request_comments FROM PROGRAM 'cat pull_request_comments.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 02:10
\copy ght_pull_request_commits FROM PROGRAM 'cat pull_request_commits.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 02:52
\copy ght_pull_request_history FROM PROGRAM 'cat pull_request_history.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 0 (empty file)
\copy ght_repo_milestones FROM PROGRAM 'cat repo_milestones.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
-- 02:39
\copy ght_watchers FROM PROGRAM 'cat watchers.csv | sed "s/\\\\$//" ' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;


-- DO
-- $do$
-- DECLARE
--   t varchar;
--   tn varchar;
--   ts varchar[] := ARRAY['ght_users', 'ght_commits', 'ght_commit_comments', 'ght_commit_parents', 'ght_followers', 'ght_watchers',];
-- BEGIN
--    FOREACH t IN ARRAY ts LOOP
--      tn = replace(replace(substring(t from 5), 'repository', 'project'), 'repositories', 'projects');
--      \copy t FROM PROGRAM 'cat ' || t ||'.csv | sed "s/\\\\$//"' DELIMITER ',' NULL '\N' QUOTE '"' ESCAPE '\' CSV;
--    END LOOP;
-- END;
-- $do$
