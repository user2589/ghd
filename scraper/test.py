import unittest

from scraper import utils

import pandas as pd


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
            self.assertEqual(utils.clean_email(email), "me@someorg.com")

    def test_commits(self):
        # as of Aug 2017 six has 438 commits
        commits = utils.commits("benjaminp/six")
        self.assertTrue(isinstance(commits, pd.DataFrame))
        self.assertGreater(len(commits), 400)
        # non-existent repository
        self.assertEqual(len(utils.commits("user2589/nothingtoseehere")), 0)

    def test_issues(self):
        # 184 issues as of Aug 2017
        issues = utils.issues("benjaminp/six")
        self.assertTrue(isinstance(issues, pd.DataFrame))
        self.assertGreater(len(issues), 180)
        # no issues
        self.assertEqual(len(utils.issues("user2589/ghd")), 0)

    def test_non_dev_issues(self):
        # 16 issues as of Aug 2017
        issues = utils.non_dev_issues("benjaminp/six")
        self.assertTrue(isinstance(issues, pd.DataFrame))
        self.assertGreater(len(issues), 15)

    def test_commit_stats(self):
        cs = utils.commit_stats("django/django")
        self.assertTrue(isinstance(cs, pd.Series))
        self.assertGreater(len(cs), 140)
        self.assertLess(len(cs), 240)

    def test_commit_users(self):
        cu = utils.commit_users("django/django")
        self.assertTrue(isinstance(cu, pd.Series))
        self.assertGreater(len(cu), 140)
        self.assertLess(len(cu), 240)

    def test_commit_gini(self):
        gini = utils.commit_gini("django/django")
        self.assertTrue(isinstance(gini, pd.Series))
        self.assertGreater(len(gini), 140)
        self.assertLess(len(gini), 240)
        self.assertTrue(all(0 <= i <= 1 for i in gini))

    def test_commit_quantile(self):
        q50 = utils.contributions_quantile("django/django", 0.5)
        self.assertTrue(isinstance(q50, pd.Series))
        self.assertGreater(len(q50), 140)
        self.assertLess(len(q50), 240)
        self.assertTrue(all(i >= 0 for i in q50))

    def test_new_issues(self):
        issues = utils.new_issues("pandas-dev/pandas")
        self.assertTrue(isinstance(issues, pd.Series))
        self.assertGreater(len(issues), 78)
        self.assertLess(len(issues), 180)

    def test_non_dev_issue_stats(self):
        non_dev_issues = utils.non_dev_issue_stats("pandas-dev/pandas")
        self.assertTrue(isinstance(non_dev_issues, pd.Series))
        self.assertGreater(len(non_dev_issues), 78)
        self.assertLess(len(non_dev_issues), 180)
        issues = utils.new_issues("pandas-dev/pandas")
        self.assertTrue(all(issues >= non_dev_issues))

    def test_submitters(self):
        submitters = utils.submitters("pandas-dev/pandas")
        self.assertTrue(isinstance(submitters, pd.Series))
        self.assertGreater(len(submitters), 78)
        self.assertLess(len(submitters), 180)
        self.assertTrue(all(s >= 0 for s in submitters))
        issues = utils.new_issues("pandas-dev/pandas")
        self.assertTrue(all(issues >= submitters))

    def test_closed_issues(self):
        issues = utils.closed_issues("pandas-dev/pandas")
        self.assertTrue(isinstance(issues, pd.Series))
        self.assertGreater(len(issues), 78)
        self.assertLess(len(issues), 180)

    def test_open_issues(self):
        issues = utils.open_issues("pandas-dev/pandas")
        self.assertTrue(isinstance(issues, pd.Series))
        self.assertGreater(len(issues), 78)
        self.assertLess(len(issues), 180)
        self.assertTrue(all(i >= 0 for i in issues))

if __name__ == "__main__":
    unittest.main()
