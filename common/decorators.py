
import os
import time
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


def fs_cache(app_name, cache_type='', expires=DEFAULT_EXPIRY):
    # type: (str, int) -> callable
    cache_path = mkdir(DATASET_PATH, app_name + ".cache", cache_type)

    def decorator(func):
        @wraps(func)
        def wrapper(*args):
            cache_filename = ".".join([
                func.__name__,
                "_".join([str(arg).replace("/", ".") for arg in args]),
                "csv"])
            cache_fpath = os.path.join(cache_path, cache_filename)
            if os.path.isfile(cache_fpath):
                if time.time() - os.path.getmtime(cache_fpath) < expires:
                    return pd.read_csv(cache_fpath, index_col=0)
            df = func(*args)
            df.to_csv(cache_fpath)
            return df

        return wrapper
    return decorator


def typed_fs_cache(app_name, expires=DEFAULT_EXPIRY):
    # type: (str, int) -> callable
    def _cache(cache_type):
        return fs_cache(app_name, cache_type, expires)

    return _cache


def cached_method(func):
    key = "_" + func.__name__

    @wraps(func)
    def wrapper(self):
        if not hasattr(self, key):
            setattr(self, key, func(self))
        return getattr(self, key)
    return wrapper


def cached_property(func):
    return property(cached_method(func))
