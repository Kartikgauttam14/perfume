"""Persistent mistake memory store for Mansam AI Concierge."""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from src.config import settings
from src.models import MistakeLogEntry

logger = logging.getLogger(__name__)


class MistakeStore:
    """Manages recording, persisting, and querying mistake logs and correction rules."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or settings.MISTAKES_PATH
        self._lock = threading.Lock()
        self._mistakes: List[MistakeLogEntry] = []
        self._load()

    def _load(self) -> None:
        """Loads logged mistakes from file if available."""
        if not self.file_path.exists():
            self._mistakes = []
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._mistakes = [MistakeLogEntry(**item) for item in data]
                logger.info("Loaded %d mistake records from %s", len(self._mistakes), self.file_path)
        except Exception as e:
            logger.warning("Could not load mistakes file (%s): %s", self.file_path, e)
            self._mistakes = []

    def _save(self) -> None:
        """Flushes in-memory mistakes to JSON storage."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                data = [m.model_dump() for m in self._mistakes]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to persist mistake records to %s: %s", self.file_path, e)

    def add_mistake(self, entry: MistakeLogEntry) -> None:
        """Appends a new mistake log entry and persists it."""
        with self._lock:
            if not entry.timestamp:
                entry.timestamp = datetime.utcnow().isoformat()
            self._mistakes.append(entry)
            self._save()
            logger.info("Recorded new mistake log: [%s] %s", entry.mistake_type, entry.correction_rule[:60])

    def get_all(self) -> List[MistakeLogEntry]:
        """Returns all recorded mistakes."""
        with self._lock:
            return list(self._mistakes)

    def get_active_correction_rules(self, limit: int = 5) -> List[str]:
        """Returns recent distinct correction rules for prompt injection."""
        with self._lock:
            seen = set()
            rules = []
            # iterate in reverse to get most recent
            for m in reversed(self._mistakes):
                rule = m.correction_rule.strip()
                if rule and rule not in seen:
                    seen.add(rule)
                    rules.append(rule)
                if len(rules) >= limit:
                    break
            return rules
