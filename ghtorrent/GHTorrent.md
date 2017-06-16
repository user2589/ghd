
`user.fake` flag is not accurate
---
`fake` is a flag indicating users that were artificially created for authors
of commits not found on Github. They typically have all-caps usernames 8 char
long. However sometimes [real users](https://github.com/egranata) have this 
flag, too. Test:

    select login, fake from ght_users u where u.login = 'egranata';

`users.deleted` is not accurate
--
Probably some of them were recreated. Previous examples were fixed in 2017-06-01


Project (repository) commits aren't accurate
--
This [project](https://github.com/linkcheck/linkchecker) appears to be a fork
 of [this](https://github.com/wummel/linkchecker/) one, but it is not reflected
 on GitHub AND in GHTorrent commits belong to fork only
 Test (selecting first commit) returns only one record: 
 
    select *
    from ght_commits c, ght_repository_commits rc
    where c.sha = '0329ca7682f735fab3fc17281a2d4c59876cabbb'
    and c.id = rc.commit_id;

`ght_commits.repository_id` has the same deficiency, except it does not
include commits authored in other repositories (i.e. before fork and merged
with pull requests).
