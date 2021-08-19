import asyncio
import atexit
import typing
from typing import Callable


class ExecutorQueue:
    """
    An executor queue class that provide a way to call `Callables` at a
    `call_interval`.

    The callback are executed in a thread pool (`ThreadPoolExecutor`) so
     it is possible to enqueue
    blocking callbacks too.

    Parameters
    ----------
    call_interval: float
        The interval between callbacks execution in seconds.
    callback_queue_size: int
        The maximum number of callback that can reside at the callback
        queue to be called. The minimum value is 10. If a number less
        than 10 is provided it will be coerced to 10.
    """

    _call_interval: float

    # A queue where the str is the Tread name for debug purpose
    _queue: asyncio.Queue[(asyncio.Future, Callable[[], typing.Any], typing.Optional[str])]
    _dispatcher_task: typing.Optional[asyncio.Task] = None
    _loop: typing.Optional[asyncio.AbstractEventLoop] = None

    def __init__(self, *, call_interval: float = 0.5, callback_queue_size: int = 30) -> None:

        super().__init__()
        self._queue = asyncio.Queue(
            maxsize=max([callback_queue_size, 10]))

        if call_interval <= 0:
            raise ValueError("call_interval must be greater than zero.")

        self._call_interval = call_interval
        self._loop = asyncio.get_event_loop()
        self._dispatcher_task = asyncio.create_task(self._dispatcher_worker())

        def cleanup():
            self._dispatcher_task.cancel()

        atexit.register(cleanup)

    async def ready(self):

        # A recursive test to reduce the waiting time
        async def is_ready(deep=0):
            ready_condition = self._loop is not None \
                              and self._dispatcher_task is not None \
                              and not self._dispatcher_task.done()

            if not ready_condition:
                if deep < 5:
                    await asyncio.sleep(0.2)
                    return await is_ready(deep + 1)
                return False
            return True

        return await is_ready()

    @property
    def call_interval(self):
        """
        The interval to wait between two calls

        Returns
        -------
        float
            Interval in seconds
        """
        return self._call_interval

    @call_interval.setter
    def call_interval(self, interval: float):
        """
        The interval to wait between two calls

        Parameters
        ----------
        interval
            Interval in seconds
        """
        if interval <= 0.5:
            raise ValueError("Interval must be greater than 500 ms.")

        if interval is None:
            raise ValueError("Interval must not be null")

        self._call_interval = interval

    async def _dispatcher_worker(self):
        """
        The work dispatcher that runs a worker for each enqueued
        callable.
        """
        while True:
            (future, _callback, thread_name) = await self._queue.get()

            # Run callback in a thread pool in case of the callback block the event loop
            # See https://docs.python.org/3/library/asyncio-eventloop.html#id14
            #
            # The future.set_result 'release' the enqueue_callback and let it return the future
            # that will have the callback value as it result.
            future.set_result(future.get_loop().run_in_executor(None, _callback))

            # Await between calls
            await asyncio.sleep(self._call_interval)

    def stop(self):
        """
        Stops the queue scan and cancel the pending tasks.
        """
        if self._dispatcher_task is not None:
            self._dispatcher_task.cancel()

    async def enqueue_callback(self, callback: Callable[[], typing.Any],
                               thread_name_prefix: typing.Optional[str] = None,
                               timeout: float = None) -> typing.Any:
        """
        Enqueue callback to be executed one by one with
        `callback_interval` seconds between executions.

        The maximum number of calls that can be enqueued is 30 by
        default. If the maximum is reached it will wait for `timeout` to
        put in the queue. If the timeout occurs the ``TimeoutError`` is
        raised.

        Parameters
        ----------
        timeout
            The number in seconds to wait to put the callback in the
            queue if it is full. If it is not provided then no timeout
            erro will be raise and the code will be blocked until the
            callback is put in the queue.
        thread_name_prefix
            The Thread name for debug purpose.
        callback
            The callback to be enqueued

        Returns
        -------
        typing.Any
            The callback result.
        """

        future = self._loop.create_future()
        put_task = self._queue.put((future, callback, thread_name_prefix))

        if timeout is not None:
            # Await 10 seconds to put item on queue if it is full
            await asyncio.wait_for(put_task, timeout=timeout)

        # `future` is a future of a future where will return the callback value.
        # So when `await future` it will return the future that will return the callback value. Thats
        # the reason to await again.
        # The first await will be 'released' when the callback get extracted from the queue.
        return await (await future)
