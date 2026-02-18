"""Proactive alerts system for R.U.T.H. V3.

Evaluates configurable alert rules against system context data and triggers
notifications, log entries, or webhook calls when conditions are met.
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


class AlertManager:
    """Manages alert rules and notifications with persistent storage.

    Rules are evaluated against context dicts provided by the caller
    (heartbeat monitor, scheduler, system metrics, etc.). When a rule
    fires, the configured action is executed.

    Args:
        storage_path: Directory for rule and notification persistence.
        log_path: Path for the alerts log file.
    """

    CONDITION_TYPES = {"threshold", "status_change", "schedule"}
    ACTION_TYPES = {"notify", "log", "webhook"}

    def __init__(
        self,
        storage_path: str = "~/.ruth/alerts",
        log_path: Optional[str] = None,
    ):
        self._storage_path = os.path.expanduser(storage_path)
        self._rules_file = os.path.join(self._storage_path, "rules.json")
        self._notifications_file = os.path.join(self._storage_path, "notifications.json")
        self._log_path = log_path or os.path.join(self._storage_path, "alerts.log")

        self._rules: Dict[str, dict] = {}
        self._notifications: List[dict] = []
        self._last_known_states: Dict[str, Any] = {}

        os.makedirs(self._storage_path, exist_ok=True)
        self._load_rules()
        self._load_notifications()
        print(f"[AlertManager] Initialized ({len(self._rules)} rules loaded)")

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(
        self,
        name: str,
        condition_type: str,
        condition_config: dict,
        action: str = "notify",
        action_config: Optional[dict] = None,
        enabled: bool = True,
    ) -> dict:
        """Add a new alert rule.

        Args:
            name: Human-readable rule name.
            condition_type: One of "threshold", "status_change", "schedule".
            condition_config: Configuration for the condition:
                - threshold: {"metric": str, "min": float|None, "max": float|None}
                - status_change: {"target_id": str, "from_status": str|None, "to_status": str|None}
                - schedule: {"cron": str}  (simple 5-field cron pattern)
            action: One of "notify", "log", "webhook".
            action_config: Configuration for the action:
                - notify: {"title": str, "message": str, "severity": "info"|"warning"|"critical"}
                - log: {"message": str}
                - webhook: {"url": str, "method": "POST"|"GET", "headers": dict}
            enabled: Whether the rule is active.

        Returns:
            The created rule dict.
        """
        if condition_type not in self.CONDITION_TYPES:
            raise ValueError(
                f"Invalid condition_type '{condition_type}'. "
                f"Must be one of: {', '.join(sorted(self.CONDITION_TYPES))}"
            )
        if action not in self.ACTION_TYPES:
            raise ValueError(
                f"Invalid action '{action}'. "
                f"Must be one of: {', '.join(sorted(self.ACTION_TYPES))}"
            )

        rule_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        rule = {
            "id": rule_id,
            "name": name,
            "condition_type": condition_type,
            "condition_config": condition_config,
            "action": action,
            "action_config": action_config or {},
            "enabled": enabled,
            "last_triggered": None,
            "created_at": now,
        }

        self._rules[rule_id] = rule
        self._save_rules()
        print(f"[AlertManager] Added rule '{name}' (id={rule_id}, condition={condition_type})")
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule by ID.

        Returns:
            True if the rule was found and removed.
        """
        if rule_id in self._rules:
            name = self._rules[rule_id]["name"]
            del self._rules[rule_id]
            self._save_rules()
            print(f"[AlertManager] Removed rule '{name}' (id={rule_id})")
            return True
        return False

    def list_rules(self) -> List[dict]:
        """Return all alert rules."""
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> Optional[dict]:
        """Get a single rule by ID."""
        return self._rules.get(rule_id)

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule["enabled"] = True
        self._save_rules()
        return True

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule["enabled"] = False
        self._save_rules()
        return True

    # ------------------------------------------------------------------
    # Rule evaluation
    # ------------------------------------------------------------------

    async def check_rules(self, context: dict) -> List[dict]:
        """Evaluate all enabled rules against the provided context.

        The context dict should contain relevant system state data. Keys
        depend on the condition types in use:

        - For threshold rules: context should have the metric key with a numeric value
        - For status_change rules: context should have target states
        - For schedule rules: evaluation uses current time

        Args:
            context: Dict of current system state data.

        Returns:
            List of triggered rule dicts (with action results appended).
        """
        triggered = []

        for rule in list(self._rules.values()):
            if not rule["enabled"]:
                continue

            try:
                fired = self._evaluate_condition(rule, context)
            except Exception as e:
                print(f"[AlertManager] Error evaluating rule '{rule['name']}': {e}")
                continue

            if fired:
                rule["last_triggered"] = datetime.utcnow().isoformat()
                self._save_rules()

                result = await self._execute_action(rule, context)
                triggered.append({**rule, "action_result": result})

        return triggered

    def _evaluate_condition(self, rule: dict, context: dict) -> bool:
        """Evaluate a single rule's condition against context.

        Args:
            rule: Rule dict with condition_type and condition_config.
            context: Current system state.

        Returns:
            True if the condition is met.
        """
        ctype = rule["condition_type"]
        config = rule["condition_config"]

        if ctype == "threshold":
            return self._check_threshold(config, context)
        elif ctype == "status_change":
            return self._check_status_change(config, context, rule["id"])
        elif ctype == "schedule":
            return self._check_schedule(config)

        return False

    def _check_threshold(self, config: dict, context: dict) -> bool:
        """Evaluate a threshold condition.

        Config keys:
            metric: Key to look up in context (supports dot notation: "cpu.usage")
            min: Minimum acceptable value (fires if value < min)
            max: Maximum acceptable value (fires if value > max)

        Args:
            config: Threshold condition configuration.
            context: Current context data.

        Returns:
            True if the threshold is breached.
        """
        metric_key = config.get("metric", "")
        value = self._resolve_dotted_key(context, metric_key)

        if value is None:
            return False

        try:
            value = float(value)
        except (ValueError, TypeError):
            return False

        min_val = config.get("min")
        max_val = config.get("max")

        if min_val is not None and value < float(min_val):
            return True
        if max_val is not None and value > float(max_val):
            return True

        return False

    def _check_status_change(self, config: dict, context: dict, rule_id: str) -> bool:
        """Evaluate a status change condition.

        Config keys:
            target_id: Key in context whose value is checked
            from_status: If set, only fires when changing FROM this status
            to_status: If set, only fires when changing TO this status

        Args:
            config: Status change condition configuration.
            context: Current context data.
            rule_id: Rule ID for tracking last known state.

        Returns:
            True if a matching status change occurred.
        """
        target_id = config.get("target_id", "")
        current_status = context.get(target_id)

        if current_status is None:
            return False

        state_key = f"{rule_id}:{target_id}"
        last_status = self._last_known_states.get(state_key)
        self._last_known_states[state_key] = current_status

        if last_status is None or last_status == current_status:
            return False

        from_status = config.get("from_status")
        to_status = config.get("to_status")

        if from_status and last_status != from_status:
            return False
        if to_status and current_status != to_status:
            return False

        return True

    def _check_schedule(self, config: dict) -> bool:
        """Evaluate a schedule condition against current time.

        Config keys:
            cron: 5-field cron pattern (minute hour dom month dow)

        Checks if the current minute matches the cron pattern.

        Args:
            config: Schedule condition configuration.

        Returns:
            True if current time matches the cron pattern.
        """
        cron = config.get("cron", "")
        parts = cron.strip().split()
        if len(parts) != 5:
            return False

        now = datetime.utcnow()

        try:
            return (
                self._cron_field_matches(parts[0], now.minute, 0, 59)
                and self._cron_field_matches(parts[1], now.hour, 0, 23)
                and self._cron_field_matches(parts[2], now.day, 1, 31)
                and self._cron_field_matches(parts[3], now.month, 1, 12)
                and self._cron_field_matches(parts[4], self._python_dow_to_cron(now.weekday()), 0, 6)
            )
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _cron_field_matches(field: str, value: int, min_val: int, max_val: int) -> bool:
        """Check if a value matches a cron field expression.

        Args:
            field: Cron field (e.g. "*", "5", "1,15", "*/10").
            value: Current value to check.
            min_val: Minimum valid value.
            max_val: Maximum valid value.

        Returns:
            True if the value matches the field.
        """
        if field == "*":
            return True

        if "/" in field:
            base, step = field.split("/", 1)
            step = int(step)
            start = min_val if base == "*" else int(base)
            return (value - start) % step == 0 and value >= start

        if "," in field:
            return value in {int(v) for v in field.split(",")}

        if "-" in field:
            start, end = field.split("-", 1)
            return int(start) <= value <= int(end)

        return value == int(field)

    @staticmethod
    def _python_dow_to_cron(weekday: int) -> int:
        """Convert Python weekday (Mon=0) to cron day (Sun=0)."""
        return (weekday + 1) % 7

    @staticmethod
    def _resolve_dotted_key(data: dict, key: str) -> Any:
        """Resolve a dot-notation key against a nested dict.

        Args:
            data: Dict to traverse.
            key: Dot-separated key path (e.g. "cpu.usage").

        Returns:
            The resolved value, or None if not found.
        """
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def _execute_action(self, rule: dict, context: dict) -> dict:
        """Execute the action defined by a triggered rule.

        Args:
            rule: The triggered rule dict.
            context: Current context data (included in notifications).

        Returns:
            Dict describing the action result.
        """
        action = rule["action"]
        config = rule.get("action_config", {})

        if action == "notify":
            return self._action_notify(rule, config, context)
        elif action == "log":
            return self._action_log(rule, config, context)
        elif action == "webhook":
            return await self._action_webhook(rule, config, context)

        return {"success": False, "error": f"Unknown action: {action}"}

    def _action_notify(self, rule: dict, config: dict, context: dict) -> dict:
        """Store a notification for frontend retrieval.

        Args:
            rule: Triggered rule.
            config: Action config with optional title, message, severity.
            context: Context data.

        Returns:
            Action result dict.
        """
        notification = {
            "id": str(uuid.uuid4())[:8],
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "title": config.get("title", rule["name"]),
            "message": config.get("message", f"Alert triggered: {rule['name']}"),
            "severity": config.get("severity", "info"),
            "timestamp": time.time(),
            "timestamp_iso": datetime.utcnow().isoformat(),
            "context_snapshot": {
                k: v for k, v in context.items()
                if isinstance(v, (str, int, float, bool, type(None)))
            },
            "acknowledged": False,
        }

        self._notifications.append(notification)
        self._save_notifications()

        print(f"[AlertManager] Notification: [{notification['severity'].upper()}] {notification['title']}")
        return {"success": True, "notification_id": notification["id"]}

    def _action_log(self, rule: dict, config: dict, context: dict) -> dict:
        """Write an entry to the alerts log file.

        Args:
            rule: Triggered rule.
            config: Action config with optional message.
            context: Context data.

        Returns:
            Action result dict.
        """
        message = config.get("message", f"Alert triggered: {rule['name']}")
        timestamp = datetime.utcnow().isoformat()
        log_line = f"[{timestamp}] [{rule['name']}] {message}\n"

        try:
            with open(self._log_path, "a") as f:
                f.write(log_line)
            return {"success": True, "log_path": self._log_path}
        except Exception as e:
            print(f"[AlertManager] Log write error: {e}")
            return {"success": False, "error": str(e)}

    async def _action_webhook(self, rule: dict, config: dict, context: dict) -> dict:
        """Send an HTTP request to a webhook URL.

        Args:
            rule: Triggered rule.
            config: Action config with url, method, headers.
            context: Context data (sent as JSON body for POST).

        Returns:
            Action result dict.
        """
        url = config.get("url")
        if not url:
            return {"success": False, "error": "No webhook URL configured"}

        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        headers.setdefault("Content-Type", "application/json")

        payload = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "triggered_at": datetime.utcnow().isoformat(),
            "context": {
                k: v for k, v in context.items()
                if isinstance(v, (str, int, float, bool, type(None)))
            },
        }

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                if method == "POST":
                    async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        return {"success": resp.status < 400, "status": resp.status}
                else:
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        return {"success": resp.status < 400, "status": resp.status}
        except Exception as e:
            print(f"[AlertManager] Webhook error: {e}")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Notifications retrieval
    # ------------------------------------------------------------------

    def add_notification(self, message: str, severity: str = "info", title: str = "") -> dict:
        """Add a notification directly (outside of rule evaluation).

        Args:
            message: The notification message.
            severity: Severity level (info, warning, error).
            title: Optional title. Defaults to the severity level.

        Returns:
            The created notification dict.
        """
        notification = {
            "id": str(uuid.uuid4())[:8],
            "rule_id": None,
            "rule_name": None,
            "title": title or severity.upper(),
            "message": message,
            "severity": severity,
            "timestamp": time.time(),
            "timestamp_iso": datetime.utcnow().isoformat(),
            "context_snapshot": {},
            "acknowledged": False,
        }
        self._notifications.append(notification)
        self._save_notifications()
        print(f"[AlertManager] Notification: [{severity.upper()}] {message}")
        return notification

    def get_notifications(self, since: Optional[float] = None, limit: int = 50) -> List[dict]:
        """Retrieve pending notifications, optionally filtered by timestamp.

        Args:
            since: Unix timestamp. Only return notifications after this time.
                   If None, returns the most recent notifications up to limit.
            limit: Maximum number of notifications to return.

        Returns:
            List of notification dicts, most recent first.
        """
        if since is not None:
            filtered = [n for n in self._notifications if n.get("timestamp", 0) > since]
        else:
            filtered = list(self._notifications)

        return sorted(filtered, key=lambda n: n.get("timestamp", 0), reverse=True)[:limit]

    def acknowledge_notification(self, notification_id: str) -> bool:
        """Mark a notification as acknowledged.

        Args:
            notification_id: ID of the notification to acknowledge.

        Returns:
            True if the notification was found and updated.
        """
        for notification in self._notifications:
            if notification["id"] == notification_id:
                notification["acknowledged"] = True
                self._save_notifications()
                return True
        return False

    def clear_notifications(self, before: Optional[float] = None):
        """Remove old notifications.

        Args:
            before: Unix timestamp. Remove notifications older than this.
                    If None, removes all notifications.
        """
        if before is None:
            self._notifications.clear()
        else:
            self._notifications = [
                n for n in self._notifications
                if n.get("timestamp", 0) >= before
            ]
        self._save_notifications()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_rules(self):
        """Load rules from the JSON file."""
        if not os.path.exists(self._rules_file):
            self._rules = {}
            return

        try:
            with open(self._rules_file, "r") as f:
                rule_list = json.load(f)
            self._rules = {r["id"]: r for r in rule_list}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[AlertManager] Error loading rules: {e}")
            self._rules = {}

    def _save_rules(self):
        """Persist current rules to the JSON file."""
        try:
            with open(self._rules_file, "w") as f:
                json.dump(list(self._rules.values()), f, indent=2)
        except Exception as e:
            print(f"[AlertManager] Error saving rules: {e}")

    def _load_notifications(self):
        """Load notifications from the JSON file."""
        if not os.path.exists(self._notifications_file):
            self._notifications = []
            return

        try:
            with open(self._notifications_file, "r") as f:
                self._notifications = json.load(f)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[AlertManager] Error loading notifications: {e}")
            self._notifications = []

    def _save_notifications(self):
        """Persist notifications to the JSON file."""
        try:
            with open(self._notifications_file, "w") as f:
                json.dump(self._notifications, f, indent=2)
        except Exception as e:
            print(f"[AlertManager] Error saving notifications: {e}")
