"""Slack bot adapter -- stub requiring slack-bolt.

This is a placeholder implementation. Slack's Socket Mode and
Events API are best handled by the official slack-bolt library
which manages connection lifecycle, retry logic, and event parsing.

Install: pip install slack-bolt
"""

from typing import Optional

from .base import BaseAdapter, NormalizedMessage


class SlackAdapter(BaseAdapter):
    """Slack messaging adapter (stub -- requires slack-bolt).

    Slack bots typically use either:
    - Socket Mode (websocket, no public URL needed)
    - Events API (webhook-based, needs public URL)

    The slack-bolt library supports both modes and handles token
    management, event parsing, retries, and ack responses.

    This stub checks for slack_bolt availability on connect() and
    raises a clear error with install instructions if it's missing.
    """

    def __init__(self, bot_token: str, app_token: str = ""):
        super().__init__()
        self._bot_token = bot_token
        self._app_token = app_token

    @property
    def platform_name(self) -> str:
        return "slack"

    async def connect(self) -> None:
        """Check for slack-bolt and raise ImportError if not installed."""
        try:
            import slack_bolt  # noqa: F401
        except ImportError:
            raise ImportError(
                "Slack adapter requires the slack-bolt library.\n"
                "Install it with: pip install slack-bolt\n"
                "Then restart R.U.T.H. to enable Slack messaging."
            )

        # TODO: Implement full Slack bot connection using slack-bolt
        # - Create slack_bolt.async_app.AsyncApp with bot_token
        # - If app_token provided, use Socket Mode
        # - Register message listener to forward to self._message_callback
        # - Start app in background task
        raise NotImplementedError(
            "Slack adapter is a stub. Full implementation pending. "
            "slack-bolt is installed -- implement the event listener."
        )

    async def disconnect(self) -> None:
        """Disconnect from Slack."""
        # TODO: Stop the slack-bolt app when implemented
        self._connected = False

    async def send_message(
        self,
        channel: str,
        text: str,
        attachments: Optional[list[dict]] = None,
    ) -> dict:
        """Send a message to a Slack channel.

        Args:
            channel: Slack channel ID (e.g. 'C01234ABCDE').
            text: Message text (supports Slack mrkdwn formatting).
            attachments: Not yet implemented.

        Returns:
            Error dict indicating stub status.
        """
        if not self._connected:
            return {
                "success": False,
                "error": "Slack adapter not connected. "
                "Full implementation requires slack-bolt.",
            }

        # TODO: Use app.client.chat_postMessage(channel=channel, text=text)
        return {
            "success": False,
            "error": "Slack send_message not yet implemented",
        }
