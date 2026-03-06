"""FileClassifier - Classifies files by their extension into categories."""

from pathlib import Path
from typing import Dict, List, Optional


class FileClassifier:
    """Classifies files into categories based on their file extension.

    Attributes:
        categories: A mapping of category names to lists of extensions.
    """

    # Default category definitions
    DEFAULT_CATEGORIES: Dict[str, List[str]] = {
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".tif"],
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
        "Video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tar.gz"],
        "Code": [".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".h", ".rb", ".go", ".rs", ".php", ".swift"],
        "Data": [".json", ".xml", ".yaml", ".yml", ".sql", ".db", ".sqlite"],
        "Executables": [".exe", ".msi", ".dmg", ".app", ".deb", ".rpm", ".sh", ".bat"],
        "Fonts": [".ttf", ".otf", ".woff", ".woff2", ".eot"],
    }

    def __init__(self, custom_categories: Optional[Dict[str, List[str]]] = None) -> None:
        """Initialize the classifier with default or custom categories.

        Args:
            custom_categories: Optional dict mapping category names to extension lists.
                               If provided, these are merged with (and override) defaults.
        """
        self._categories: Dict[str, List[str]] = dict(self.DEFAULT_CATEGORIES)
        if custom_categories:
            self._categories.update(custom_categories)

        # Build a reverse lookup: extension -> category
        self._extension_map: Dict[str, str] = {}
        self._rebuild_extension_map()

    def _rebuild_extension_map(self) -> None:
        """Rebuild the internal extension-to-category mapping."""
        self._extension_map.clear()
        for category, extensions in self._categories.items():
            for ext in extensions:
                self._extension_map[ext.lower()] = category

    @property
    def categories(self) -> Dict[str, List[str]]:
        """Return a copy of the current categories."""
        return dict(self._categories)

    def add_category(self, name: str, extensions: List[str]) -> None:
        """Add or update a category with the given extensions.

        Args:
            name: Category name (used as subfolder name).
            extensions: List of file extensions (e.g., ['.txt', '.md']).
        """
        self._categories[name] = [ext.lower() for ext in extensions]
        self._rebuild_extension_map()

    def remove_category(self, name: str) -> bool:
        """Remove a category by name.

        Args:
            name: The category name to remove.

        Returns:
            True if the category was removed, False if it didn't exist.
        """
        if name in self._categories:
            del self._categories[name]
            self._rebuild_extension_map()
            return True
        return False

    def classify(self, file_path: Path) -> str:
        """Classify a single file by its extension.

        Args:
            file_path: Path to the file.

        Returns:
            The category name, or 'Other' if no match is found.
        """
        ext = file_path.suffix.lower()
        return self._extension_map.get(ext, "Other")

    def classify_multiple(self, file_paths: List[Path]) -> Dict[str, List[Path]]:
        """Classify multiple files and group them by category.

        Args:
            file_paths: List of file paths to classify.

        Returns:
            Dict mapping category names to lists of file paths.
        """
        result: Dict[str, List[Path]] = {}
        for fp in file_paths:
            category = self.classify(fp)
            result.setdefault(category, []).append(fp)
        return result

    def get_category_for_extension(self, extension: str) -> str:
        """Look up which category an extension belongs to.

        Args:
            extension: File extension (e.g., '.pdf').

        Returns:
            Category name or 'Other'.
        """
        return self._extension_map.get(extension.lower(), "Other")

    def __repr__(self) -> str:
        return f"FileClassifier(categories={len(self._categories)})"
