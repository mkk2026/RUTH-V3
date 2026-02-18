"""Abstract base class for platform messaging adapters."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


@dataclass
class NormalizedMessage:
    """Platform-agnostic message format.

    Every adapter normalizes incoming messages into this structure
    before forwarding to the broker.
    """
    platform: str
    sender: str
    text: str
    attachments: list[dict] = field(default_factory=list)
    thread_id: str = ""
    timestamp: float = 0.0
    raw: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "sender": self.sender,
            "text": self.text,
            "attachments": self.attachments,
            "thread_id": self.thread_id,
            "timestamp": self.timestamp,
        }


MessageCallback = Callable[[NormalizedMessage], Awaitable[Any]]


class BaseAdapter(ABC):
    """Abstract base class for all messaging platform adapters.

    Subclasses wrap a specific platform (Telegram, Discord, Slack, etc.)
    and normalize messages into NormalizedMessage format.

    Subclasses must implement:
        - platform_name: Unique platform identifier
        - connect(): Establish connection / start polling
        - disconnect(): Clean shutdown
        - send_message(): Send outbound message
    """

    def __init__(self):
        self._connected: bool = False
        self._message_callback: Optional[MessageCallback] = None

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Unique identifier for this platform (e.g. 'telegram', 'discord')."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether the adapter is currently connected and receiving messages."""
        return self._connected

    def on_message(self, callback: MessageCallback) -> None:
        """Register a callback invoked for every incoming message.

        The broker calls this during adapter registration to wire up
        message routing.

        Args:
            callback: Async function receiving a NormalizedMessage.
        """
        self._message_callback = callback

    @abstractmethod
    async def connect(self) -> None:
        """Start the adapter -- authenticate, open websocket / start polling.

        Should set self._connected = True on success.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Stop the adapter -- close connections, cancel background tasks.

        Should set self._connected = False.
        """
        ...

    @abstractmethod
    async def send_message(
        self,
        channel: str,
        text: str,
        attachments: Optional[list[dict]] = None,
    ) -> dict:
        """Send a message on this platform.

        Args:
            channel: Platform-specific channel/chat identifier.
            text: Message body.
            attachments: Optional list of attachment dicts.

        Returns:
            Dict with at least 'success' and 'message_id' keys.
        """
        ...
