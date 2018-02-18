
import logging
import multiprocessing
import Queue
import threading
import time

CPU_COUNT = multiprocessing.cpu_count()


class ThreadPool(object):
    _threads = None
    queue = None
    started = False
    callback_semaphore = None

    def __init__(self, n_workers=None):
        # the only reason to use threadpool in Python is IO (because of GIL)
        # so, we're not really limited with CPU and twice as many threads
        # is usually fine
        self.n = n_workers or CPU_COUNT * 2
        self.queue = Queue.Queue()
        self.callback_semaphore = threading.Lock()

    def start(self):
        assert not self.started, "The pool is already started"

        def worker():
            while self.started or not self.queue.empty():
                try:
                    func, args, kwargs, callback = self.queue.get(False)
                except Queue.Empty:
                    time.sleep(0.1)
                    continue
                else:
                    logging.debug("Got new data")

                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    logging.exception(e)
                else:
                    logging.debug("Processed data: %s -> %s", str(args), str(result))
                    self.callback_semaphore.acquire()
                    try:
                        callback(result)
                    except Exception as e:
                        logging.exception(e)
                    finally:
                        self.callback_semaphore.release()

        self._threads = [threading.Thread(target=worker) for _ in range(self.n)]
        self.started = True
        [t.start() for t in self._threads]

    def submit(self, func, *args, **kwargs):
        # submit is executed from the main thread and expected to by synchronous
        callback = kwargs.get('callback')
        if 'callback' in kwargs:
            assert callable(callback), "Callback must be callable"
            del(kwargs['callback'])

        self.queue.put((func, args, kwargs, callback))

        if not self.started:
            self.start()

    def shutdown(self):
        # cleanup
        self.started = False
        for t in self._threads:
            t.join()

    def __del__(self):
        self.shutdown()
