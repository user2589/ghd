
import os
import time
import logging
from functools import wraps

import pandas as pd

try:
    import settings
except ImportError:
    settings = object()


def mkdir(*args):
    path = ''
    for chunk in args:
        path = os.path.join(path, chunk)
        if not os.path.isdir(path):
            os.mkdir(path)
    return path


DEFAULT_EXPIRY = 3600 * 24 * 30 * 3
DATASET_PATH = getattr(settings, 'DATASET_PATH', None) or \
    os.path.join(os.path.dirname(__file__), '..', '.cache')
mkdir(DATASET_PATH)


def _argstring(*args):
    return "_".join([str(arg).replace("/", ".") for arg in args])


class fs_cache(object):

    def __init__(self, app_name, idx=1, cache_type='',
                 expires=DEFAULT_EXPIRY, ds_path=DATASET_PATH):
        self.expires = expires
        self.idx = idx
        if not app_name:
            self.cache_path = ds_path
        else:
            self.cache_path = mkdir(ds_path, app_name + ".cache", cache_type)

    def get_cache_fname(self, func_name, *args, **kwargs):
        chunks = [func_name]
        if args:
            chunks.append(_argstring(*args))
        chunks.append(kwargs.get("extension", "csv"))
        return os.path.join(self.cache_path, ".".join(chunks))

    def expired(self, cache_fpath):
        return not os.path.isfile(cache_fpath) \
               or time.time() - os.path.getmtime(cache_fpath) > self.expires

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args):
            cache_fpath = self.get_cache_fname(func.__name__, *args)

            if not self.expired(cache_fpath):
                return pd.read_csv(cache_fpath, index_col=range(self.idx),
                                   encoding="utf8", squeeze=True)

            res = func(*args)
            if isinstance(res, pd.DataFrame):
                df = res
                if len(df.columns) == 1 and self.idx == 1:
                    logging.warning(
                        "Single column dataframe is returned by %s.\nSince it "
                        "will cause inconsistent behavior with @fs_cache "
                        "decorator, please consider changing result type "
                        "to pd.Series", func.__name__)
            elif isinstance(res, pd.Series):
                df = pd.DataFrame(res)
            else:
                raise ValueError("Unsupported result type (pd.DataFrame or "
                                 "pd.Series expected, got %s)" % type(res))
            df.to_csv(cache_fpath, float_format="%g", encoding="utf-8")
            return res
        return wrapper

    def invalidate(self, func):
        """ Remove all files caching this function """
        for fname in os.listdir(self.cache_path):
            if fname.startswith(func.__name__):
                os.remove(os.path.join(self.cache_path, fname))


def typed_fs_cache(app_name, expires=DEFAULT_EXPIRY):
    # type: (str, int) -> callable
    def _cache(cache_type, idx=1):
        return fs_cache(app_name, idx, cache_type=cache_type, expires=expires)

    return _cache


def memoize(func):
    """ Classical memoize for non-class methods """
    cache = {}

    @wraps(func)
    def wrapper(*args):
        key = "__".join(str(arg) for arg in args)
        if key not in cache:
            cache[key] = func(*args)
        return cache[key]
    return wrapper


def cached_method(func):
    """ Classical memoize for non-class methods """
    @wraps(func)
    def wrapper(self, *args):
        if not hasattr(self, "_cache"):
            self._cache = {}
        key = "__".join((func.__name__,) + args)
        if key not in self._cache:
            self._cache[key] = func(self, *args)
        return self._cache[key]
    return wrapper


def cached_property(func):
    return property(cached_method(func))
