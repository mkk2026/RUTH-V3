"""PTY-based terminal session manager for R.U.T.H. V3.

Manages multiple terminal sessions, each backed by a pseudo-terminal.
Streams output via a configurable callback for real-time frontend delivery.

Socket.IO event mapping:
    terminal_create  -> create_session(session_id, shell)
    terminal_input   -> write_input(session_id, data)
    terminal_output  <- on_output(session_id, data)  [emitted to frontend]
    terminal_resize  -> resize_session(session_id, rows, cols)
    terminal_close   -> close_session(session_id)
"""

import asyncio
import os
import sys
import struct
import signal
import subprocess
from typing import Callable, Dict, List, Optional, Tuple

# PTY support is Linux/Mac only
_PTY_AVAILABLE = False
try:
    import pty
    import fcntl
    import termios
    _PTY_AVAILABLE = True
except ImportError:
    pass


class TerminalSession:
    """Represents a single PTY-backed terminal session."""

    def __init__(self, session_id: str, master_fd: int, pid: int, shell: str):
        self.session_id: str = session_id
        self.master_fd: int = master_fd
        self.pid: int = pid
        self.shell: str = shell
        self.rows: int = 24
        self.cols: int = 80
        self._reader_task: Optional[asyncio.Task] = None
        self._active: bool = True

    @property
    def active(self) -> bool:
        return self._active

    def mark_closed(self):
        self._active = False


