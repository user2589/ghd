
from __future__ import unicode_literals
import unittest

import pypi


class TestPyPi(unittest.TestCase):
    def test_compare_versions(self):
        self.assertEqual(pypi.compare_versions("0.1.1", "0.1.2"), -1)
        self.assertEqual(pypi.compare_versions("0.1.2", "0.1.1"), 1)
        self.assertEqual(pypi.compare_versions("0.1", "0.1.1"), 0)
        self.assertEqual(pypi.compare_versions("0.1.1rc1", "0.1.1a"), 1)
        self.assertEqual(pypi.compare_versions("0.1.1rc1", "0.1.1"), -1)

    def test_list_packages(self):
        packages = list(pypi.list_packages())
        self.assertGreater(len(packages), 100000)
        # fails on Python2 because of unicode
        # self.assertTrue(all(isinstance(p, str) for p in packages))
        self.assertTrue(all(len(p) < 250 for p in packages))

    def test_github_url(self):
        p = pypi.Package("numpy")
        self.assertEqual(p.github_url, "numpy/numpy")

    def test_releases(self):
        p = pypi.Package("django")
        self.assertGreater(len(p.releases()), 10)

    def test_dependencies(self):
        p = pypi.Package("pandas")
        self.assertIn('numpy', p.dependencies())

    def test_size(self):
        p = pypi.Package("easy_phi")
        self.assertGreater('easy_phi', 500)

if __name__ == "__main__":
    unittest.main()
