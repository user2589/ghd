
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


def get_cache_path(app_name, cache_type="", ds_path=DATASET_PATH):
    if not app_name:
        return ds_path
    return mkdir(ds_path, app_name + ".cache", cache_type)


def expired(cache_fpath, expires):
    return not os.path.isfile(cache_fpath) \
           or time.time() - os.path.getmtime(cache_fpath) > expires


def fs_cache(app_name, idx=1, cache_type='', expires=DEFAULT_EXPIRY):
    # type: (str, int, str, int) -> callable
    cache_path = get_cache_path(app_name, cache_type)

    def decorator(func):
        @wraps(func)
        def wrapper(*args):
            cache_filename = ".".join([
                func.__name__,
                "_".join([str(arg).replace("/", ".") for arg in args]),
                "csv"])
            cache_fpath = os.path.join(cache_path, cache_filename)
            if not expired(cache_fpath, expires):
                return pd.read_csv(cache_fpath, index_col=range(idx),
                                   encoding="utf8")
            df = func(*args)
            df.to_csv(cache_fpath, float_format="%.2g", encoding="utf-8")
            return df

        return wrapper
    return decorator


def typed_fs_cache(app_name, expires=DEFAULT_EXPIRY):
    # type: (str, int) -> callable
    def _cache(cache_type, idx=1):
        return fs_cache(app_name, idx, cache_type=cache_type, expires=expires)

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
