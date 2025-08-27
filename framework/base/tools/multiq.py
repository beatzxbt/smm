import asyncio
from typing import AsyncIterable


async def consume_multiq[T](queues: list[asyncio.Queue[T]]) -> AsyncIterable[T]:
    """Consume items from multiple queues as they arrive."""
    if not queues:
        return

    # Avoid expensive logic for single queue case.
    if len(queues) == 1:
        while True:
            item = await queues[0].get()
            yield item
        return

    # Maintain one persistent get-task per queue; re-arm only the queue(s) that delivered
    task_to_index: dict[asyncio.Task[T], int] = {}
    for index, queue in enumerate(queues):
        task_to_index[asyncio.create_task(queue.get())] = index

    try:
        while True:
            done, _pending = await asyncio.wait(
                task_to_index.keys(), return_when=asyncio.FIRST_COMPLETED
            )

            for finished in done:
                index = task_to_index.pop(finished)
                item = await finished
                yield item

                # Drain burst for this queue before re-arming
                queue = queues[index]
                while True:
                    try:
                        next_item = queue.get_nowait()
                        yield next_item
                    except asyncio.QueueEmpty:
                        break

                # Re-arm the completed queue
                task_to_index[asyncio.create_task(queues[index].get())] = index
    finally:
        for task in task_to_index.keys():
            task.cancel()
