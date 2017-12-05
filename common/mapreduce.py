
import collections

import pandas as pd
import dask
import dask.threaded
import dask.multiprocessing
import dask.dataframe as dd
from dask.distributed import Client

from common import threadpool

CONFIG = {
    'backend': "threaded",
    'num_threads': 4,  # applies to backends using threads
    # Dask part
    'chunk_size': 10,  # dask dataframe chunk size
    'scheduler': '127.0.0.1:8786'  # dask.distributed scheduler network addr
}

try:
    import settings
    CONFIG.update(getattr(settings, 'MAPREDUCE_OPTIONS', {}))
except ImportError:
    pass


class Backend(object):

    def __init__(self, data, **config):
        assert isinstance(data, collections.Iterable), "Iterable expected"
        self.data = data
        for key, value in config.items():
            setattr(self, key, value)

    def map(self, func):
        raise NotImplemented

    def reduce(self, func):
        raise NotImplemented

    def resolve(self):
        raise NotImplemented


class ThreadedBackend(Backend):

    def __init__(self, *args, **kwargs):
        self.num_threads = CONFIG['num_threads']
        super(ThreadedBackend, self).__init__(*args, **kwargs)
        self.threadpool = threadpool.ThreadPool(self.num_threads)

    def map(self, func):
        if func:
            if isinstance(self.data, pd.DataFrame):
                data = []

                def callback(res):
                    data.append(res)

                for _, row in self.data.iterrows():
                    self.threadpool.submit(func, row)

                self.threadpool.shutdown()
                self.data = pd.DataFrame(data)

            elif isinstance(self.data, pd.Series):
                index = []
                data = []

                def callback(res):
                    index.append(res[0])
                    data.append(res[1])

                for i, d in self.data.iteritems():
                    self.threadpool.submit(func, i, d)

                self.threadpool.shutdown()
                self.data = pd.Series(data, index=index)

            elif isinstance(self.data, dict):
                raise NotImplemented
            else:
                raise NotImplemented

        return self

    def reduce(self, func):
        if func:  # just plain synch
            self.data = func(self.data)
        return self

    def resolve(self):
        return self.data


class DaskThreadedBackend(ThreadedBackend):

    def __init__(self, *args, **kwargs):
        self.chunk_size = CONFIG['chunk_size']

        super(DaskThreadedBackend, self).__init__(*args, **kwargs)

        if isinstance(self.data, (pd.DataFrame, pd.Series)):
            self.data = dd.from_pandas(self.data, chunksize=self.chunk_size)
        else:
            self.data = dd.from_array(self.data, chunksize=self.chunk_size)

    def map(self, func):
        if func:
            self.data = self.data.apply(func, axis=1)
        return self

    def resolve(self):
        with dask.set_options(get=dask.multiprocessing.get):
            return self.data.compute(num_workers=self.num_threads)


class DaskDistributedBackend(Backend):
    scheduler = CONFIG['scheduler']

    def __init__(self, *args, **kwargs):
        super(DaskDistributedBackend, self).__init__(*args, **kwargs)
        self.client = Client(self.scheduler)

    def map(self, func):
        if func:
            self.data = self.client.map(func, self.data)
        return self

    def reduce(self, func):
        if func:
            self.data = self.client.submit(func, self.data)
        return self

    def resolve(self):
        return self.data.result()


_BACKENDS = {
    'threaded': ThreadedBackend,
    'dask.threaded': DaskThreadedBackend,
    'dask.distributed': DaskDistributedBackend
}


class MapReduce(object):
    # change these to override default backend
    backend = CONFIG['backend']
    backend_config = {}

    # methods
    preprocess = None
    map = None
    reduce = None
    postprocess = None

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
        assert CONFIG['backend'] in _BACKENDS, "Unsupported MapReduce backend"

        if cls.preprocess:
            # preliminary manipulations with input data.
            # E.g. remove outliers, slice time series etc
            data = cls.preprocess(data)

        backend = _BACKENDS[cls.backend](data, **cls.backend_config)

        result = backend.map(cls.map).reduce(cls.reduce).resolve()

        if cls.postprocess:
            result = cls.postprocess(result)

        return result
