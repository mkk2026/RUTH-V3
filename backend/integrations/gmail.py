"""Gmail integration using raw REST API calls.

Provides tools for listing, reading, sending, and searching emails
via the Gmail API. Requires OAuth2 tokens managed by OAuthManager.
"""

import base64
import json
from email.mime.text import MIMEText
from typing import Any, Optional

import aiohttp

from .base import BaseIntegration
from .oauth import OAuthManager

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailIntegration(BaseIntegration):
    """Gmail integration via REST API.

    Requires OAuth2 credentials with Gmail scopes. Uses OAuthManager
    for token storage and refresh.
    """

    def __init__(
        self,
        oauth: OAuthManager,
        client_id: str = "",
        client_secret: str = "",
    ):
        super().__init__()
        self._oauth = oauth
        self._client_id = client_id
        self._client_secret = client_secret
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "gmail"

    @property
    def description(self) -> str:
        return "Read, send, and search Gmail messages"

    async def setup(self) -> None:
        """Verify we have a valid Gmail token and open an HTTP session."""
        token = await self._oauth.get_valid_token(
            "gmail", self._client_id, self._client_secret
        )
        if token is None:
            raise RuntimeError(
                "No valid Gmail token. Run the OAuth flow first: "
                "oauth.start_auth_flow('gmail', client_id, "
                "['https://www.googleapis.com/auth/gmail.modify'], redirect_uri)"
            )
        self._session = aiohttp.ClientSession()
        self._connected = True
        print("[Gmail] Connected")

    async def teardown(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        self._connected = False
        print("[Gmail] Disconnected")

    def get_tools(self) -> list[dict]:
        return [
            {
                "name": "gmail_list_emails",
                "description": "List recent emails, optionally filtered by query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Gmail search query (e.g. 'is:unread')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of emails to return",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "gmail_read_email",
                "description": "Read the full content of a specific email by message ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The Gmail message ID",
                        },
                    },
                    "required": ["message_id"],
                },
            },
            {
                "name": "gmail_send_email",
                "description": "Send an email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line",
                        },
                        "body": {
                            "type": "string",
                            "description": "Plain-text email body",
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
            },
            {
                "name": "gmail_search_emails",
                "description": "Search emails with a Gmail query and return summaries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Gmail search query",
                        },
                    },
                    "required": ["query"],
                },
            },
        ]

    async def execute(self, tool_name: str, args: dict) -> dict:
        dispatch = {
            "gmail_list_emails": self._list_emails,
            "gmail_read_email": self._read_email,
            "gmail_send_email": self._send_email,
            "gmail_search_emails": self._search_emails,
        }
        handler = dispatch.get(tool_name)
        if handler is None:
            return await super().execute(tool_name, args)
        return await handler(**args)

    # -- Private API methods --------------------------------------------------

    async def _get_headers(self) -> dict[str, str]:
        """Build authorization headers, refreshing the token if needed."""
        token = await self._oauth.get_valid_token(
            "gmail", self._client_id, self._client_secret
        )
        if token is None:
            raise RuntimeError("Gmail token expired and could not be refreshed")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _api_get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make an authenticated GET request to the Gmail API."""
        if self._session is None or self._session.closed:
            raise RuntimeError("Gmail session not initialized. Call setup() first.")
        headers = await self._get_headers()
        url = f"{GMAIL_API_BASE}{path}"
        async with self._session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            if resp.status != 200:
                error = data.get("error", {}).get("message", str(data))
                raise RuntimeError(f"Gmail API error ({resp.status}): {error}")
            return data

    async def _api_post(self, path: str, body: dict) -> dict:
        """Make an authenticated POST request to the Gmail API."""
        if self._session is None or self._session.closed:
            raise RuntimeError("Gmail session not initialized. Call setup() first.")
        headers = await self._get_headers()
        url = f"{GMAIL_API_BASE}{path}"
        async with self._session.post(url, headers=headers, json=body) as resp:
            data = await resp.json()
            if resp.status not in (200, 202):
                error = data.get("error", {}).get("message", str(data))
                raise RuntimeError(f"Gmail API error ({resp.status}): {error}")
            return data

    async def _list_emails(
        self, query: str = "", max_results: int = 10
    ) -> dict:
        """List emails matching an optional query."""
        params: dict[str, Any] = {"maxResults": min(max_results, 100)}
        if query:
            params["q"] = query

        data = await self._api_get("/messages", params=params)
        messages = data.get("messages", [])

        results = []
        for msg_stub in messages:
            msg = await self._api_get(
                f"/messages/{msg_stub['id']}",
                params={"format": "metadata", "metadataHeaders": "Subject,From,Date"},
            )
            headers_map = {
                h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])
            }
            results.append({
                "id": msg["id"],
                "snippet": msg.get("snippet", ""),
                "subject": headers_map.get("Subject", "(no subject)"),
                "from": headers_map.get("From", ""),
                "date": headers_map.get("Date", ""),
            })

        return {"result": json.dumps(results, indent=2)}

    async def _read_email(self, message_id: str) -> dict:
        """Read the full content of a specific email."""
        msg = await self._api_get(
            f"/messages/{message_id}", params={"format": "full"}
        )

        headers_map = {
            h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])
        }

        body_text = self._extract_body(msg.get("payload", {}))

        return {
            "result": json.dumps({
                "id": msg["id"],
                "subject": headers_map.get("Subject", ""),
                "from": headers_map.get("From", ""),
                "to": headers_map.get("To", ""),
                "date": headers_map.get("Date", ""),
                "body": body_text,
                "labels": msg.get("labelIds", []),
            }, indent=2)
        }

    async def _send_email(self, to: str, subject: str, body: str) -> dict:
        """Send a plain-text email."""
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        data = await self._api_post("/messages/send", {"raw": raw})

        return {
            "result": f"Email sent successfully (id: {data.get('id', 'unknown')})"
        }

    async def _search_emails(self, query: str) -> dict:
        """Search emails and return summaries."""
        return await self._list_emails(query=query, max_results=20)

    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Recursively extract plain-text body from a Gmail message payload."""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        for part in payload.get("parts", []):
            text = GmailIntegration._extract_body(part)
            if text:
                return text

        return ""
