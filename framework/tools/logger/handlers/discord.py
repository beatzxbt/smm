import asyncio
from typing import List, Coroutine
from mm_toolbox.logging.standard.handlers.base import BaseLogHandler

class DiscordLogHandler(BaseLogHandler):
    """
    A log handler that sends messages to a Discord webhook.
    """
    def __init__(self, webhook: str):
        """
        Initializes the DiscordLogHandler.

        Args:
            webhook (str): The Discord webhook URL.

        Raises:
            ValueError: If webhook is invalid.
        """
        super().__init__()
        
        if not webhook.startswith("https://discord.com/api/webhooks/"):
            raise ValueError(f"Invalid webhook format; expected 'https://discord.com/api/webhooks/*' but got {webhook}")
        
        self.url = webhook
        self.headers = {"Content-Type": "application/json"}

    async def push(self, buffer):
        try:
            tasks = []

            for log_msg in buffer:
                tasks.append(
                    self.http_session.post(
                        url=self.url,
                        headers=self.headers,
                        data=self.json_encode({"content": log_msg}),
                    )
                )
            await asyncio.gather(*tasks)

        except Exception as e:
            print(f"Failed to send message to Discord; {e}")