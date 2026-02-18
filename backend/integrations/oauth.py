"""OAuth2 flow handler for service integrations.

Manages token storage, refresh, and the authorization code exchange flow.
Tokens are stored as JSON files in ~/.ruth/tokens/<service>.json.
"""

import json
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import aiohttp


class OAuthManager:
    """Handles OAuth2 authorization flows and token persistence.

    Token file format per service:
        {
            "access_token": "...",
            "refresh_token": "...",
            "expires_at": 1700000000,
            "scopes": ["scope1", "scope2"]
        }
    """

    def __init__(self, tokens_dir: str = "~/.ruth/tokens"):
        self._tokens_dir = Path(tokens_dir).expanduser()
        self._tokens_dir.mkdir(parents=True, exist_ok=True)
        self._pending_flows: dict[str, dict] = {}

    def _token_path(self, service: str) -> Path:
        """Return the path to a service's token file."""
        safe_name = service.replace("/", "_").replace("\\", "_")
        return self._tokens_dir / f"{safe_name}.json"

    def get_token(self, service: str) -> Optional[dict]:
        """Load stored token data for a service.

        Args:
            service: Service identifier (e.g. 'gmail', 'calendar').

        Returns:
            Token dict if file exists, None otherwise.
        """
        path = self._token_path(service)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[OAuth] Failed to read token for '{service}': {e}")
            return None

    def save_token(self, service: str, token_data: dict) -> None:
        """Persist token data for a service.

        Args:
            service: Service identifier.
            token_data: Dict with access_token, refresh_token, expires_at, scopes.
        """
        path = self._token_path(service)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(token_data, f, indent=2)
        path.chmod(0o600)
        print(f"[OAuth] Saved token for '{service}'")

    def delete_token(self, service: str) -> bool:
        """Remove stored tokens for a service.

        Returns:
            True if a token file was deleted.
        """
        path = self._token_path(service)
        if path.exists():
            path.unlink()
            print(f"[OAuth] Deleted token for '{service}'")
            return True
        return False

    def is_token_expired(self, service: str) -> bool:
        """Check if the stored access token has expired.

        Returns True if expired or if no token exists.
        """
        token = self.get_token(service)
        if token is None:
            return True
        expires_at = token.get("expires_at", 0)
        return time.time() >= expires_at

    def start_auth_flow(
        self,
        service: str,
        client_id: str,
        scopes: list[str],
        redirect_uri: str,
        auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth",
    ) -> str:
        """Begin an OAuth2 authorization code flow.

        Stores flow parameters for later use in handle_callback() and
        returns the URL the user should visit to authorize.

        Args:
            service: Service identifier.
            client_id: OAuth client ID.
            scopes: List of OAuth scope strings.
            redirect_uri: Where the provider redirects after auth.
            auth_url: Authorization endpoint (default: Google).

        Returns:
            The full authorization URL to present to the user.
        """
        self._pending_flows[service] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
        }

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{auth_url}?{urlencode(params)}"

    async def handle_callback(
        self,
        service: str,
        code: str,
        client_secret: str,
        token_url: str = "https://oauth2.googleapis.com/token",
    ) -> dict:
        """Exchange an authorization code for access and refresh tokens.

        Args:
            service: Service identifier (must match a pending flow).
            code: Authorization code from the callback.
            client_secret: OAuth client secret.
            token_url: Token exchange endpoint (default: Google).

        Returns:
            Normalized token dict that was also saved to disk.

        Raises:
            ValueError: If no pending flow exists for the service.
            RuntimeError: If the token exchange fails.
        """
        flow = self._pending_flows.pop(service, None)
        if flow is None:
            raise ValueError(
                f"No pending OAuth flow for '{service}'. "
                f"Call start_auth_flow() first."
            )

        payload = {
            "code": code,
            "client_id": flow["client_id"],
            "client_secret": client_secret,
            "redirect_uri": flow["redirect_uri"],
            "grant_type": "authorization_code",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=payload) as resp:
                data = await resp.json()
                if resp.status != 200:
                    error = data.get("error_description", data.get("error", "unknown"))
                    raise RuntimeError(
                        f"Token exchange failed for '{service}': {error}"
                    )

        token_data = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": time.time() + data.get("expires_in", 3600),
            "scopes": flow["scopes"],
        }
        self.save_token(service, token_data)
        return token_data

    async def refresh_token(
        self,
        service: str,
        client_id: str,
        client_secret: str,
        token_url: str = "https://oauth2.googleapis.com/token",
    ) -> dict:
        """Refresh an expired access token using the stored refresh token.

        Args:
            service: Service identifier.
            client_id: OAuth client ID.
            client_secret: OAuth client secret.
            token_url: Token refresh endpoint (default: Google).

        Returns:
            Updated token dict.

        Raises:
            ValueError: If no refresh token is stored.
            RuntimeError: If the refresh request fails.
        """
        existing = self.get_token(service)
        if existing is None or not existing.get("refresh_token"):
            raise ValueError(
                f"No refresh token stored for '{service}'. Re-authorize."
            )

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": existing["refresh_token"],
            "grant_type": "refresh_token",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=payload) as resp:
                data = await resp.json()
                if resp.status != 200:
                    error = data.get("error_description", data.get("error", "unknown"))
                    raise RuntimeError(
                        f"Token refresh failed for '{service}': {error}"
                    )

        token_data = {
            "access_token": data["access_token"],
            "refresh_token": existing["refresh_token"],
            "expires_at": time.time() + data.get("expires_in", 3600),
            "scopes": existing.get("scopes", []),
        }
        self.save_token(service, token_data)
        return token_data

    async def get_valid_token(
        self,
        service: str,
        client_id: str,
        client_secret: str,
    ) -> Optional[str]:
        """Return a valid access token, refreshing if necessary.

        Convenience method for integrations -- call this instead of
        manually checking expiry.

        Returns:
            The access token string, or None if no token exists.
        """
        token = self.get_token(service)
        if token is None:
            return None

        if self.is_token_expired(service):
            try:
                token = await self.refresh_token(service, client_id, client_secret)
            except (ValueError, RuntimeError) as e:
                print(f"[OAuth] Could not refresh token for '{service}': {e}")
                return None

        return token.get("access_token")
