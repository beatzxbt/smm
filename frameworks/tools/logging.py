import orjson
from aiohttp import ClientSession
from time import time_ns, strftime

def time_ms() -> int:
    return time_ns()//1_000_000

def time_now() -> str:
    return strftime("%Y-%m-%d %H:%M:%S") + f".{(time_ns()//1000) % 1000000:05d}"

class Logger:
    def __init__(self, print_to_console: bool=True, discord_webhook: str="") -> None:
        self.print_to_console = print_to_console

        self.discord_webhook = discord_webhook
        self.send_to_discord = bool(discord_webhook)
        self.discord_client = None
        self.discord_data = {"content": ""}
        self.discord_headers = {"Content-Type": "application/json"}
        
    async def get_discord_client(self) -> ClientSession:
        if not self.discord_client:
            self.discord_client = ClientSession()
            await self.info("Starting up logger...")

        return self.discord_client

    async def close(self) -> None:
        if self.discord_client:
            await self.warning("Shutting down logger...")
            await self.discord_client.close()
            self.discord_client = None

    async def _message_(self, level: str, msg: str) -> None:
        if self.print_to_console:
            print(f"{time_now()} | {level} | {msg}")
        
        if self.send_to_discord:
            self.discord_data["content"] = msg

            await self.get_discord_client().post(
                url=self.discord_webhook, 
                data=orjson.dumps(self.discord_data).decode(), 
                headers=self.discord_headers
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