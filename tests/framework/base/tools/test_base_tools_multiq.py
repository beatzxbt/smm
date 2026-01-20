import asyncio

import pytest

from framework.base.tools.multiq import consume_multiq


@pytest.mark.asyncio
async def test_empty_queues_list():
    """Test that empty queues list returns immediately."""
    queues = []
    result = []
    async for item in consume_multiq(queues):
        result.append(item)
        if len(result) > 0:  # Should never reach here
            break
    assert result == []


@pytest.mark.asyncio
async def test_single_queue():
    """Test consuming from a single queue."""
    queue = asyncio.Queue()
    queues = [queue]

    # Add test items
    for i in range(3):
        queue.put_nowait(i)

    result = []
    async for item in consume_multiq(queues):
        result.append(item)
        if len(result) == 3:
            break

    assert result == [0, 1, 2]


@pytest.mark.asyncio
async def test_multiple_queues_interleaved():
    """Test consuming from multiple queues with interleaved items."""
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()
    queues = [queue1, queue2]

    # Add items to both queues
    queue1.put_nowait("a1")
    queue2.put_nowait("b1")
    queue1.put_nowait("a2")
    queue2.put_nowait("b2")

    result = []
    async for item in consume_multiq(queues):
        result.append(item)
        if len(result) == 4:
            break

    # Order is not guaranteed, but all items should be present
    assert set(result) == {"a1", "b1", "a2", "b2"}
    assert len(result) == 4


@pytest.mark.asyncio
async def test_burst_draining():
    """Test that burst items from the same queue are drained before re-arming."""
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()
    queues = [queue1, queue2]

    # Add multiple items to queue1 (burst)
    for i in range(5):
        queue1.put_nowait(f"q1_{i}")

    queue2.put_nowait("q2_0")

    result = []
    queue_sources = []

    async for item in consume_multiq(queues):
        result.append(item)
        if item.startswith("q1"):
            queue_sources.append(1)
        else:
            queue_sources.append(2)

        if len(result) == 6:
            break

    assert len(result) == 6
    assert set(result) == {f"q1_{i}" for i in range(5)} | {"q2_0"}


@pytest.mark.asyncio
async def test_async_producer_consumer():
    """Test with async producers adding items while consuming."""
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()
    queues = [queue1, queue2]

    async def producer1():
        for i in range(3):
            await asyncio.sleep(0.01)
            queue1.put_nowait(f"p1_{i}")

    async def producer2():
        for i in range(3):
            await asyncio.sleep(0.015)
            queue2.put_nowait(f"p2_{i}")

    async def consumer():
        result = []
        async for item in consume_multiq(queues):
            result.append(item)
            if len(result) == 6:
                break
        return result

    # Start producers and consumer concurrently
    producer1_task = asyncio.create_task(producer1())
    producer2_task = asyncio.create_task(producer2())
    consumer_task = asyncio.create_task(consumer())

    result = await consumer_task
    await producer1_task
    await producer2_task

    assert len(result) == 6
    assert set(result) == {f"p1_{i}" for i in range(3)} | {f"p2_{i}" for i in range(3)}


@pytest.mark.asyncio
async def test_queue_becomes_empty():
    """Test behavior when queues become empty during consumption."""
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()
    queues = [queue1, queue2]

    # Add initial items
    queue1.put_nowait("initial1")
    queue2.put_nowait("initial2")

    result = []

    async def delayed_producer():
        await asyncio.sleep(0.05)
        queue1.put_nowait("delayed")

    producer_task = asyncio.create_task(delayed_producer())

    async for item in consume_multiq(queues):
        result.append(item)
        if len(result) == 3:
            break

    await producer_task

    assert len(result) == 3
    assert set(result) == {"initial1", "initial2", "delayed"}


@pytest.mark.asyncio
async def test_cancellation_cleanup():
    """Test that tasks are properly cancelled when consumption is stopped."""
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()
    queues = [queue1, queue2]

    consumer_gen = consume_multiq(queues)

    # Start consumption with a timeout to avoid blocking
    try:
        await asyncio.wait_for(consumer_gen.__anext__(), timeout=0.1)
    except TimeoutError:
        # Expected since queues are empty
        pass

    # Close the generator to trigger cleanup
    await consumer_gen.aclose()

    # Add items to ensure queues aren't blocking other operations
    queue1.put_nowait("test")
    assert queue1.get_nowait() == "test"


@pytest.mark.asyncio
async def test_different_data_types():
    """Test consuming different data types from queues."""
    queue1 = asyncio.Queue()
    queue2 = asyncio.Queue()
    queues = [queue1, queue2]

    # Add different types
    queue1.put_nowait(42)
    queue1.put_nowait({"key": "value"})
    queue2.put_nowait([1, 2, 3])
    queue2.put_nowait(None)

    result = []
    async for item in consume_multiq(queues):
        result.append(item)
        if len(result) == 4:
            break

    assert len(result) == 4
    assert 42 in result
    assert {"key": "value"} in result
    assert [1, 2, 3] in result
    assert None in result
