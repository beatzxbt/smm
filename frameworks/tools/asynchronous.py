import asyncio
import uvloop
import contextlib
import signal
import os

def initialize_event_loop() -> None:
    """
    Initialize the event loop based on the operating system.

    For Windows, it sets up a new asyncio event loop. 
    For other operating systems, it sets up a new uvloop event loop.
    It also adds signal handlers for SIGINT and SIGTERM to handle stop signals.

    Returns
    -------
    None
    """
    def _handle_stop_signals(sig):
        loop = asyncio.get_event_loop()
        loop.stop()

    if os.name == 'nt':  # Check if the operating system is Windows
        _loop = asyncio.new_event_loop()
        with contextlib.suppress(ValueError):
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, _handle_stop_signals)
    else:
        _loop = uvloop.new_event_loop()
        with contextlib.suppress(ValueError):
            for sig in (signal.SIGINT, signal.SIGTERM):
                _loop.add_signal_handler(sig, _handle_stop_signals)

    asyncio.set_event_loop(_loop)
