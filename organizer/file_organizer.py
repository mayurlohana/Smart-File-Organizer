"""FileOrganizer - Core engine that scans, classifies, and moves files."""

import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from organizer.classifier import FileClassifier
from organizer.history import FileHistory
from organizer.logger import FileLogger


class FileOrganizer:
    """Core class that orchestrates file scanning, classification, and organization.

    Brings together the FileClassifier, FileLogger, and FileHistory to provide
    a complete file organization workflow with undo support and error handling.

    Attributes:
        target_folder: The folder to organize.
        classifier: FileClassifier instance for categorizing files.
        logger: FileLogger instance for operation logging.
        history: FileHistory instance for undo support.
    """

    def __init__(
        self,
        target_folder: Optional[Path] = None,
        classifier: Optional[FileClassifier] = None,
        logger: Optional[FileLogger] = None,
        history: Optional[FileHistory] = None,
    ) -> None:
        """Initialize the FileOrganizer.

        Args:
            target_folder: The folder to organize. Can be set later.
            classifier: Custom FileClassifier. Uses defaults if None.
            logger: Custom FileLogger. Uses defaults if None.
            history: Custom FileHistory. Uses defaults if None.
        """
        self._target_folder = target_folder
        self._classifier = classifier or FileClassifier()
        self._logger = logger or FileLogger()
        self._history = history or FileHistory()
        self._is_running = False

    @property
    def target_folder(self) -> Optional[Path]:
        """Return the current target folder."""
        return self._target_folder

    @target_folder.setter
    def target_folder(self, folder: Path) -> None:
        """Set the target folder to organize."""
        self._target_folder = folder

    @property
    def classifier(self) -> FileClassifier:
        """Return the FileClassifier instance."""
        return self._classifier

    @property
    def logger(self) -> FileLogger:
        """Return the FileLogger instance."""
        return self._logger

    @property
    def history(self) -> FileHistory:
        """Return the FileHistory instance."""
        return self._history

    @property
    def is_running(self) -> bool:
        """Return whether an organization operation is in progress."""
        return self._is_running

    def scan_files(self, folder: Optional[Path] = None) -> List[Path]:
        """Scan and return all files (non-directories) in the target folder.

        Only scans the top level — does not recurse into subfolders.

        Args:
            folder: Folder to scan. Uses target_folder if not provided.

        Returns:
            List of Path objects for each file found.

        Raises:
            ValueError: If no folder is specified.
            FileNotFoundError: If the folder doesn't exist.
            PermissionError: If the folder can't be read.
        """
        folder = folder or self._target_folder
        if folder is None:
            raise ValueError("No target folder specified.")
        folder = Path(folder)

        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")
        if not folder.is_dir():
            raise NotADirectoryError(f"Not a directory: {folder}")

        try:
            files = [f for f in folder.iterdir() if f.is_file()]
        except PermissionError as e:
            self._logger.log_error(f"Permission denied scanning '{folder}'", e)
            raise

        self._logger.log_info(f"Scanned '{folder}' — found {len(files)} file(s)")
        return files

    def preview(self, folder: Optional[Path] = None) -> Dict[str, List[Path]]:
        """Preview how files would be organized without actually moving them.

        Args:
            folder: Folder to preview. Uses target_folder if not provided.

        Returns:
            Dict mapping category names to lists of file paths.
        """
        files = self.scan_files(folder)
        return self._classifier.classify_multiple(files)

    def _resolve_conflict(self, destination: Path) -> Path:
        """Generate a unique filename if the destination already exists.

        Appends a numeric suffix like `_1`, `_2`, etc.

        Args:
            destination: The intended destination path.

        Returns:
            A unique path that doesn't conflict with existing files.
        """
        if not destination.exists():
            return destination

        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent
        counter = 1

        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                self._logger.log_warning(
                    f"Name conflict: '{destination.name}' -> renamed to '{new_name}'"
                )
                return new_path
            counter += 1

    def organize(
        self,
        folder: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Tuple[int, int, int]:
        """Organize files in the target folder into categorized subfolders.

        Args:
            folder: Folder to organize. Uses target_folder if not provided.
            progress_callback: Optional callable(current, total, message) for progress updates.

        Returns:
            Tuple of (moved_count, skipped_count, error_count).

        Raises:
            ValueError: If no folder is specified.
            RuntimeError: If an organization is already in progress.
        """
        if self._is_running:
            raise RuntimeError("An organization operation is already in progress.")

        folder = Path(folder) if folder else self._target_folder
        if folder is None:
            raise ValueError("No target folder specified.")

        self._is_running = True
        moved = 0
        skipped = 0
        errors = 0

        try:
            files = self.scan_files(folder)
            total = len(files)

            if total == 0:
                self._logger.log_info("No files to organize.")
                if progress_callback:
                    progress_callback(0, 0, "No files found.")
                return (0, 0, 0)

            classified = self._classifier.classify_multiple(files)

            file_index = 0
            for category, file_list in classified.items():
                # Create destination subfolder
                dest_folder = folder / category
                try:
                    dest_folder.mkdir(exist_ok=True)
                except PermissionError as e:
                    self._logger.log_error(
                        f"Cannot create folder '{dest_folder}'", e
                    )
                    errors += len(file_list)
                    file_index += len(file_list)
                    continue

                for file_path in file_list:
                    if not self._is_running:
                        self._logger.log_info("Organization stopped by user.")
                        if progress_callback:
                            progress_callback(file_index, total, "Stopped by user.")
                        break

                    file_index += 1
                    destination = dest_folder / file_path.name
                    destination = self._resolve_conflict(destination)

                    try:
                        shutil.move(str(file_path), str(destination))
                        self._history.add_record(file_path, destination, category)
                        self._logger.log_move(file_path, destination)
                        moved += 1
                    except PermissionError as e:
                        self._logger.log_error(
                            f"Permission denied moving '{file_path}'", e
                        )
                        errors += 1
                    except FileNotFoundError as e:
                        self._logger.log_error(
                            f"File not found: '{file_path}'", e
                        )
                        errors += 1
                    except OSError as e:
                        self._logger.log_error(
                            f"OS error moving '{file_path}'", e
                        )
                        errors += 1

                    if progress_callback:
                        progress_callback(
                            file_index, total,
                            f"Moved: {file_path.name} -> {category}/"
                        )

                if not self._is_running:
                    break

        finally:
            self._is_running = False

        self._logger.log_summary(
            total_files=moved + skipped + errors,
            moved=moved,
            skipped=skipped,
            errors=errors,
        )
        return (moved, skipped, errors)

    def stop(self) -> None:
        """Signal the current organization operation to stop."""
        self._is_running = False
        self._logger.log_info("Stop signal received.")

    def undo_last(self) -> bool:
        """Undo the last file move operation.

        Returns:
            True if the undo was successful, False otherwise.
        """
        record = self._history.pop_last_record()
        if record is None:
            self._logger.log_info("Nothing to undo.")
            return False

        source = Path(record.destination)  # current location
        destination = Path(record.source)  # original location

        if not source.exists():
            self._logger.log_error(f"Cannot undo: file not found at '{source}'")
            return False

        try:
            shutil.move(str(source), str(destination))
            self._logger.log_undo(source, destination)

            # Clean up empty category folder
            category_folder = source.parent
            if category_folder.is_dir() and not any(category_folder.iterdir()):
                category_folder.rmdir()
                self._logger.log_info(f"Removed empty folder: '{category_folder}'")

            return True
        except (PermissionError, OSError) as e:
            self._logger.log_error(f"Failed to undo move", e)
            return False

    def undo_all(self) -> Tuple[int, int]:
        """Undo all recorded file moves.

        Returns:
            Tuple of (successful_undos, failed_undos).
        """
        records = self._history.pop_all_records()
        if not records:
            self._logger.log_info("No history to undo.")
            return (0, 0)

        success = 0
        failed = 0
        folders_to_check = set()

        for record in records:
            source = Path(record.destination)
            destination = Path(record.source)

            if not source.exists():
                self._logger.log_error(f"Cannot undo: '{source}' not found")
                failed += 1
                continue

            try:
                shutil.move(str(source), str(destination))
                self._logger.log_undo(source, destination)
                folders_to_check.add(source.parent)
                success += 1
            except (PermissionError, OSError) as e:
                self._logger.log_error(f"Failed to undo '{source}'", e)
                failed += 1

        # Clean up empty category folders
        for folder in folders_to_check:
            try:
                if folder.is_dir() and not any(folder.iterdir()):
                    folder.rmdir()
                    self._logger.log_info(f"Removed empty folder: '{folder}'")
            except OSError:
                pass

        self._logger.log_info(f"Undo complete: {success} restored, {failed} failed")
        return (success, failed)

    def __repr__(self) -> str:
        return (
            f"FileOrganizer(target='{self._target_folder}', "
            f"running={self._is_running})"
        )
