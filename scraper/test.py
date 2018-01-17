
import unittest

import pandas as pd

import scraper


class TestScraper(unittest.TestCase):
    # TODO: move to doctests

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
