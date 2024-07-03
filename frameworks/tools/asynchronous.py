import asyncio
import uvloop
import os


def initialize_event_loop() -> None:
    """
    Initialize the event loop based on the operating system.

    For Windows, it does nothing (uses default event loop).
    For other operating systems, it sets up a new uvloop event loop.

    Returns
    -------
    None
    """

    if os.name == "nt":  # Check if the operating system is Windows
        pass

    else:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
