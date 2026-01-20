"""CLI entry point for running an SMM trader.

Usage: run `python -m smm` after configuring `smm/config.toml`.
Components: config loader, logger setup, trader instantiation.
"""

from __future__ import annotations

import os

import uvloop

from mm_toolbox.logging.standard import FileLogHandler, Logger

from smm.config import load_config
from smm.traders import load_trader


CONFIG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.toml")


async def run() -> None:
    """Run the configured trader.

    Returns:
        None.
    """
    logger = Logger(
        name="SMM",
        handlers=[
            FileLogHandler(
                filepath=os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), "logs.txt"
                ),
                create=True,
            )
        ],
    )

    config = load_config(CONFIG_FILE)
    trader_cls = load_trader(config.core.trader)
    trader = await trader_cls.create(config=config, logger=logger)
    await trader.run()


if __name__ == "__main__":
    uvloop.run(run())
