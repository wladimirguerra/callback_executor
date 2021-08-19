# Request Sender

This module provides a `CallbackExecutor` class to receive and queue callbacks to 
be executed in a configured interval between calls. 

The time between calls can be greater than the configured interval, but not less.


## Use Case
If one needs to limit the rate of request to an API endpoint.

### Sample Code

```
import asyncio
from callback_executor import ExecutorQueue

async main():
    exec_queue = ExecutorQueue(call_interval=0.5)
    await exec_queue.ready()
    
    tasks = [
        exec_queue.enqueue_callback(blocking_request_to_api_1),
        exec_queue.enqueue_callback(blocking_request_to_api_2),
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # Handle responses

if __name__ == "__main__":
    asyncio.run(main())
```
