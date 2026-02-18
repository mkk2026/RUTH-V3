"""Webhook server for receiving external service callbacks.

Runs a lightweight aiohttp web server that routes incoming POST
requests to registered callback functions.
"""

import asyncio
import json
from typing import Any, Awaitable, Callable, Optional

from aiohttp import web


WebhookCallback = Callable[[dict], Awaitable[Any]]


class WebhookManager:
    """Manages a simple HTTP server for incoming webhooks.

    Register paths with callbacks, then start the server. Incoming POST
    requests to registered paths are parsed as JSON and dispatched to
    the corresponding callback.

    Usage:
        wh = WebhookManager(port=8001)
        wh.register_hook("/github", handle_github_event)
        await wh.start()
        ...
        await wh.stop()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8001):
        self._host = host
        self._port = port
        self._hooks: dict[str, WebhookCallback] = {}
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def registered_paths(self) -> list[str]:
        return list(self._hooks.keys())

    def register_hook(self, path: str, callback: WebhookCallback) -> None:
        """Register a callback for a webhook path.

        Args:
            path: URL path (e.g. '/github'). Leading slash is enforced.
            callback: Async function receiving the parsed JSON body as a dict.
        """
        if not path.startswith("/"):
            path = f"/{path}"
        self._hooks[path] = callback
        print(f"[Webhook] Registered hook: {path}")

    def unregister_hook(self, path: str) -> None:
        """Remove a registered webhook path.

        Args:
            path: The path to unregister.
        """
        if not path.startswith("/"):
            path = f"/{path}"
        if path in self._hooks:
            del self._hooks[path]
            print(f"[Webhook] Unregistered hook: {path}")
        else:
            print(f"[Webhook] Path '{path}' was not registered")

    async def start(self) -> None:
        """Start the webhook HTTP server."""
        if self._running:
            print("[Webhook] Server already running")
            return

        self._app = web.Application()
        self._app.router.add_post("/{path:.*}", self._handle_request)
        self._app.router.add_get("/health", self._handle_health)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

        self._running = True
        print(f"[Webhook] Server listening on {self._host}:{self._port}")

    async def stop(self) -> None:
        """Stop the webhook HTTP server."""
        if not self._running:
            return

        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

        self._app = None
        self._runner = None
        self._site = None
        self._running = False
        print("[Webhook] Server stopped")

    async def _handle_request(self, request: web.Request) -> web.Response:
        """Route incoming POST requests to registered callbacks."""
        path = f"/{request.match_info['path']}"

        callback = self._hooks.get(path)
        if callback is None:
            return web.json_response(
                {"error": f"No hook registered for '{path}'"},
                status=404,
            )

        try:
            body = await request.json()
        except json.JSONDecodeError:
            body = {"raw": await request.text()}

        try:
            result = await callback(body)
            response_data = {"status": "ok"}
            if result is not None:
                response_data["data"] = result
            return web.json_response(response_data)
        except Exception as e:
            print(f"[Webhook] Error in handler for '{path}': {e}")
            return web.json_response(
                {"error": f"Handler error: {str(e)}"},
                status=500,
            )

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Simple health check endpoint."""
        return web.json_response({
            "status": "ok",
            "hooks": list(self._hooks.keys()),
        })
