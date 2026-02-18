"""Discord bot adapter for R.U.T.H. V3 messaging system.

Uses discord.py to connect to the Discord Gateway and route messages
through the messaging broker.
"""

import asyncio
from typing import Optional

from .base import BaseAdapter, NormalizedMessage


class DiscordAdapter(BaseAdapter):
    """Discord messaging adapter using discord.py.

    Connects to Discord Gateway with proper heartbeat, intents, and
    message handling. Routes incoming messages through the broker's
    normalized message format.
    """

    def __init__(self, bot_token: str):
        super().__init__()
        self._token = bot_token
        self._client = None
        self._bot_task = None

    @property
    def platform_name(self) -> str:
        return "discord"

    async def connect(self) -> None:
        """Start the Discord bot connection."""
        try:
            import discord
        except ImportError:
            raise ImportError(
                "Discord adapter requires the discord.py library.\n"
                "Install it with: pip install discord.py\n"
                "Then restart R.U.T.H. to enable Discord messaging."
            )

        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True

        self._client = discord.Client(intents=intents)
        adapter_ref = self

        @self._client.event
        async def on_ready():
            print(f"[DISCORD] Connected as {self._client.user}")
            adapter_ref._connected = True

        @self._client.event
        async def on_message(message):
            # Ignore messages from the bot itself
            if message.author == self._client.user:
                return

            # Normalize and forward
            normalized = NormalizedMessage(
                platform="discord",
                sender=str(message.author),
                sender_id=str(message.author.id),
                text=message.content,
                thread_id=str(message.channel.id),
                raw={"guild_id": str(message.guild.id) if message.guild else None},
            )

            if adapter_ref._message_callback:
                try:
                    await adapter_ref._message_callback(normalized)
                except Exception as e:
                    print(f"[DISCORD] Message callback error: {e}")

        # Run the bot in a background task
        self._bot_task = asyncio.create_task(self._run_bot())

    async def _run_bot(self):
        """Run the Discord client, handling reconnections."""
        try:
            await self._client.start(self._token)
        except Exception as e:
            print(f"[DISCORD] Bot connection error: {e}")
            self._connected = False

    async def disconnect(self) -> None:
        """Disconnect from Discord gateway."""
        if self._client and not self._client.is_closed():
            await self._client.close()
        if self._bot_task and not self._bot_task.done():
            self._bot_task.cancel()
            try:
                await self._bot_task
            except asyncio.CancelledError:
                pass
        self._connected = False
        print("[DISCORD] Disconnected")

    async def send_message(
        self,
        channel: str,
        text: str,
        attachments: Optional[list[dict]] = None,
    ) -> dict:
        """Send a message to a Discord channel.

        Args:
            channel: Discord channel ID (numeric string).
            text: Message content.
            attachments: Not yet implemented.

        Returns:
            Result dict with success status.
        """
        if not self._connected or not self._client:
            return {"success": False, "error": "Discord adapter not connected."}

        try:
            channel_id = int(channel)
            discord_channel = self._client.get_channel(channel_id)

            if not discord_channel:
                # Try fetching if not cached
                try:
                    discord_channel = await self._client.fetch_channel(channel_id)
                except Exception:
                    return {"success": False, "error": f"Channel {channel} not found."}

            sent = await discord_channel.send(text)
            return {"success": True, "message_id": str(sent.id)}
        except Exception as e:
            return {"success": False, "error": f"Discord send error: {e}"}
