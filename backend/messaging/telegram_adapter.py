"""Telegram Bot API adapter using raw HTTP (no library dependency).

Uses long polling via getUpdates to receive messages and the
sendMessage endpoint to reply. All communication goes through
aiohttp against the Telegram Bot API.
"""

import asyncio
from typing import Any, Optional

import aiohttp

from .base import BaseAdapter, NormalizedMessage

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramAdapter(BaseAdapter):
    """Telegram messaging adapter via the Bot API.

    Args:
        bot_token: Telegram bot token from @BotFather.
        poll_timeout: Long-poll timeout in seconds (default 30).
    """

    def __init__(self, bot_token: str, poll_timeout: int = 30):
        super().__init__()
        self._token = bot_token
        self._poll_timeout = poll_timeout
        self._base_url = TELEGRAM_API_BASE.format(token=bot_token)
        self._session: Optional[aiohttp.ClientSession] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._last_update_id: int = 0

    @property
    def platform_name(self) -> str:
        return "telegram"

    async def connect(self) -> None:
        """Verify the bot token and start the long-polling loop."""
        self._session = aiohttp.ClientSession()

        me = await self._api_call("getMe")
        if not me.get("ok"):
            await self._session.close()
            raise RuntimeError(
                f"Telegram auth failed: {me.get('description', 'unknown error')}"
            )

        bot_info = me["result"]
        print(
            f"[Telegram] Authenticated as @{bot_info.get('username', '?')} "
            f"(id: {bot_info.get('id')})"
        )

        self._connected = True
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def disconnect(self) -> None:
        """Stop polling and close the HTTP session."""
        self._connected = False

        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

        print("[Telegram] Disconnected")

    async def send_message(
        self,
        channel: str,
        text: str,
        attachments: Optional[list[dict]] = None,
    ) -> dict:
        """Send a text message to a Telegram chat.

        Args:
            channel: Telegram chat_id (string or numeric).
            text: Message text (supports Markdown via parse_mode).
            attachments: Not yet implemented for Telegram.

        Returns:
            Dict with 'success' and 'message_id'.
        """
        payload: dict[str, Any] = {
            "chat_id": channel,
            "text": text,
            "parse_mode": "Markdown",
        }

        result = await self._api_call("sendMessage", payload)

        if result.get("ok"):
            msg_id = result["result"].get("message_id", "")
            return {"success": True, "message_id": str(msg_id)}

        error = result.get("description", "unknown error")
        return {"success": False, "error": error}

    # -- Internal methods -----------------------------------------------------

    async def _api_call(
        self, method: str, data: Optional[dict] = None
    ) -> dict:
        """Make a POST request to the Telegram Bot API.

        Args:
            method: API method name (e.g. 'sendMessage').
            data: Optional JSON body.

        Returns:
            Parsed JSON response.
        """
        if self._session is None or self._session.closed:
            raise RuntimeError("Telegram session not initialized")

        url = f"{self._base_url}/{method}"
        async with self._session.post(url, json=data or {}) as resp:
            return await resp.json()

    async def _poll_loop(self) -> None:
        """Long-poll getUpdates in a background loop."""
        print("[Telegram] Polling started")

        while self._connected:
            try:
                params = {
                    "offset": self._last_update_id + 1,
                    "timeout": self._poll_timeout,
                    "allowed_updates": ["message"],
                }
                result = await self._api_call("getUpdates", params)

                if not result.get("ok"):
                    print(
                        f"[Telegram] getUpdates error: "
                        f"{result.get('description', 'unknown')}"
                    )
                    await asyncio.sleep(5)
                    continue

                for update in result.get("result", []):
                    self._last_update_id = update["update_id"]
                    await self._process_update(update)

            except asyncio.CancelledError:
                break
            except aiohttp.ClientError as e:
                print(f"[Telegram] Network error during polling: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[Telegram] Unexpected polling error: {e}")
                await asyncio.sleep(5)

        print("[Telegram] Polling stopped")

    async def _process_update(self, update: dict) -> None:
        """Process a single Telegram update and forward as NormalizedMessage."""
        message = update.get("message")
        if message is None:
            return

        text = message.get("text", "")
        chat = message.get("chat", {})
        sender_info = message.get("from", {})
        chat_id = str(chat.get("id", ""))

        sender_name = sender_info.get("username", "")
        if not sender_name:
            first = sender_info.get("first_name", "")
            last = sender_info.get("last_name", "")
            sender_name = f"{first} {last}".strip() or str(
                sender_info.get("id", "unknown")
            )

        if text == "/start":
            await self.send_message(
                chat_id,
                "Connected to R.U.T.H. You can now send messages here and "
                "I will respond.",
            )
            return

        attachments: list[dict] = []
        if message.get("photo"):
            largest = message["photo"][-1]
            attachments.append({
                "type": "photo",
                "file_id": largest.get("file_id", ""),
            })
        if message.get("document"):
            doc = message["document"]
            attachments.append({
                "type": "document",
                "file_id": doc.get("file_id", ""),
                "file_name": doc.get("file_name", ""),
            })

        normalized = NormalizedMessage(
            platform="telegram",
            sender=sender_name,
            text=text,
            attachments=attachments,
            thread_id=chat_id,
            timestamp=message.get("date", 0),
            raw=message,
        )

        if self._message_callback:
            await self._message_callback(normalized)
