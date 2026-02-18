"""Background daemon mode for R.U.T.H. V3.

Generates platform-specific service files (systemd, launchd) and provides
methods to install, manage, and query the daemon status.
"""

import os
import socket
import sys
import subprocess
import textwrap
from pathlib import Path
from typing import Optional


class DaemonManager:
    """Manages R.U.T.H. V3 as a background system daemon.

    Generates service definitions for systemd (Linux) and launchd (macOS),
    and provides install/uninstall/status methods.

    Args:
        server_script: Absolute path to server.py.
        host: Bind address for the backend server.
        port: Port the backend server runs on.
        python_path: Path to the Python interpreter. Defaults to current.
    """

    SERVICE_NAME = "ruth-daemon"
    PLIST_LABEL = "tech.corebrim.ruth-daemon"

    def __init__(
        self,
        server_script: Optional[str] = None,
        host: str = "0.0.0.0",
        port: int = 8000,
        python_path: Optional[str] = None,
    ):
        self._server_script = server_script or self._default_server_script()
        self._host = host
        self._port = port
        self._python_path = python_path or sys.executable
        self._log_dir = os.path.expanduser("~/.ruth/logs")
        os.makedirs(self._log_dir, exist_ok=True)
        print("[DaemonManager] Initialized (port={})".format(port))

    # ------------------------------------------------------------------
    # Service file generation
    # ------------------------------------------------------------------

    def generate_service_file(self, platform: Optional[str] = None) -> str:
        """Generate platform-specific service file content.

        Args:
            platform: "linux" for systemd, "macos" for launchd.
                      Auto-detected if None.

        Returns:
            Service file content as a string.
        """
        if platform is None:
            platform = self._detect_platform()

        if platform == "linux":
            return self._generate_systemd_unit()
        elif platform == "macos":
            return self._generate_launchd_plist()
        else:
            return f"# Unsupported platform: {platform}\n# Manual setup required."

    def _generate_systemd_unit(self) -> str:
        """Generate a systemd service unit file."""
        working_dir = os.path.dirname(self._server_script)
        return textwrap.dedent(f"""\
            [Unit]
            Description=R.U.T.H. V3 Backend Daemon
            After=network.target

            [Service]
            Type=simple
            User={os.getenv("USER", "root")}
            WorkingDirectory={working_dir}
            ExecStart={self._python_path} {self._server_script}
            Restart=on-failure
            RestartSec=5
            StandardOutput=append:{self._log_dir}/ruth-daemon.log
            StandardError=append:{self._log_dir}/ruth-daemon.err
            Environment=RUTH_DAEMON=1

            [Install]
            WantedBy=multi-user.target
        """)

    def _generate_launchd_plist(self) -> str:
        """Generate a macOS LaunchAgent plist file."""
        return textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
              "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>{self.PLIST_LABEL}</string>
                <key>ProgramArguments</key>
                <array>
                    <string>{self._python_path}</string>
                    <string>{self._server_script}</string>
                </array>
                <key>WorkingDirectory</key>
                <string>{os.path.dirname(self._server_script)}</string>
                <key>RunAtLoad</key>
                <true/>
                <key>KeepAlive</key>
                <true/>
                <key>StandardOutPath</key>
                <string>{self._log_dir}/ruth-daemon.log</string>
                <key>StandardErrorPath</key>
                <string>{self._log_dir}/ruth-daemon.err</string>
                <key>EnvironmentVariables</key>
                <dict>
                    <key>RUTH_DAEMON</key>
                    <string>1</string>
                </dict>
            </dict>
            </plist>
        """)

    # ------------------------------------------------------------------
    # Install / Uninstall
    # ------------------------------------------------------------------

    def install_service(self) -> dict:
        """Install the daemon service for the current platform.

        Returns:
            Dict with status and any messages.
        """
        platform = self._detect_platform()

        if platform == "linux":
            return self._install_systemd()
        elif platform == "macos":
            return self._install_launchd()
        else:
            return {"success": False, "message": f"Unsupported platform: {platform}"}

    def uninstall_service(self) -> dict:
        """Uninstall the daemon service for the current platform.

        Returns:
            Dict with status and any messages.
        """
        platform = self._detect_platform()

        if platform == "linux":
            return self._uninstall_systemd()
        elif platform == "macos":
            return self._uninstall_launchd()
        else:
            return {"success": False, "message": f"Unsupported platform: {platform}"}

    def _install_systemd(self) -> dict:
        """Install the systemd service unit."""
        unit_path = Path(f"/etc/systemd/system/{self.SERVICE_NAME}.service")
        content = self._generate_systemd_unit()

        try:
            unit_path.write_text(content)
        except PermissionError:
            # Try user-level service instead
            user_unit_dir = Path.home() / ".config" / "systemd" / "user"
            user_unit_dir.mkdir(parents=True, exist_ok=True)
            unit_path = user_unit_dir / f"{self.SERVICE_NAME}.service"
            unit_path.write_text(content)

            self._run_cmd(["systemctl", "--user", "daemon-reload"])
            self._run_cmd(["systemctl", "--user", "enable", self.SERVICE_NAME])
            self._run_cmd(["systemctl", "--user", "start", self.SERVICE_NAME])

            return {
                "success": True,
                "message": f"Installed user service at {unit_path}",
                "path": str(unit_path),
            }

        self._run_cmd(["systemctl", "daemon-reload"])
        self._run_cmd(["systemctl", "enable", self.SERVICE_NAME])
        self._run_cmd(["systemctl", "start", self.SERVICE_NAME])

        return {
            "success": True,
            "message": f"Installed system service at {unit_path}",
            "path": str(unit_path),
        }

    def _uninstall_systemd(self) -> dict:
        """Remove the systemd service unit."""
        # Try system-level first
        system_path = Path(f"/etc/systemd/system/{self.SERVICE_NAME}.service")
        user_path = Path.home() / ".config" / "systemd" / "user" / f"{self.SERVICE_NAME}.service"

        if system_path.exists():
            self._run_cmd(["systemctl", "stop", self.SERVICE_NAME])
            self._run_cmd(["systemctl", "disable", self.SERVICE_NAME])
            try:
                system_path.unlink()
            except PermissionError:
                return {"success": False, "message": "Permission denied removing system service"}
            self._run_cmd(["systemctl", "daemon-reload"])
            return {"success": True, "message": "System service removed"}

        if user_path.exists():
            self._run_cmd(["systemctl", "--user", "stop", self.SERVICE_NAME])
            self._run_cmd(["systemctl", "--user", "disable", self.SERVICE_NAME])
            user_path.unlink()
            self._run_cmd(["systemctl", "--user", "daemon-reload"])
            return {"success": True, "message": "User service removed"}

        return {"success": False, "message": "Service file not found"}

    def _install_launchd(self) -> dict:
        """Install the macOS LaunchAgent plist."""
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_path = plist_dir / f"{self.PLIST_LABEL}.plist"

        content = self._generate_launchd_plist()
        plist_path.write_text(content)

        self._run_cmd(["launchctl", "load", str(plist_path)])

        return {
            "success": True,
            "message": f"Installed LaunchAgent at {plist_path}",
            "path": str(plist_path),
        }

    def _uninstall_launchd(self) -> dict:
        """Remove the macOS LaunchAgent plist."""
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{self.PLIST_LABEL}.plist"

        if not plist_path.exists():
            return {"success": False, "message": "Plist not found"}

        self._run_cmd(["launchctl", "unload", str(plist_path)])
        plist_path.unlink()

        return {"success": True, "message": "LaunchAgent removed"}

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        """Check if the backend is responding on the configured port.

        Uses a TCP connection test to determine if the server is alive.

        Returns:
            True if the server is accepting connections.
        """
        try:
            with socket.create_connection(("127.0.0.1", self._port), timeout=2):
                return True
        except (ConnectionRefusedError, OSError, socket.timeout):
            return False

    def get_status(self) -> dict:
        """Get detailed daemon status.

        Returns:
            Dict with running state, port, platform, and service info.
        """
        running = self.is_running()
        platform = self._detect_platform()

        status = {
            "running": running,
            "port": self._port,
            "host": self._host,
            "platform": platform,
            "python": self._python_path,
            "server_script": self._server_script,
            "log_dir": self._log_dir,
        }

        # Check service installation status
        if platform == "linux":
            system_path = Path(f"/etc/systemd/system/{self.SERVICE_NAME}.service")
            user_path = Path.home() / ".config" / "systemd" / "user" / f"{self.SERVICE_NAME}.service"
            status["service_installed"] = system_path.exists() or user_path.exists()
            status["service_type"] = "systemd"
        elif platform == "macos":
            plist_path = Path.home() / "Library" / "LaunchAgents" / f"{self.PLIST_LABEL}.plist"
            status["service_installed"] = plist_path.exists()
            status["service_type"] = "launchd"
        else:
            status["service_installed"] = False
            status["service_type"] = "none"

        return status

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_platform() -> str:
        """Detect the current platform category."""
        if sys.platform.startswith("linux"):
            return "linux"
        elif sys.platform == "darwin":
            return "macos"
        elif sys.platform == "win32":
            return "windows"
        return sys.platform

    @staticmethod
    def _default_server_script() -> str:
        """Return the default path to server.py relative to this file."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

    @staticmethod
    def _run_cmd(cmd: list) -> Optional[str]:
        """Run a system command, returning stdout or None on failure."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except Exception as e:
            print(f"[DaemonManager] Command failed ({' '.join(cmd)}): {e}")
            return None
