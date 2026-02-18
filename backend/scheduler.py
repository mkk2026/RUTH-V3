"""Task scheduler for R.U.T.H. V3.

Stores scheduled tasks in a JSON file and executes them on a configurable
schedule using pure asyncio (no external scheduler dependencies). Supports
one-shot, interval, and cron-style scheduling.
"""

import asyncio
import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class TaskScheduler:
    """Asyncio-based task scheduler with persistent task storage.

    Tasks are persisted to ~/.ruth/scheduler/tasks.json. The scheduler
    runs a background loop that checks for due tasks every 30 seconds.

    Args:
        storage_path: Directory for task persistence.
        on_task_execute: Async callback invoked when a task fires.
            Signature: on_task_execute(task: dict) -> Any
        check_interval: Seconds between schedule checks.
    """

    def __init__(
        self,
        storage_path: str = "~/.ruth/scheduler",
        on_task_execute: Optional[Callable] = None,
        check_interval: int = 30,
    ):
        self._storage_path = os.path.expanduser(storage_path)
        self._tasks_file = os.path.join(self._storage_path, "tasks.json")
        self._on_task_execute = on_task_execute
        self._check_interval = check_interval
        self._tasks: Dict[str, dict] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

        os.makedirs(self._storage_path, exist_ok=True)
        self._load_tasks()
        print(f"[TaskScheduler] Initialized ({len(self._tasks)} tasks loaded)")

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    def add_task(
        self,
        name: str,
        description: str = "",
        schedule_type: str = "once",
        schedule_value: str = "",
        tool_name: str = "",
        tool_args: Optional[dict] = None,
        enabled: bool = True,
    ) -> dict:
        """Add a new scheduled task.

        Args:
            name: Human-readable task name.
            description: What this task does.
            schedule_type: "once", "interval", or "cron".
            schedule_value: Depends on type:
                - once: ISO datetime string (e.g. "2026-03-01T08:00:00")
                - interval: seconds as string (e.g. "3600" for hourly)
                - cron: cron pattern (e.g. "0 8 * * *")
            tool_name: Name of the tool/action to invoke.
            tool_args: Arguments to pass to the tool.
            enabled: Whether the task is active.

        Returns:
            The created task dict.
        """
        task_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        task = {
            "id": task_id,
            "name": name,
            "description": description,
            "schedule_type": schedule_type,
            "schedule_value": schedule_value,
            "tool_name": tool_name,
            "tool_args": tool_args or {},
            "enabled": enabled,
            "last_run": None,
            "next_run": self._calculate_next_run(schedule_type, schedule_value),
            "created_at": now,
        }

        self._tasks[task_id] = task
        self._save_tasks()
        print(f"[TaskScheduler] Added task '{name}' (id={task_id}, type={schedule_type})")
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID.

        Returns:
            True if the task was found and removed.
        """
        if task_id in self._tasks:
            name = self._tasks[task_id]["name"]
            del self._tasks[task_id]
            self._save_tasks()
            print(f"[TaskScheduler] Removed task '{name}' (id={task_id})")
            return True
        return False

    def list_tasks(self) -> List[dict]:
        """Return all tasks as a list of dicts."""
        return list(self._tasks.values())

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a single task by ID."""
        return self._tasks.get(task_id)

    def enable_task(self, task_id: str) -> bool:
        """Enable a task. Recalculates next_run.

        Returns:
            True if the task was found and enabled.
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        task["enabled"] = True
        task["next_run"] = self._calculate_next_run(task["schedule_type"], task["schedule_value"])
        self._save_tasks()
        return True

    def disable_task(self, task_id: str) -> bool:
        """Disable a task.

        Returns:
            True if the task was found and disabled.
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        task["enabled"] = False
        self._save_tasks()
        return True

    # ------------------------------------------------------------------
    # Scheduler loop
    # ------------------------------------------------------------------

    async def run_loop(self):
        """Main scheduler loop. Checks for due tasks every check_interval seconds.

        Runs indefinitely until stop() is called. Designed to be launched
        as an asyncio.Task from the server startup.
        """
        self._running = True
        print(f"[TaskScheduler] Scheduler loop started (interval={self._check_interval}s)")

        while self._running:
            try:
                await self._check_and_execute_due_tasks()
            except Exception as e:
                print(f"[TaskScheduler] Loop error: {e}")

            await asyncio.sleep(self._check_interval)

        print("[TaskScheduler] Scheduler loop stopped")

    def stop(self):
        """Signal the scheduler loop to stop."""
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()

    async def start(self):
        """Start the scheduler loop as a background task."""
        self._loop_task = asyncio.create_task(self.run_loop())
        return self._loop_task

    async def _check_and_execute_due_tasks(self):
        """Check all enabled tasks and execute any that are due."""
        now = datetime.utcnow().isoformat()

        for task in list(self._tasks.values()):
            if not task["enabled"]:
                continue

            next_run = task.get("next_run")
            if not next_run:
                continue

            if now >= next_run:
                await self._execute_task(task)

    async def _execute_task(self, task: dict):
        """Execute a single task and update its state.

        Args:
            task: Task dict to execute.
        """
        task_id = task["id"]
        print(f"[TaskScheduler] Executing task '{task['name']}' (id={task_id})")

        now = datetime.utcnow().isoformat()
        task["last_run"] = now

        # Calculate next run based on schedule type
        if task["schedule_type"] == "once":
            task["enabled"] = False
            task["next_run"] = None
        else:
            task["next_run"] = self._calculate_next_run(
                task["schedule_type"], task["schedule_value"]
            )

        self._save_tasks()

        # Invoke the callback
        if self._on_task_execute:
            try:
                if asyncio.iscoroutinefunction(self._on_task_execute):
                    await self._on_task_execute(task)
                else:
                    self._on_task_execute(task)
            except Exception as e:
                print(f"[TaskScheduler] Task '{task['name']}' execution error: {e}")

    # ------------------------------------------------------------------
    # Schedule calculation
    # ------------------------------------------------------------------

    def _calculate_next_run(self, schedule_type: str, schedule_value: str) -> Optional[str]:
        """Calculate the next run time for a task.

        Args:
            schedule_type: "once", "interval", or "cron".
            schedule_value: Value appropriate for the schedule type.

        Returns:
            ISO datetime string of next run, or None if not schedulable.
        """
        now = datetime.utcnow()

        if schedule_type == "once":
            return schedule_value if schedule_value else None

        elif schedule_type == "interval":
            try:
                seconds = int(schedule_value)
                return (now + timedelta(seconds=seconds)).isoformat()
            except (ValueError, TypeError):
                print(f"[TaskScheduler] Invalid interval value: {schedule_value}")
                return None

        elif schedule_type == "cron":
            return self._next_cron_run(schedule_value, now)

        return None

    def _next_cron_run(self, pattern: str, after: datetime) -> Optional[str]:
        """Calculate the next datetime matching a simple cron pattern.

        Supports standard 5-field cron: minute hour day_of_month month day_of_week.
        Fields support: exact values, '*' (any), and comma-separated values.

        Args:
            pattern: Cron expression (e.g. "0 8 * * *" for daily at 8am).
            after: Calculate next run after this datetime.

        Returns:
            ISO datetime string or None if pattern is invalid.
        """
        parts = pattern.strip().split()
        if len(parts) != 5:
            print(f"[TaskScheduler] Invalid cron pattern (expected 5 fields): {pattern}")
            return None

        try:
            minute_spec = self._parse_cron_field(parts[0], 0, 59)
            hour_spec = self._parse_cron_field(parts[1], 0, 23)
            dom_spec = self._parse_cron_field(parts[2], 1, 31)
            month_spec = self._parse_cron_field(parts[3], 1, 12)
            dow_spec = self._parse_cron_field(parts[4], 0, 6)
        except ValueError as e:
            print(f"[TaskScheduler] Cron parse error: {e}")
            return None

        # Search forward from the next minute, up to 366 days
        candidate = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
        limit = after + timedelta(days=366)

        while candidate < limit:
            if (
                candidate.minute in minute_spec
                and candidate.hour in hour_spec
                and candidate.day in dom_spec
                and candidate.month in month_spec
                and candidate.weekday() in self._convert_dow(dow_spec)
            ):
                return candidate.isoformat()

            candidate += timedelta(minutes=1)

            # Skip ahead if hour doesn't match (optimization)
            if candidate.minute == 0 and candidate.hour not in hour_spec:
                next_valid_hour = None
                for h in sorted(hour_spec):
                    if h > candidate.hour:
                        next_valid_hour = h
                        break
                if next_valid_hour is not None:
                    candidate = candidate.replace(hour=next_valid_hour, minute=0)
                else:
                    candidate = (candidate + timedelta(days=1)).replace(hour=min(hour_spec), minute=0)

        return None

    @staticmethod
    def _parse_cron_field(field: str, min_val: int, max_val: int) -> set:
        """Parse a single cron field into a set of valid integer values.

        Args:
            field: Cron field string (e.g. "*", "5", "1,15", "*/10").
            min_val: Minimum valid value for this field.
            max_val: Maximum valid value for this field.

        Returns:
            Set of matching integer values.
        """
        if field == "*":
            return set(range(min_val, max_val + 1))

        # Handle step values: */5, 1-30/5
        if "/" in field:
            base, step = field.split("/", 1)
            step = int(step)
            if base == "*":
                return set(range(min_val, max_val + 1, step))
            if "-" in base:
                start, end = base.split("-", 1)
                return set(range(int(start), int(end) + 1, step))
            return set(range(int(base), max_val + 1, step))

        # Handle ranges: 1-5
        if "-" in field:
            start, end = field.split("-", 1)
            return set(range(int(start), int(end) + 1))

        # Handle comma-separated: 1,5,10
        if "," in field:
            return {int(v) for v in field.split(",")}

        # Single value
        return {int(field)}

    @staticmethod
    def _convert_dow(cron_dow: set) -> set:
        """Convert cron day-of-week (0=Sun) to Python weekday (0=Mon).

        Args:
            cron_dow: Set of cron day-of-week values.

        Returns:
            Set of Python weekday values (Monday=0).
        """
        # cron: 0=Sunday, 1=Monday, ..., 6=Saturday
        # Python: 0=Monday, 1=Tuesday, ..., 6=Sunday
        mapping = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
        return {mapping.get(d, d) for d in cron_dow}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_tasks(self):
        """Load tasks from the JSON file."""
        if not os.path.exists(self._tasks_file):
            self._tasks = {}
            return

        try:
            with open(self._tasks_file, "r") as f:
                task_list = json.load(f)
            self._tasks = {t["id"]: t for t in task_list}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[TaskScheduler] Error loading tasks: {e}")
            self._tasks = {}

    def _save_tasks(self):
        """Persist current tasks to the JSON file."""
        try:
            with open(self._tasks_file, "w") as f:
                json.dump(list(self._tasks.values()), f, indent=2)
        except Exception as e:
            print(f"[TaskScheduler] Error saving tasks: {e}")
