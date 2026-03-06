"""FileHistory - Tracks moved files to enable undo operations."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class MoveRecord:
    """A record of a single file move operation.

    Attributes:
        source: Original file path before move.
        destination: File path after move.
        timestamp: When the move occurred (ISO format string).
        category: The category/folder the file was moved into.
    """
    source: str
    destination: str
    timestamp: str
    category: str

    @classmethod
    def create(cls, source: Path, destination: Path, category: str) -> "MoveRecord":
        """Factory method to create a MoveRecord with the current timestamp.

        Args:
            source: Original file path.
            destination: Destination file path.
            category: Category the file was classified into.

        Returns:
            A new MoveRecord instance.
        """
        return cls(
            source=str(source),
            destination=str(destination),
            timestamp=datetime.now().isoformat(),
            category=category,
        )


class FileHistory:
    """Manages the history of moved files to support undo operations.

    The history is persisted to a JSON file so it survives across sessions.

    Attributes:
        history_file: Path to the JSON file where history is persisted.
    """

    def __init__(self, history_file: Optional[Path] = None) -> None:
        """Initialize file history.

        Args:
            history_file: Path to the history JSON file.
                          Defaults to '.organizer_history.json' in cwd.
        """
        self._history_file = history_file or Path.cwd() / ".organizer_history.json"
        self._records: List[MoveRecord] = []
        self._load()

    def _load(self) -> None:
        """Load history from the JSON file if it exists."""
        if self._history_file.exists():
            try:
                with open(self._history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._records = [MoveRecord(**entry) for entry in data]
            except (json.JSONDecodeError, KeyError, TypeError):
                self._records = []

    def _save(self) -> None:
        """Persist the current history to the JSON file."""
        with open(self._history_file, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self._records], f, indent=2)

    @property
    def history_file(self) -> Path:
        """Return the path to the history file."""
        return self._history_file

    @property
    def records(self) -> List[MoveRecord]:
        """Return a copy of all move records."""
        return list(self._records)

    @property
    def record_count(self) -> int:
        """Return the number of records in history."""
        return len(self._records)

    def add_record(self, source: Path, destination: Path, category: str) -> MoveRecord:
        """Add a new move record to the history.

        Args:
            source: Original file path.
            destination: Destination file path.
            category: Category name.

        Returns:
            The newly created MoveRecord.
        """
        record = MoveRecord.create(source, destination, category)
        self._records.append(record)
        self._save()
        return record

    def get_last_record(self) -> Optional[MoveRecord]:
        """Return the most recent move record, or None if history is empty."""
        return self._records[-1] if self._records else None

    def pop_last_record(self) -> Optional[MoveRecord]:
        """Remove and return the most recent move record.

        Returns:
            The most recent MoveRecord, or None if history is empty.
        """
        if not self._records:
            return None
        record = self._records.pop()
        self._save()
        return record

    def get_records_for_session(self, session_timestamp: str) -> List[MoveRecord]:
        """Get all records that share the same session (same minute).

        Args:
            session_timestamp: ISO timestamp to match against (matches to the minute).

        Returns:
            List of matching MoveRecords.
        """
        # Match records within the same minute (session approximation)
        prefix = session_timestamp[:16]  # 'YYYY-MM-DDTHH:MM'
        return [r for r in self._records if r.timestamp.startswith(prefix)]

    def pop_all_records(self) -> List[MoveRecord]:
        """Remove and return all records (for full undo).

        Returns:
            List of all MoveRecords in reverse chronological order.
        """
        records = list(reversed(self._records))
        self._records.clear()
        self._save()
        return records

    def clear(self) -> None:
        """Clear all history."""
        self._records.clear()
        self._save()

    def __repr__(self) -> str:
        return f"FileHistory(records={len(self._records)}, file='{self._history_file}')"
