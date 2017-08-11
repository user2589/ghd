
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


def get_cache_path(app_name, cache_type="", ds_path=DATASET_PATH):
    if not app_name:
        return ds_path
    return mkdir(ds_path, app_name + ".cache", cache_type)


def expired(cache_fpath, expires):
    return not os.path.isfile(cache_fpath) \
           or time.time() - os.path.getmtime(cache_fpath) > expires


def get_cache_fname(cache_path, func, *args):
    cache_filename = ".".join([
        func.__name__,
        "_".join([str(arg).replace("/", ".") for arg in args]),
        "csv"])
    return os.path.join(cache_path, cache_filename)


def invalidate(app_name, func, *args, **kwargs):
    cache_path = get_cache_path(app_name, **kwargs)
    cache_fname = get_cache_fname(cache_path, func, *args)
    if os.path.isfile(cache_fname):
        os.remove(cache_fname)
        return True
    return False


def fs_cache(app_name, idx=1, cache_type='', expires=DEFAULT_EXPIRY):
    # type: (str, int, str, int) -> callable
    cache_path = get_cache_path(app_name, cache_type)

    def decorator(func):
        @wraps(func)
        def wrapper(*args):
            cache_fpath = get_cache_fname(cache_path, func, *args)
            if not expired(cache_fpath, expires):
                df = pd.read_csv(
                    cache_fpath, index_col=range(idx), encoding="utf8")
                if len(df.columns) == 1 and idx == 1:
                    return df[df.columns[0]]
                return df

            res = func(*args)
            if isinstance(res, pd.DataFrame):
                df = res
                if len(df.columns) == 1 and idx == 1:
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
            df.to_csv(cache_fpath, float_format="%.2g", encoding="utf-8")
            return res

        return wrapper
    return decorator


def typed_fs_cache(app_name, expires=DEFAULT_EXPIRY):
    # type: (str, int) -> callable
    def _cache(cache_type, idx=1):
        return fs_cache(app_name, idx, cache_type=cache_type, expires=expires)

    return _cache


def cached_method(func):
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
