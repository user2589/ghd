
import pandas as pd

import collections

from common import threadpool


def map(data, func, num_workers=None):
    """

    >>> s = pd.Series(range(120, 0, -1))
    >>> s2 = map(s, lambda i, x: x ** 3.75)
    >>> isinstance(s2, type(s))
    True
    >>> len(s) == len(s2)
    True
    >>> (s2 == s.map(lambda x: x ** 3.75)).all()
    True
    >>> s = list(range(120, 0, -1))
    >>> s2 = map(s, lambda i, x: x ** 3.75)
    >>> isinstance(s2, type(s))
    True
    >>> len(s) == len(s2)
    True
    >>> all(x ** 3.75 == s2[i] for i, x in enumerate(s))
    True
    >>> s = dict(enumerate(range(120, 0, -1)))
    >>> s2 = map(s, lambda i, x: x ** 3.75)
    >>> isinstance(s2, type(s))
    True
    >>> len(s) == len(s2)
    True
    >>> all(x ** 3.75 == s2[i] for i, x in s.items())
    True
    """
    backend = threadpool.ThreadPool(n_workers=num_workers)
    iterable = None
    # pd.Series didn't have .items() until pandas 0.21,
    # so iteritems for older versions
    for method in ('iterrows', 'iteritems', 'items'):
        if hasattr(data, method):
            iterable = getattr(data, method)()
            break
    if iterable is None:
        iterable = enumerate(data)

    mapped = {}

    def collect(key):
        def process(res):
            mapped[key] = res
        return process

    for key, value in iterable:
        backend.submit(func, key, value, callback=collect(key))

    backend.shutdown()

    if isinstance(data, pd.DataFrame):
        return pd.DataFrame.from_dict(
            mapped, orient='index').reindex(data.index)
    elif isinstance(data, pd.Series):
        return pd.Series(mapped).reindex(data.index)
    elif isinstance(data, list):
        return [mapped[i] for i in range(len(data))]
    else:
        # in Python, hash(<int>) := <int>, so guaranteed to be in order for list
        # and tuple. For other types
        return type(data)(mapped)


class MapReduce(object):
    """ Helper to process large volumes of information
    It employes configured backend

    Workflow:
        (input of every function passed to the next one)
        preprocess -> map -> reduce -> postprocess

        at least map() or reduce() should be defined.
        pre/post processing is intended for reusable classes, useless otherwise

    Use:
        class Processor(MapRedue):
            # NOTE: all methods are static, i.e. no self

            def preprocess(*data):
                # gets raw input data
                return single_object

            def map(key, value)
                # depending on input, key, value defined as a result of:
                # .iterrows(), .items(), or enumerate, whatever found first
                processed_value = process(value)
                return key, processed_value

    """
    # change these to override default backend
    n_workers = None  # keywords to init backend object (Threadpool)

    # methods
    preprocess = None
    map = None
    reduce = None
    postprocess = None
    @staticmethod
    def __new__(cls, data):
        """ An intro to Python object creation:
        1. Python checks for metaclass
            - object.__metaclass__
            - parent.__metaclass__
            - module.__metaclass__
            - type by default
            Metaclass is a callable with args:
                - class_name
                - tuple of parent classes
                - dict of attributes and their values
            Metaclass returns a CLASS (not an object)
        2. Python calls the class.__new__()  # note the call is static
            NOTE: it is only called for new-style classes, but you don't
                have to worry about this until you time travelled back to 2013
            __new__ accepts class, args and kwargs,
                and returns an object instance, calling __init__ along the way
            This makes possible to use __new__ as a static __call__, which is
            exploited in this article: https://habrahabr.ru/post/145835/
            And so will we.

        Wokflow in this method:
            - accept list of inputs as the only argument
            - use schedule(map) to transofrm the input
            - reduce will be used as a success callback to form result
        """

        assert cls.map or cls.reduce, "MapReduce subclasses are expected to " \
                                      "have at least one of map() or reduce()" \
                                      " methods defined."

        if cls.preprocess:
            data = cls.preprocess(data)

        assert isinstance(data, collections.Iterable), "Iterable expected"

        if cls.map:
            data = map(data, cls.map)

        if cls.reduce:
            data = cls.reduce(data)

        if cls.postprocess:
            data = cls.postprocess(data)

        return data
