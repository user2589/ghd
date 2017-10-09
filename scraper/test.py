
import unittest

import pandas as pd

import scraper


class TestScraper(unittest.TestCase):
    # TODO: invalidate cache
    def test_clean_email(self):
        test = [
            "me@someorg.com",
            "<me@someorg.com",
            "me@someorg.com>",
            "John Doe <me@someorg.com>",
            "John Doe <me+github.com@someorg.com>",
            "John Doe me@someorg.com",
        ]
        for email in test:
            self.assertEqual(scraper.clean_email(email), "me@someorg.com")

    def test_commits(self):
        # as of Aug 2017 six has 438 commits
        commits = scraper.commits("benjaminp/six")
        self.assertTrue(isinstance(commits, pd.DataFrame))
        self.assertGreater(len(commits), 400)
        # non-existent repository
        self.assertEqual(len(scraper.commits("user2589/nothingtoseehere")), 0)

    def test_issues(self):
        # 184 issues as of Aug 2017
        issues = scraper.issues("benjaminp/six")
        self.assertTrue(isinstance(issues, pd.DataFrame))
        self.assertGreater(len(issues), 180)
        # no issues
        self.assertEqual(len(scraper.issues("user2589/ghd")), 0)

    def test_non_dev_issues(self):
        # 16 issues as of Aug 2017
        issues = scraper.non_dev_issues("benjaminp/six")
        self.assertTrue(isinstance(issues, pd.DataFrame))
        self.assertGreater(len(issues), 15)

    def test_commit_stats(self):
        cs = scraper.commit_stats("django/django")
        self.assertTrue(isinstance(cs, pd.Series))
        self.assertGreater(len(cs), 140)
        self.assertLess(len(cs), 240)

    def test_commit_users(self):
        cu = scraper.commit_users("django/django")
        self.assertTrue(isinstance(cu, pd.Series))
        self.assertGreater(len(cu), 140)
        self.assertLess(len(cu), 240)

    def test_commit_gini(self):
        gini = scraper.commit_gini("django/django")
        self.assertTrue(isinstance(gini, pd.Series))
        self.assertGreater(len(gini), 140)
        self.assertLess(len(gini), 240)
        self.assertTrue(all(0 <= i <= 1 for i in gini))

    def test_commit_quantile(self):
        q50 = scraper.contributions_quantile("django/django", 0.5)
        self.assertTrue(isinstance(q50, pd.Series))
        self.assertGreater(len(q50), 140)
        self.assertLess(len(q50), 240)
        self.assertTrue(all(i >= 0 for i in q50))

    def test_new_issues(self):
        issues = scraper.new_issues("pandas-dev/pandas")
        self.assertTrue(isinstance(issues, pd.Series))
        self.assertGreater(len(issues), 78)
        self.assertLess(len(issues), 180)

    def test_non_dev_issue_stats(self):
        non_dev_issues = scraper.non_dev_issue_stats("pandas-dev/pandas")
        self.assertTrue(isinstance(non_dev_issues, pd.Series))
        self.assertGreater(len(non_dev_issues), 78)
        self.assertLess(len(non_dev_issues), 180)
        issues = scraper.new_issues("pandas-dev/pandas")
        self.assertTrue(all(issues >= non_dev_issues))

    def test_submitters(self):
        repo = "pandas-dev/pandas"
        submitters = scraper.submitters(repo)
        self.assertTrue(isinstance(submitters, pd.Series))
        self.assertGreater(len(submitters), 78)
        self.assertLess(len(submitters), 180)
        self.assertTrue(all(s >= 0 for s in submitters))
        issues = scraper.new_issues(repo)
        if len(issues) < len(submitters):
            submitters = submitters.reindex(issues.index)
        elif len(issues) > len(submitters):
            issues = issues.reindex(submitters.index)
        self.assertTrue(all(issues >= submitters))

    def test_non_dev_submitters(self):
        repo = "pandas-dev/pandas"
        submitters = scraper.non_dev_submitters(repo)
        self.assertTrue(isinstance(submitters, pd.Series))
        self.assertGreater(len(submitters), 78)
        self.assertLess(len(submitters), 180)
        self.assertTrue(all(s >= 0 for s in submitters))
        issues = scraper.non_dev_issue_stats(repo)
        if len(issues) < len(submitters):
            submitters = submitters.reindex(issues.index)
        elif len(issues) > len(submitters):
            issues = issues.reindex(submitters.index)
        self.assertTrue(all(issues >= submitters))

    def test_closed_issues(self):
        issues = scraper.closed_issues("pandas-dev/pandas")
        self.assertTrue(isinstance(issues, pd.Series))
        self.assertGreater(len(issues), 78)
        self.assertLess(len(issues), 180)

    def test_open_issues(self):
        issues = scraper.open_issues("pandas-dev/pandas")
        self.assertTrue(isinstance(issues, pd.Series))
        self.assertGreater(len(issues), 78)
        self.assertLess(len(issues), 180)
        self.assertTrue(all(i >= 0 for i in issues))

if __name__ == "__main__":
    unittest.main()
