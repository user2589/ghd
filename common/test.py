
from __future__ import unicode_literals, print_function

import unittest
import random

import numpy as np
import pandas as pd

from common import decorators as d
from common import mapreduce
from common import threadpool


def series(length):
    return pd.Series(np.random.rand(length) * 100).astype(int)


def dataframe(x, y):
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


class TestThreadpool(unittest.TestCase):

    def test_async_mapping(self):
        tp = threadpool.ThreadPool()
        data = range(20) * 30
        results = []

        def callback(status):
            results.append(status)

        def do(x):
            return x ** 3.75

        for x in data:
            tp.submit(do, x, callback=callback)
        tp.shutdown()

        response = [do(x) for x in data]

        self.assertEqual(len(response), len(results))
        self.assertEqual(sum(response), sum(results))


if __name__ == "__main__":
    unittest.main()
