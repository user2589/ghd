
from __future__ import unicode_literals, print_function

import unittest
import random

import pandas as pd
import numpy as np

from common import decorators as d
from common import utils as common
from common import email


def series(length, *args):
    return pd.Series(np.random.rand(length) * 100).astype(int)


def dataframe(x, y, *args):
    return pd.DataFrame(np.random.rand(x, y) * 100).astype(int)


class TestDecorators(unittest.TestCase):
    @d.cached_method
    def rand(self, *args):
        return random.random()

    def test_memoize(self):

        def test(*args):
            return random.random()

        mtest = d.memoize(test)

        self.assertNotEquals(test('one', 'two'), test('one', 'two'))
        self.assertEquals(mtest('one', 'two'), mtest('one', 'two'))
        self.assertNotEquals(mtest('one', 'two'), mtest('two', 'one'))

    def test_cached_method(self):
        self.assertEquals(self.rand('one', 'two'), self.rand('one', 'two'))
        self.assertNotEquals(self.rand('one', 'two'), self.rand('two', 'one'))

    def test_fs_cache(self):
        decorator = d.fs_cache('common')
        cseries = decorator(series)
        self.assertEqual(0, (cseries(10) != cseries(10)).values.sum())
        self.assertGreater((cseries(10, 'one', 'two') != cseries(10, 'two', 'one')).values.sum(), 0)
        self.assertGreater((series(10) != series(10)).values.sum(), 0)
        self.assertIsInstance(cseries(10, 'one', 'two'), pd.Series)

        decorator.invalidate(series)

        cdataframe = decorator(dataframe)
        self.assertEqual(0, (cdataframe(10, 10).values != cdataframe(10, 10).values).sum())
        self.assertGreater((cdataframe(10, 10, 'one', 'two').values != cdataframe(10, 10, 'two', 'one').values).sum(), 0)
        self.assertGreater((dataframe(10, 10).values != dataframe(10, 10).values).sum(), 0)
        self.assertIsInstance(cdataframe(10, 10, 'one', 'two'), pd.DataFrame)

        decorator.invalidate(cdataframe)


class TestEmails(unittest.TestCase):

    def test_clean_email(self):
        test = [
            "me@someorg.com",
            "<me@someorg.com",
            "me@someorg.com>",
            "John Doe <me@someorg.com>",
            "John Doe <me+github.com@someorg.com>",
            "John Doe me@someorg.com",
            # git2svn produces addresses like this:
            "<me@someorg.com@ce2b1a6d-e550-0410-aec6-3dcde31c8c00>",
        ]

        for addr in test:
            self.assertEqual(email.clean(addr), "me@someorg.com")

    def test_email_domain(self):
        test = [
            "test@dep.uni.edu>",
            "test@dep.uni.edu@ce2b1a6d-e550-0410-aec6-3dcde31c8c00>",
        ]
        for email_addr in test:
            self.assertEqual(email.domain(email_addr), "dep.uni.edu")

    def test_public_university_domains(self):
        assert(
            not email.public_domains().intersection(email.university_domains()))

    def test_university_email(self):
        test = {
            "john@cmu.edu": True,
            "john@abc.cmu.edu": True,
            "john@abc.edu.uk": True,
            "john@edu.au": True,
            "john@aedu.au": False,
            "john@vvsu.ru": True,
            "john@abc.vvsu.ru": True,
            "john@england.edu": False,
            "john@gmail.com": False,
        }
        for email_addr, res in test.items():
            self.assertEqual(email.is_university(email_addr), res)

    def test_public_email(self):
        test = {
            "john@cmu.edu": False,
            "john@gmail.com": True,
            "john@163.com": True,
            "john@qq.com": True,
            "john@abc.vvsu.ru": False,
            "john@australia.edu": True,
        }
        for email_addr, res in test.items():
            self.assertEqual(email.is_public(email_addr), res)


if __name__ == "__main__":
    unittest.main()
