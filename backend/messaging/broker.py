"""Central message broker -- routes messages between R.U.T.H. and platform adapters."""

import asyncio
from typing import Awaitable, Callable, Optional

from .base import BaseAdapter, NormalizedMessage


IncomingHandler = Callable[[NormalizedMessage], Awaitable[None]]


class MessageBroker:
    """Routes messages between R.U.T.H.'s core and multiple messaging platforms.

    All incoming messages from any platform are normalized and forwarded
    to a single handler. Outgoing messages from R.U.T.H. are dispatched to
    the correct platform adapter.

    Usage:
        broker = MessageBroker()
        broker.register_adapter(TelegramAdapter(token="..."))
        broker.set_handler(my_handler)
        await broker.start_all()
    """

    def __init__(self):
        self._adapters: dict[str, BaseAdapter] = {}
        self._handler: Optional[IncomingHandler] = None

    def set_handler(self, handler: IncomingHandler) -> None:
        """Set the single callback for all incoming messages.

        This is typically the R.U.T.H. core message processor that decides
        how to respond regardless of which platform the message arrived on.

        Args:
            handler: Async function receiving a NormalizedMessage.
        """
        self._handler = handler

    def register_adapter(self, adapter: BaseAdapter) -> None:
        """Register a platform adapter with the broker.

        Automatically wires the adapter's incoming-message callback
        to route through this broker.

        Args:
            adapter: An instance of a BaseAdapter subclass.
        """
        name = adapter.platform_name
        if name in self._adapters:
            print(f"[MessageBroker] Warning: overwriting adapter '{name}'")
        self._adapters[name] = adapter
        adapter.on_message(self._route_incoming)
        print(f"[MessageBroker] Registered adapter: {name}")

    def unregister_adapter(self, platform: str) -> None:
        """Remove a platform adapter.

        Args:
            platform: The platform_name of the adapter to remove.
        """
        if platform in self._adapters:
            del self._adapters[platform]
            print(f"[MessageBroker] Unregistered adapter: {platform}")

    def get_adapter(self, platform: str) -> Optional[BaseAdapter]:
        """Retrieve an adapter by platform name."""
        return self._adapters.get(platform)

    def list_adapters(self) -> list[dict]:
        """Return summary info for all registered adapters."""
        return [
            {
                "platform": adapter.platform_name,
                "connected": adapter.is_connected,
            }
            for adapter in self._adapters.values()
        ]

    async def start_all(self) -> dict[str, bool]:
        """Connect all registered adapters.

        Returns:
            Dict mapping platform name to connection success.
        """
        results: dict[str, bool] = {}
        for name, adapter in self._adapters.items():
            try:
                await adapter.connect()
                results[name] = True
                print(f"[MessageBroker] '{name}' connected")
            except Exception as e:
                results[name] = False
                print(f"[MessageBroker] '{name}' failed to connect: {e}")
        return results

    async def stop_all(self) -> None:
        """Disconnect all registered adapters."""
        for name, adapter in self._adapters.items():
            try:
                await adapter.disconnect()
                print(f"[MessageBroker] '{name}' disconnected")
            except Exception as e:
                print(f"[MessageBroker] '{name}' disconnect error: {e}")

    async def send(
        self,
        platform: str,
        channel: str,
        text: str,
        attachments: Optional[list[dict]] = None,
    ) -> dict:
        """Send a message to a specific platform and channel.

        Args:
            platform: Target platform name.
            channel: Platform-specific channel/chat ID.
            text: Message body.
            attachments: Optional attachments.

        Returns:
            Result dict from the adapter, or error dict.
        """
        adapter = self._adapters.get(platform)
        if adapter is None:
            return {"success": False, "error": f"No adapter for platform '{platform}'"}
        if not adapter.is_connected:
            return {
                "success": False,
                "error": f"Adapter '{platform}' is not connected",
            }
        try:
            return await adapter.send_message(channel, text, attachments)
        except Exception as e:
            print(f"[MessageBroker] Send error on '{platform}': {e}")
            return {"success": False, "error": str(e)}

    async def broadcast(
        self, text: str, channels: Optional[dict[str, str]] = None
    ) -> dict[str, dict]:
        """Send a message to all connected platforms.

        Args:
            text: Message body to broadcast.
            channels: Optional mapping of platform -> channel_id.
                      If not provided, adapters that don't need a channel
                      will still attempt delivery.

        Returns:
            Dict mapping platform name to send result.
        """
        channels = channels or {}
        results: dict[str, dict] = {}
        for name, adapter in self._adapters.items():
            if not adapter.is_connected:
                results[name] = {"success": False, "error": "not connected"}
                continue
            channel = channels.get(name, "")
            if not channel:
                results[name] = {"success": False, "error": "no channel specified"}
                continue
            results[name] = await self.send(name, channel, text)
        return results

    async def _route_incoming(self, message: NormalizedMessage) -> None:
        """Route an incoming message from any adapter to the handler."""
        if self._handler is None:
            print(
                f"[MessageBroker] No handler set, dropping message from "
                f"'{message.platform}': {message.text[:80]}"
            )
            return

        try:
            await self._handler(message)
        except Exception as e:
            print(
                f"[MessageBroker] Handler error for message from "
                f"'{message.platform}': {e}"
            )
