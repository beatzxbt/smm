import asyncio
from typing import Coroutine
from mm_toolbox.logging.standard.handlers.base import BaseLogHandler

class TelegramLogHandler(BaseLogHandler):
    """
    A log handler that sends messages to a Telegram chat via bot API.
    """

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """
        Initialize the TelegramLogHandler with bot token and chat ID.

        Args:
            bot_token (str): The Telegram bot token for authorization.
            chat_id (str): The ID of the Telegram chat to receive messages.
        """
        super().__init__()
        self.chat_id = chat_id
        self.url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.headers = {"Content-Type": "application/json"}
        self.payload = {
            "chat_id": self.chat_id,
            "text": "",
            "disable_web_page_preview": True,
        }

    async def push(self, buffer):
        try:
            tasks = []
            for log_msg in buffer:
                self.payload["text"] = log_msg
                tasks.append(
                    self.http_session.post(
                        url=self.url,
                        headers=self.headers,
                        data=self.json_encode(self.payload),
                    )
                )
            await asyncio.gather(*tasks)

        except Exception as e:
            print(f"Failed to send message to Telegram; {e}")
