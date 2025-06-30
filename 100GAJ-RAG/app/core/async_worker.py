# File: app/core/async_worker.py

import asyncio
import threading
from typing import Coroutine, Any, AsyncGenerator

class AsyncWorker:
    """
    Manages a dedicated asyncio event loop running in a background thread.
    This allows a synchronous application (like Flask) to safely run
    async code without blocking or lifecycle conflicts.
    """
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def run_coroutine(self, coro: Coroutine) -> Any:
        """Runs a coroutine in the background loop and waits for the result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def run_async_generator(self, async_gen: AsyncGenerator) -> Any:
        """
        Iterates over an async generator from a synchronous context,
        yielding each item as it becomes available.
        """
        while True:
            try:
                future = asyncio.run_coroutine_threadsafe(async_gen.__anext__(), self._loop)
                yield future.result()
            except StopAsyncIteration:
                break

    def stop(self):
        """Stops the event loop and joins the thread."""
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()

# Create a single, global instance of the worker.
async_worker = AsyncWorker()