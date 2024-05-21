import orjson
import aiosonic
from time import time_ns, strftime


def time_ms() -> int:
    """
    Get the current time in milliseconds since the epoch.

    Returns
    -------
    int
        The current time in milliseconds.
    """
    return time_ns() // 1_000_000


def time_now() -> str:
    """
    Get the current time in the format 'YYYY-MM-DD HH:MM:SS.microseconds'.

    Returns
    -------
    str
        The current time string.
    """
    return strftime("%Y-%m-%d %H:%M:%S") + f".{(time_ns()//1000) % 1000000:05d}"


class Logger:
    def __init__(
        self, print_to_console: bool = True, discord_webhook: str = ""
    ) -> None:
        self.print_to_console = print_to_console

        self.discord_webhook = discord_webhook
        self.send_to_discord = bool(discord_webhook)
        self.discord_client = None
        self.discord_data = {"content": ""}
        self.discord_headers = {"Content-Type": "application/json"}

    async def get_discord_client(self) -> aiosonic.HTTPClient:
        """
        Get the Discord client session.

        Returns
        -------
        aiosonic.HTTPClient
            The Discord client session.
        """
        if not self.discord_client:
            self.discord_client = aiosonic.HTTPClient()
            await self.info("Starting up logger...")

        return self.discord_client

    async def close(self) -> None:
        """
        Close the logger.

        Returns
        -------
        None
        """
        if self.discord_client:
            await self.warning("Shutting down logger...")
            self.discord_client.shutdown() # TODO: Incorrect shutdown method!
            self.discord_client = None

    async def _message_(self, level: str, msg: str) -> None:
        """
        Log a message with a specified logging level.

        Parameters
        ----------
        level : str
            The logging level of the message.

        msg : str
            The message to log.

        Returns
        -------
        None
        """
        formatted_msg = f"{time_now()} | {level} | {msg}"

        if self.print_to_console:
            print(formatted_msg)

        if self.send_to_discord:
            self.discord_data["content"] = formatted_msg

            await self.get_discord_client().post(
                url=self.discord_webhook,
                data=orjson.dumps(self.discord_data).decode(),
                headers=self.discord_headers,
            )

    async def success(self, msg: str) -> None:
        await self._message_("SUCCESS", msg)

    async def info(self, msg: str) -> None:
        await self._message_("INFO", msg)

    async def debug(self, msg: str) -> None:
        await self._message_("DEBUG", msg)

    async def warning(self, msg: str) -> None:
        await self._message_("WARNING", msg)

    async def error(self, msg: str) -> None:
        await self._message_("ERROR", msg)

    async def critical(self, msg: str) -> None:
        await self._message_("CRITICAL", msg)
