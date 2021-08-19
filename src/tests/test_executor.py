#  Copyright (c) 2021 Wladimir A. Guerra
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
#  OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#  ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#  OTHER DEALINGS IN THE SOFTWARE.

#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#
import asyncio
import logging
import math
import time
from datetime import datetime
from typing import Awaitable
from unittest import IsolatedAsyncioTestCase

from src.callback_executor import ExecutorQueue

logging.basicConfig(level=logging.DEBUG)


class TestCallbackExecutor(IsolatedAsyncioTestCase):

    async def test_start_stop(self):
        exec_queue = ExecutorQueue(call_interval=23)
        self.assertEqual(exec_queue.call_interval, 23)
        self.assertTrue(await exec_queue.ready())
        exec_queue.stop()
        await asyncio.sleep(1)
        self.assertTrue(exec_queue._dispatcher_task.cancelled())

    async def test_enqueue_callback(self):
        exec_queue = ExecutorQueue(call_interval=23)

        def _callback():
            return 23

        return_value = await exec_queue.enqueue_callback(_callback)

        self.assertEqual(return_value, 23)
        exec_queue.stop()

    async def test_blocking_callbacks(self):
        def first_callback():
            first_call_time = datetime.now()
            print(f'First call at: ${first_call_time.strftime("%Y-%M-%D %H:%M:%S")}')
            time.sleep(3)
            return first_call_time

        def second_callback():
            second_call_time = datetime.now()
            print(f'Second call at: ${second_call_time.strftime("%Y-%M-%D %H:%M:%S")}')
            time.sleep(5)
            return second_call_time

        call_interval = 1

        exec_queue = ExecutorQueue(call_interval=call_interval)

        self.assertTrue(await exec_queue.ready())

        tasks: list[Awaitable] = [exec_queue.enqueue_callback(first_callback,
                                                                "first_callback"),
                                  exec_queue.enqueue_callback(second_callback,
                                                                "second_callback")]

        times = await asyncio.gather(*tasks)
        delta_time = (times[1] - times[0]).total_seconds()

        # Test if the time between the executions of the two callbacks is equal
        self.assertEqual(math.trunc(delta_time), call_interval)

        exec_queue.stop()