class TerminalManager:
    """Manages multiple PTY terminal sessions with async output streaming.

    Args:
        on_output: Callback invoked as on_output(session_id, data) when a
                   terminal produces output. Designed for Socket.IO emission.
    """

    def __init__(self, on_output: Optional[Callable] = None):
        self._sessions: Dict[str, TerminalSession] = {}
        self._on_output: Optional[Callable] = on_output
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        print("[TerminalManager] Initialized (PTY available: {})".format(_PTY_AVAILABLE))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_session(
        self,
        session_id: str,
        shell: Optional[str] = None,
        rows: int = 24,
        cols: int = 80,
    ) -> dict:
        """Create a new terminal session.

        Args:
            session_id: Unique identifier for the session.
            shell: Shell executable path. Auto-detected if None.
            rows: Initial terminal rows.
            cols: Initial terminal columns.

        Returns:
            Dict with session metadata.
        """
        if session_id in self._sessions:
            return {"error": f"Session '{session_id}' already exists"}

        if not _PTY_AVAILABLE:
            return await self._create_session_fallback(session_id, shell)

        if shell is None:
            shell = self._detect_shell()

        self._loop = asyncio.get_running_loop()

        master_fd, slave_fd = pty.openpty()

        # Set initial terminal size
        self._set_winsize(master_fd, rows, cols)

        # Spawn child process attached to the PTY slave
        pid = os.fork()
        if pid == 0:
            # Child process
            os.close(master_fd)
            os.setsid()

            # Set the slave as the controlling terminal
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)

            # Redirect stdio to the PTY slave
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)

            if slave_fd > 2:
                os.close(slave_fd)

            env = os.environ.copy()
            env["TERM"] = "xterm-256color"

            os.execvpe(shell, [shell], env)
        else:
            # Parent process
            os.close(slave_fd)

            # Set master_fd to non-blocking
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            session = TerminalSession(
                session_id=session_id,
                master_fd=master_fd,
                pid=pid,
                shell=shell,
            )
            session.rows = rows
            session.cols = cols

            self._sessions[session_id] = session

            # Start background reader
            session._reader_task = asyncio.create_task(
                self._read_output_loop(session)
            )

            print(f"[TerminalManager] Session '{session_id}' created (pid={pid}, shell={shell})")
            return {
                "session_id": session_id,
                "pid": pid,
                "shell": shell,
                "rows": rows,
                "cols": cols,
            }

    async def write_input(self, session_id: str, data: str) -> bool:
        """Send input data to a terminal session.

        Args:
            session_id: Target session identifier.
            data: Raw input string (keystrokes) to write.

        Returns:
            True if written successfully, False otherwise.
        """
        session = self._sessions.get(session_id)
        if not session or not session.active:
            return False

        try:
            os.write(session.master_fd, data.encode("utf-8"))
            return True
        except OSError as e:
            print(f"[TerminalManager] Write error on '{session_id}': {e}")
            return False

    async def resize_session(self, session_id: str, rows: int, cols: int) -> bool:
        """Resize a terminal session.

        Args:
            session_id: Target session identifier.
            rows: New row count.
            cols: New column count.

        Returns:
            True if resized successfully.
        """
        session = self._sessions.get(session_id)
        if not session or not session.active:
            return False

        session.rows = rows
        session.cols = cols
        self._set_winsize(session.master_fd, rows, cols)

        # Notify the child process of the size change
        try:
            os.kill(session.pid, signal.SIGWINCH)
        except ProcessLookupError:
            pass

        return True

    async def close_session(self, session_id: str) -> bool:
        """Close and clean up a terminal session.

        Args:
            session_id: Session to close.

        Returns:
            True if closed, False if session not found.
        """
        session = self._sessions.pop(session_id, None)
        if not session:
            return False

        session.mark_closed()

        # Cancel the reader task
        if session._reader_task and not session._reader_task.done():
            session._reader_task.cancel()
            try:
                await session._reader_task
            except asyncio.CancelledError:
                pass

        # Terminate the child process
        try:
            os.kill(session.pid, signal.SIGTERM)
            # Give it a moment, then force kill
            await asyncio.sleep(0.5)
            try:
                os.kill(session.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass

        # Close the master fd
        try:
            os.close(session.master_fd)
        except OSError:
            pass

        # Reap zombie process
        try:
            os.waitpid(session.pid, os.WNOHANG)
        except ChildProcessError:
            pass

        print(f"[TerminalManager] Session '{session_id}' closed")
        return True

    def list_sessions(self) -> List[dict]:
        """Return metadata for all active sessions."""
        return [
            {
                "session_id": s.session_id,
                "pid": s.pid,
                "shell": s.shell,
                "rows": s.rows,
                "cols": s.cols,
                "active": s.active,
            }
            for s in self._sessions.values()
        ]

    async def shutdown(self):
        """Close all sessions and release resources. Call on server shutdown."""
        session_ids = list(self._sessions.keys())
        for sid in session_ids:
            await self.close_session(sid)
        print("[TerminalManager] All sessions closed")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _read_output_loop(self, session: TerminalSession):
        """Background task that reads PTY output and dispatches via callback."""
        loop = asyncio.get_running_loop()

        while session.active:
            try:
                data = await loop.run_in_executor(
                    None, self._blocking_read, session.master_fd
                )
                if data and self._on_output:
                    if asyncio.iscoroutinefunction(self._on_output):
                        await self._on_output(session.session_id, data)
                    else:
                        self._on_output(session.session_id, data)
            except OSError:
                # fd closed or child exited
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[TerminalManager] Read error on '{session.session_id}': {e}")
                break

        session.mark_closed()

    @staticmethod
    def _blocking_read(fd: int, size: int = 4096) -> str:
        """Blocking read from a file descriptor. Runs in executor."""
        import select
        readable, _, _ = select.select([fd], [], [], 0.1)
        if readable:
            raw = os.read(fd, size)
            if not raw:
                raise OSError("EOF on PTY")
            return raw.decode("utf-8", errors="replace")
        return ""

    @staticmethod
    def _set_winsize(fd: int, rows: int, cols: int):
        """Set the terminal window size on a file descriptor."""
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

    @staticmethod
    def _detect_shell() -> str:
        """Detect the appropriate shell for the current platform."""
        if sys.platform == "win32":
            return os.environ.get("COMSPEC", "cmd.exe")

        # Prefer user's shell, fall back to common defaults
        user_shell = os.environ.get("SHELL", "")
        if user_shell and os.path.isfile(user_shell):
            return user_shell

        for candidate in ["/bin/bash", "/bin/zsh", "/bin/sh"]:
            if os.path.isfile(candidate):
                return candidate

        return "/bin/sh"

    async def _create_session_fallback(self, session_id: str, shell: Optional[str]) -> dict:
        """Fallback session creation for Windows (no PTY, uses subprocess)."""
        if shell is None:
            shell = self._detect_shell()

        process = await asyncio.create_subprocess_exec(
            shell,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        print(f"[TerminalManager] Fallback session '{session_id}' created (pid={process.pid})")
        return {
            "session_id": session_id,
            "pid": process.pid,
            "shell": shell,
            "rows": 24,
            "cols": 80,
            "fallback": True,
        }
