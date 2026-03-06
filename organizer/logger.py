"""FileLogger - Handles logging of file move operations."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


class FileLogger:
    """Logs file organization operations to both console and a log file.

    Attributes:
        log_file: Path to the log file.
        logger: Python logging.Logger instance.
    """

    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, log_file: Optional[Path] = None, level: int = logging.INFO) -> None:
        """Initialize the logger.

        Args:
            log_file: Path to the log file. Defaults to 'organizer.log' in cwd.
            level: Logging level (default: INFO).
        """
        self._log_file = log_file or Path.cwd() / "organizer.log"
        self._logger = logging.getLogger("SmartFileOrganizer")
        self._logger.setLevel(level)

        # Avoid adding duplicate handlers on re-initialization
        if not self._logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Configure console and file handlers."""
        formatter = logging.Formatter(self.LOG_FORMAT, datefmt=self.DATE_FORMAT)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # File handler
        file_handler = logging.FileHandler(str(self._log_file), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

    @property
    def log_file(self) -> Path:
        """Return the path to the log file."""
        return self._log_file

    def log_move(self, source: Path, destination: Path) -> None:
        """Log a successful file move operation.

        Args:
            source: Original file path.
            destination: New file path after move.
        """
        timestamp = datetime.now().strftime(self.DATE_FORMAT)
        self._logger.info(
            "MOVED | '%s' -> '%s' | at %s", source, destination, timestamp
        )

    def log_undo(self, source: Path, destination: Path) -> None:
        """Log an undo (reverse move) operation.

        Args:
            source: The path the file is currently at (destination of original move).
            destination: The original path the file is being restored to.
        """
        self._logger.info("UNDO  | '%s' -> '%s'", source, destination)

    def log_error(self, message: str, exc: Optional[Exception] = None) -> None:
        """Log an error message.

        Args:
            message: Description of the error.
            exc: Optional exception object.
        """
        if exc:
            self._logger.error("%s | Exception: %s", message, exc)
        else:
            self._logger.error(message)

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        self._logger.warning(message)

    def log_info(self, message: str) -> None:
        """Log an informational message."""
        self._logger.info(message)

    def log_summary(self, total_files: int, moved: int, skipped: int, errors: int) -> None:
        """Log an operation summary.

        Args:
            total_files: Total number of files scanned.
            moved: Number of files successfully moved.
            skipped: Number of files skipped.
            errors: Number of errors encountered.
        """
        self._logger.info(
            "SUMMARY | Total: %d | Moved: %d | Skipped: %d | Errors: %d",
            total_files, moved, skipped, errors,
        )

    def __repr__(self) -> str:
        return f"FileLogger(log_file='{self._log_file}')"
