
import os
import time
from typing import Iterable
from functools import wraps

import pandas as pd

try:
    import settings
except ImportError:
    settings = object()

CACHE_PATH = getattr(settings, 'DATASET_PATH', '.cache')


def cache(app_name, cache_types=(), expires=3600*24*30*3):
    # type: (str, Iterable[str], int) -> callable
    cache_path = os.path.join(CACHE_PATH, app_name + ".cache")
    ctypes = {}

    if not os.path.isdir(cache_path):
        os.mkdir(cache_path)

    for t in cache_types:
        path = os.path.join(cache_path, t)
        if not os.path.isdir(path):
            os.mkdir(path)
        ctypes[t] = path

    def _cache(cache_type=None):
        assert (not cache_type and not ctypes) or cache_type in ctypes
        cpath = cache_path if not ctypes else ctypes[cache_type]

        def decorator(func):
            @wraps(func)
            def wrapper(*args):
                cache_filename = ".".join([
                    "_".join([arg.replace("/", ".") for arg in args]),
                    func.__name__, "csv"])
                cache_fpath = os.path.join(cpath, cache_filename)
                if os.path.isfile(cache_fpath):
                    if time.time() - os.path.getmtime(cache_fpath) < expires:
                        return pd.read_csv(cache_fpath, index_col=0)
                df = func(*args)
                df.to_csv(cache_fpath)
                return df

            return wrapper
        return decorator

    return _cache
