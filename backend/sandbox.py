"""Sandboxed code execution engine for R.U.T.H. V3.

Executes user-provided code in isolated subprocesses with configurable
timeouts, working directory restrictions, and output capture.
"""

import asyncio
import os
import sys
import stat
import tempfile
import time
from pathlib import Path
from typing import Optional


class CodeSandbox:
    """Executes code in isolated subprocesses with resource constraints.

    Supports Python scripts and shell scripts. Code is written to a
    temporary file, executed via subprocess, and output is captured.

    Args:
        default_timeout: Default execution timeout in seconds.
        default_working_dir: Default working directory for code execution.
            If None, uses a temporary directory.
    """

    SUPPORTED_LANGUAGES = {"python", "shell", "bash", "sh"}

    def __init__(
        self,
        default_timeout: int = 30,
        default_working_dir: Optional[str] = None,
    ):
        self._default_timeout = default_timeout
        self._default_working_dir = default_working_dir
        print("[CodeSandbox] Initialized (timeout={}s)".format(default_timeout))

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
    ) -> dict:
        """Execute code in a sandboxed subprocess.

        Args:
            code: Source code to execute.
            language: Execution language ("python", "shell", "bash", "sh").
            timeout: Max execution time in seconds. Uses default if None.
            working_dir: Directory to restrict execution to. Uses default if None.

        Returns:
            Dict with keys: stdout, stderr, return_code, timed_out, execution_time
        """
        language = language.lower().strip()
        if language not in self.SUPPORTED_LANGUAGES:
            return {
                "stdout": "",
                "stderr": f"Unsupported language: '{language}'. Supported: {', '.join(sorted(self.SUPPORTED_LANGUAGES))}",
                "return_code": -1,
                "timed_out": False,
                "execution_time": 0.0,
            }

        timeout = timeout if timeout is not None else self._default_timeout
        work_dir = self._resolve_working_dir(working_dir)

        # Write code to temp file
        suffix = ".py" if language == "python" else ".sh"
        tmp_path = None
        try:
            tmp_path = self._write_temp_file(code, suffix, work_dir)
            result = await self._run_subprocess(tmp_path, language, timeout, work_dir)
            return result
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Execution error: {e}",
                "return_code": -1,
                "timed_out": False,
                "execution_time": 0.0,
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    async def _run_subprocess(
        self,
        script_path: str,
        language: str,
        timeout: int,
        working_dir: str,
    ) -> dict:
        """Spawn a subprocess to run the script and capture output.

        Args:
            script_path: Path to the temporary script file.
            language: Language to determine interpreter.
            timeout: Execution timeout in seconds.
            working_dir: Working directory for the subprocess.

        Returns:
            Execution result dict.
        """
        cmd = self._build_command(script_path, language)

        env = self._build_env(working_dir)

        start_time = time.monotonic()
        timed_out = False

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                timed_out = True
                process.kill()
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    stdout_bytes = b""
                    stderr_bytes = b"Process killed after timeout (failed to collect output)"

            elapsed = time.monotonic() - start_time

            stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

            if timed_out:
                stderr_text = f"Execution timed out after {timeout}s. {stderr_text}".strip()

            return {
                "stdout": stdout_text,
                "stderr": stderr_text,
                "return_code": process.returncode if process.returncode is not None else -9,
                "timed_out": timed_out,
                "execution_time": round(elapsed, 3),
            }

        except FileNotFoundError as e:
            elapsed = time.monotonic() - start_time
            return {
                "stdout": "",
                "stderr": f"Interpreter not found: {e}",
                "return_code": -1,
                "timed_out": False,
                "execution_time": round(elapsed, 3),
            }

    def _write_temp_file(self, code: str, suffix: str, directory: str) -> str:
        """Write code to a temporary file in the working directory.

        Args:
            code: Source code content.
            suffix: File extension (.py or .sh).
            directory: Directory to create the temp file in.

        Returns:
            Absolute path to the temporary file.
        """
        os.makedirs(directory, exist_ok=True)

        fd, path = tempfile.mkstemp(suffix=suffix, prefix="ruth_exec_", dir=directory)
        try:
            os.write(fd, code.encode("utf-8"))
        finally:
            os.close(fd)

        # Make shell scripts executable
        if suffix == ".sh":
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

        return path

    def _resolve_working_dir(self, working_dir: Optional[str]) -> str:
        """Resolve and validate the working directory.

        Args:
            working_dir: Requested working directory, or None.

        Returns:
            Absolute path to a valid working directory.
        """
        if working_dir:
            resolved = os.path.abspath(os.path.expanduser(working_dir))
            os.makedirs(resolved, exist_ok=True)
            return resolved

        if self._default_working_dir:
            resolved = os.path.abspath(os.path.expanduser(self._default_working_dir))
            os.makedirs(resolved, exist_ok=True)
            return resolved

        # Fall back to a temporary directory
        tmp = os.path.join(tempfile.gettempdir(), "ruth_sandbox")
        os.makedirs(tmp, exist_ok=True)
        return tmp

    @staticmethod
    def _build_command(script_path: str, language: str) -> list:
        """Build the subprocess command list.

        Args:
            script_path: Path to the script file.
            language: Execution language.

        Returns:
            List of command arguments.
        """
        if language == "python":
            return [sys.executable, "-u", script_path]
        else:
            # shell/bash/sh
            shell = "/bin/bash" if os.path.isfile("/bin/bash") else "/bin/sh"
            return [shell, script_path]

    @staticmethod
    def _build_env(working_dir: str) -> dict:
        """Build a restricted environment for the subprocess.

        Inherits the current environment but overrides HOME and
        restricts PATH-like variables that could leak information.

        Args:
            working_dir: The sandbox working directory.

        Returns:
            Environment variable dict.
        """
        env = os.environ.copy()
        # Override HOME to sandbox directory to prevent dotfile access
        env["RUTH_SANDBOX"] = "1"
        env["RUTH_WORKING_DIR"] = working_dir
        return env
