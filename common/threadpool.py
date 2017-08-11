
import threading
import logging


class ThreadPool(object):
    _threads = []

    def __init__(self, n_workers):
        self.n = n_workers
        self.exec_semaphore = threading.BoundedSemaphore(n_workers)
        self.callback_semaphore = threading.Lock()

    def submit(self, func, *args, **kwargs):
        callback = kwargs.get('callback')
        if 'callback' in kwargs:
            del(kwargs['callback'])

        def worker():
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                logging.exception(e)
            else:
                if callable(callback):
                    self.callback_semaphore.acquire()
                    try:
                        callback(result)
                    except Exception as e:
                        logging.exception(e)
                    finally:
                        self.callback_semaphore.release()
            finally:
                self.exec_semaphore.release()

        if self.n < 2:
            try:
                res = func(*args, **kwargs)
                if callable(callback):
                    callback(res)
            except Exception as e:
                logging.exception(e)
            return None
        self.exec_semaphore.acquire()

        t = threading.Thread(target=worker)
        t.start()
        if len(self._threads) > self.n:
            self.callback_semaphore.acquire()
            self._threads = [t for t in self._threads if t.is_alive()]
            self.callback_semaphore.release()
        self._threads.append(t)

    def shutdown(self):
        for t in self._threads:
            t.join()
