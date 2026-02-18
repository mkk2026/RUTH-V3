"""Health monitoring engine for R.U.T.H. V3.

Monitors URLs, TCP ports, and running processes at configurable intervals.
Fires callbacks on status changes for alerting and dashboard updates.
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import aiohttp


class HeartbeatMonitor:
    """Monitors the health of configurable targets (URLs, TCP ports, processes).

    Targets are persisted to ~/.ruth/heartbeat/targets.json. The monitor runs
    an async loop checking each target at its configured interval.

    Args:
        storage_path: Directory for target persistence.
        on_status_change: Callback invoked when a target's status changes.
            Signature: on_status_change(target, old_status, new_status)
    """

    TARGET_TYPES = {"url", "tcp", "process"}

    def __init__(
        self,
        storage_path: str = "~/.ruth/heartbeat",
        on_status_change: Optional[Callable] = None,
    ):
        self._storage_path = os.path.expanduser(storage_path)
        self._targets_file = os.path.join(self._storage_path, "targets.json")
        self._on_status_change = on_status_change
        self._targets: Dict[str, dict] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

        os.makedirs(self._storage_path, exist_ok=True)
        self._load_targets()
        print(f"[HeartbeatMonitor] Initialized ({len(self._targets)} targets loaded)")

    # ------------------------------------------------------------------
    # Target management
    # ------------------------------------------------------------------

    def add_target(
        self,
        name: str,
        target_type: str,
        target: str,
        interval_seconds: int = 60,
        enabled: bool = True,
    ) -> dict:
        """Add a new monitoring target.

        Args:
            name: Human-readable name for this target.
            target_type: One of "url", "tcp", "process".
            target: The target value:
                - url: Full URL (e.g. "https://example.com/health")
                - tcp: "host:port" (e.g. "127.0.0.1:5432")
                - process: Process name to search for (e.g. "nginx")
            interval_seconds: Seconds between health checks.
            enabled: Whether monitoring is active.

        Returns:
            The created target dict.
        """
        if target_type not in self.TARGET_TYPES:
            raise ValueError(
                f"Invalid target_type '{target_type}'. Must be one of: {', '.join(sorted(self.TARGET_TYPES))}"
            )

        target_id = str(uuid.uuid4())[:8]

        entry = {
            "id": target_id,
            "name": name,
            "type": target_type,
            "target": target,
            "interval_seconds": interval_seconds,
            "enabled": enabled,
            "last_check": None,
            "status": "unknown",
            "last_error": None,
        }

        self._targets[target_id] = entry
        self._save_targets()
        print(f"[HeartbeatMonitor] Added target '{name}' ({target_type}: {target})")
        return entry

    def remove_target(self, target_id: str) -> bool:
        """Remove a monitoring target by ID.

        Returns:
            True if the target was found and removed.
        """
        if target_id in self._targets:
            name = self._targets[target_id]["name"]
            del self._targets[target_id]
            self._save_targets()
            print(f"[HeartbeatMonitor] Removed target '{name}' (id={target_id})")
            return True
        return False

    def list_targets(self) -> List[dict]:
        """Return all monitoring targets."""
        return list(self._targets.values())

    def get_status(self, target_id: str) -> Optional[dict]:
        """Get the current status of a specific target.

        Args:
            target_id: Target identifier.

        Returns:
            Target dict with current status, or None if not found.
        """
        return self._targets.get(target_id)

    # ------------------------------------------------------------------
    # Monitor loop
    # ------------------------------------------------------------------

    async def run_loop(self):
        """Main monitoring loop. Checks targets at their configured intervals.

        Runs indefinitely until stop() is called. Each target is checked
        independently based on its own interval_seconds.
        """
        self._running = True
        print("[HeartbeatMonitor] Monitor loop started")

        while self._running:
            now = time.time()
            tasks = []

            for target in list(self._targets.values()):
                if not target["enabled"]:
                    continue

                last_check_ts = self._parse_check_time(target.get("last_check"))
                interval = target.get("interval_seconds", 60)

                if last_check_ts is None or (now - last_check_ts) >= interval:
                    tasks.append(self._check_target(target))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            await asyncio.sleep(5)

        print("[HeartbeatMonitor] Monitor loop stopped")

    async def start(self):
        """Start the monitor loop as a background task."""
        self._loop_task = asyncio.create_task(self.run_loop())
        return self._loop_task

    def stop(self):
        """Signal the monitor loop to stop."""
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    async def _check_target(self, target: dict):
        """Run a health check on a single target and update its state.

        Args:
            target: Target dict to check.
        """
        target_type = target["type"]
        old_status = target["status"]
        new_status = "unknown"
        error = None

        try:
            if target_type == "url":
                new_status, error = await self._check_url(target["target"])
            elif target_type == "tcp":
                new_status, error = await self._check_tcp(target["target"])
            elif target_type == "process":
                new_status, error = await self._check_process(target["target"])
        except Exception as e:
            new_status = "down"
            error = str(e)

        target["last_check"] = datetime.utcnow().isoformat()
        target["status"] = new_status
        target["last_error"] = error
        self._save_targets()

        if old_status != new_status and old_status != "unknown":
            print(f"[HeartbeatMonitor] '{target['name']}' status changed: {old_status} -> {new_status}")
            if self._on_status_change:
                try:
                    if asyncio.iscoroutinefunction(self._on_status_change):
                        await self._on_status_change(target, old_status, new_status)
                    else:
                        self._on_status_change(target, old_status, new_status)
                except Exception as e:
                    print(f"[HeartbeatMonitor] Status change callback error: {e}")

    async def _check_url(self, url: str, timeout: int = 10) -> tuple:
        """Check a URL for a 2xx HTTP response.

        Args:
            url: Full URL to check.
            timeout: Request timeout in seconds.

        Returns:
            Tuple of (status_string, error_or_none).
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if 200 <= resp.status < 300:
                        return "up", None
                    else:
                        return "down", f"HTTP {resp.status}"
        except aiohttp.ClientError as e:
            return "down", str(e)
        except asyncio.TimeoutError:
            return "down", "Connection timed out"

    async def _check_tcp(self, target: str, timeout: int = 5) -> tuple:
        """Check a TCP port for connectivity.

        Args:
            target: "host:port" string.
            timeout: Connection timeout in seconds.

        Returns:
            Tuple of (status_string, error_or_none).
        """
        try:
            host, port_str = target.rsplit(":", 1)
            port = int(port_str)
        except (ValueError, AttributeError):
            return "down", f"Invalid target format: '{target}' (expected host:port)"

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()
            return "up", None
        except asyncio.TimeoutError:
            return "down", f"Connection to {host}:{port} timed out"
        except ConnectionRefusedError:
            return "down", f"Connection refused on {host}:{port}"
        except OSError as e:
            return "down", str(e)

    async def _check_process(self, process_name: str) -> tuple:
        """Check if a process with the given name is running.

        Uses 'pgrep' on Unix systems for process detection.

        Args:
            process_name: Name of the process to search for.

        Returns:
            Tuple of (status_string, error_or_none).
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "pgrep", "-f", process_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0 and stdout.strip():
                return "up", None
            else:
                return "down", f"Process '{process_name}' not found"
        except FileNotFoundError:
            # pgrep not available, try /proc scan on Linux
            return await self._check_process_proc(process_name)

    async def _check_process_proc(self, process_name: str) -> tuple:
        """Fallback process check using /proc filesystem.

        Args:
            process_name: Name of the process to search for.

        Returns:
            Tuple of (status_string, error_or_none).
        """
        proc_dir = "/proc"
        if not os.path.isdir(proc_dir):
            return "unknown", "Cannot check processes (no pgrep, no /proc)"

        try:
            for entry in os.listdir(proc_dir):
                if not entry.isdigit():
                    continue
                cmdline_path = os.path.join(proc_dir, entry, "cmdline")
                try:
                    with open(cmdline_path, "r") as f:
                        cmdline = f.read()
                    if process_name in cmdline:
                        return "up", None
                except (OSError, PermissionError):
                    continue
            return "down", f"Process '{process_name}' not found"
        except Exception as e:
            return "unknown", str(e)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_targets(self):
        """Load targets from the JSON file."""
        if not os.path.exists(self._targets_file):
            self._targets = {}
            return

        try:
            with open(self._targets_file, "r") as f:
                target_list = json.load(f)
            self._targets = {t["id"]: t for t in target_list}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[HeartbeatMonitor] Error loading targets: {e}")
            self._targets = {}

    def _save_targets(self):
        """Persist current targets to the JSON file."""
        try:
            with open(self._targets_file, "w") as f:
                json.dump(list(self._targets.values()), f, indent=2)
        except Exception as e:
            print(f"[HeartbeatMonitor] Error saving targets: {e}")

    @staticmethod
    def _parse_check_time(iso_string: Optional[str]) -> Optional[float]:
        """Parse an ISO datetime string to a Unix timestamp.

        Args:
            iso_string: ISO format datetime string.

        Returns:
            Unix timestamp as float, or None.
        """
        if not iso_string:
            return None
        try:
            dt = datetime.fromisoformat(iso_string)
            return dt.timestamp()
        except (ValueError, TypeError):
            return None
