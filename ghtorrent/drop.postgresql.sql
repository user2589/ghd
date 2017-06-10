
/* CASCADE will drop all associated indices. It does not drop dependent tables
 but rather drops an associated column, which makes deletion really slow if you
 don't do it in the right order
*/

DROP TABLE IF EXISTS
ght_watchers,
ght_repo_milestones,
ght_pull_request_history,
ght_pull_request_commits,
ght_pull_request_comments,
ght_repository_languages,
ght_repository_members,
ght_repository_commits,
ght_organization_members,
ght_issue_labels,
ght_repo_labels,
ght_issue_events,
ght_issue_comments,
ght_issues,
ght_pull_requests,
ght_followers,
ght_commit_parents,
ght_commit_comments,
ght_commits,
ght_repositories,
ght_users
CASCADE;
