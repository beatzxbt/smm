import os
import orjson
import aiosonic
import asyncio
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
        self,
        debug_mode: bool = False,
    ) -> None:
        self.debug_mode = debug_mode

        self.discord_client = None
        self.telegram_client = None

        self.send_to_discord = bool(os.getenv("DISCORD_WEBHOOK"))
        if self.send_to_discord:
            self.discord_client = DiscordClient()
            self.discord_client.start(os.getenv("DISCORD_WEBHOOK"))

        self.send_to_telegram = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
        if self.send_to_telegram:
            self.telegram_client = TelegramClient()
            self.telegram_client.start(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"))

        self.tasks = []

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
            task = asyncio.create_task(self.discord_client.send(formatted_msg))
            self.tasks.append(task)

        if self.send_to_telegram:
            task = asyncio.create_task(self.telegram_client.send(formatted_msg))
            self.tasks.append(task)

    async def success(self, msg: str) -> None:
        await self._message_("SUCCESS", msg)

    async def info(self, msg: str) -> None:
        await self._message_("INFO", msg)

    async def debug(self, msg: str) -> None:
        if self.debug_mode:
            await self._message_("DEBUG", msg)

    async def warning(self, msg: str) -> None:
        await self._message_("WARNING", msg)

    async def error(self, msg: str) -> None:
        await self._message_("ERROR", msg)

    async def critical(self, msg: str) -> None:
        await self._message_("CRITICAL", msg)

    async def shutdown(self) -> None:
        """
        Shutdown the logger by ensuring all clients are closed and all tasks are complete.

        Returns
        -------
        None
        """
        if self.discord_client:
            await self.discord_client.shutdown()

        if self.telegram_client:
            await self.telegram_client.shutdown()

        if self.tasks:
            await asyncio.gather(*self.tasks)

class DiscordClient:
    """
    A client for sending messages to a Discord channel using a webhook URL with buffering capabilities.
    """
    def __init__(self, buffer_size: int = 5) -> None:
        self.max_buffer_size = buffer_size
        self.buffer = []

        self.client = None
        self.webhook = None
        self.data = {"content": ""}
        self.headers = {"Content-Type": "application/json"}

        self.tasks = []

    def start(self, webhook: str) -> None:
        """
        Initialize the Discord client with the provided webhook URL.

        Parameters
        ----------
        webhook : str
            The webhook URL for the Discord channel.

        Returns
        -------
        None
        """
        self.webhook = webhook
        self.client = aiosonic.HTTPClient()

    async def send(self, content: str, flush_buffer: bool = False) -> None:
        """
        Send a message to a Discord channel.

        Parameters
        ----------
        content : str
            The formatted message to send.

        flush_buffer : bool, optional
            Whether to flush the buffer and send all buffered messages immediately (default is False).

        Returns
        -------
        None
        """
        try:
            if not self.client or not self.webhook:
                raise RuntimeError("Client not initialized or webhook URL not set.")

            self.data["content"] = content
            self.buffer.append(self.data.copy())

            if len(self.buffer) >= self.max_buffer_size or flush_buffer:
                for message in self.buffer:
                    await self.client.post(
                        url=self.webhook,
                        data=orjson.dumps(message).decode(),
                        headers=self.headers,
                    )

                self.buffer.clear()

        except Exception as e:
            print(f"Failed to send message to Discord: {e}")

    async def shutdown(self) -> None:
        """
        Close the async client, if existing, and ensure all tasks are complete.

        Returns
        -------
        None
        """
        if self.tasks:
            await asyncio.gather(*self.tasks)

        if self.client:
            await self.send("Shutting down logger.", flush_buffer=True)
            await asyncio.sleep(1.0)
            await self.client.connector.cleanup()
            await self.client.__aexit__(None, None, None)
            del self.client

class TelegramClient:
    """
    A client for sending messages to a Telegram channel using a bot token and chat ID with buffering capabilities.
    """
    def __init__(self, buffer_size: int = 5) -> None:
        self.max_buffer_size = buffer_size
        self.buffer = []

        self.client = None
        self.bot_token = None
        self.chat_id = None
        self.data = {"text": ""}
        self.headers = {"Content-Type": "application/json"}

        self.tasks = []

    def start(self, bot_token: str, chat_id: str) -> None:
        """
        Initialize the Telegram client with the provided bot token and chat ID.

        Parameters
        ----------
        bot_token : str
            The bot token for the Telegram bot.

        chat_id : str
            The chat ID of the Telegram channel.

        Returns
        -------
        None
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = aiosonic.HTTPClient()

    async def send(self, content: str, flush_buffer: bool = False) -> None:
        """
        Send a message to a Telegram channel.

        Parameters
        ----------
        content : str
            The formatted message to send.

        flush_buffer : bool, optional
            Whether to flush the buffer and send all buffered messages immediately (default is False).

        Returns
        -------
        None
        """
        try:
            if not self.client or not self.bot_token or not self.chat_id:
                raise RuntimeError("Client not initialized, bot token, or chat ID not set.")

            self.data["text"] = content
            self.buffer.append(self.data.copy())

            if len(self.buffer) >= self.max_buffer_size or flush_buffer:
                for message in self.buffer:
                    await self.client.post(
                        url=f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_id}",
                        data=orjson.dumps(message).decode(),
                        headers=self.headers,
                    )

                self.buffer.clear()

        except Exception as e:
            print(f"Failed to send message to Telegram: {e}")

    async def shutdown(self) -> None:
        """
        Close the async client, if existing, and ensure all tasks are complete.

        Returns
        -------
        None
        """
        if self.tasks:
            await asyncio.gather(*self.tasks)

        if self.client:
            await self.send("Shutting down logger.", flush_buffer=True)
            await asyncio.sleep(1.0)
            await self.client.connector.cleanup()
            await self.client.__aexit__(None, None, None)
            del self.client
