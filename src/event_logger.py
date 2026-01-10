# src/event_logger.py

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any


class EventLogger:
    """
    Simple JSONL event logger for WordBuddy evaluation.
    One JSON object per line, append-only.
    """

    def __init__(self, log_path: str = "Log/events.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        trial_id: str,
        event: str,
        meta: Optional[Dict[str, Any]] = None,
        ts: Optional[float] = None,
    ):
        """
        Write one event to the JSONL log.

        Args:
            trial_id: e.g. "Test_1", "P01_T2"
            event: event name string
            meta: optional dictionary with extra info
            ts: optional timestamp (seconds). If None, time.time() is used.
        """
        record = {
            "ts": ts if ts is not None else time.time(),
            "trial_id": trial_id,
            "event": event,
            "meta": meta or {},
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
