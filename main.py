#!/usr/bin/env python3
"""Smart File Organizer — Main entry point.

Supports two modes:
  1. GUI mode (default):   python main.py
  2. CLI mode:             python main.py --cli [folder_path]
"""

import argparse
import sys
from pathlib import Path

from organizer.file_organizer import FileOrganizer
from organizer.gui import OrganizerGUI


def cli_menu(organizer: FileOrganizer) -> None:
    """Run the interactive command-line menu.

    Args:
        organizer: A FileOrganizer instance.
    """
    print("\n" + "=" * 50)
    print("  Smart File Organizer — CLI Mode")
    print("=" * 50)

    while True:
        print("\n--- Menu ---")
        print("1. Select folder to organize")
        print("2. Preview classification")
        print("3. Organize files")
        print("4. Undo last move")
        print("5. Undo all moves")
        print("6. View history")
        print("7. Exit")
        print()

        choice = input("Enter choice (1-7): ").strip()

        if choice == "1":
            folder = input("Enter folder path: ").strip()
            path = Path(folder).expanduser().resolve()
            if not path.is_dir():
                print(f"  ERROR: '{path}' is not a valid directory.")
                continue
            organizer.target_folder = path
            print(f"  Selected: {path}")

        elif choice == "2":
            if organizer.target_folder is None:
                print("  Please select a folder first (option 1).")
                continue
            try:
                classified = organizer.preview()
                print(f"\n  Preview for: {organizer.target_folder}")
                print("  " + "-" * 40)
                total = 0
                for category, files in sorted(classified.items()):
                    print(f"  📁 {category} ({len(files)} files)")
                    for f in sorted(files, key=lambda p: p.name.lower()):
                        print(f"      📄 {f.name}")
                    total += len(files)
                print(f"\n  Total: {total} file(s)")
            except Exception as e:
                print(f"  ERROR: {e}")

        elif choice == "3":
            if organizer.target_folder is None:
                print("  Please select a folder first (option 1).")
                continue
            confirm = input(f"  Organize '{organizer.target_folder}'? (y/n): ").strip().lower()
            if confirm != "y":
                print("  Cancelled.")
                continue
            try:
                moved, skipped, errors = organizer.organize()
                print(f"\n  Done — Moved: {moved} | Skipped: {skipped} | Errors: {errors}")
            except Exception as e:
                print(f"  ERROR: {e}")

        elif choice == "4":
            success = organizer.undo_last()
            if success:
                print("  Last move undone successfully.")
            else:
                print("  Nothing to undo or undo failed.")

        elif choice == "5":
            confirm = input("  Undo ALL moves? (y/n): ").strip().lower()
            if confirm != "y":
                print("  Cancelled.")
                continue
            restored, failed = organizer.undo_all()
            print(f"  Undo All — Restored: {restored} | Failed: {failed}")

        elif choice == "6":
            records = organizer.history.records
            if not records:
                print("  No history.")
            else:
                print(f"\n  Move History ({len(records)} records):")
                print("  " + "-" * 60)
                for i, r in enumerate(records, 1):
                    print(f"  {i}. [{r.timestamp}] {r.category}")
                    print(f"     {r.source}")
                    print(f"     -> {r.destination}")

        elif choice == "7":
            print("  Goodbye!")
            break

        else:
            print("  Invalid choice. Please enter 1-7.")


def main() -> None:
    """Parse arguments and launch the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Smart File Organizer — Automatically sort files into subfolders."
    )
    parser.add_argument(
        "--cli", action="store_true",
        help="Run in command-line mode instead of GUI."
    )
    parser.add_argument(
        "folder", nargs="?", default=None,
        help="Optional: path to the folder to organize."
    )
    args = parser.parse_args()

    organizer = FileOrganizer()

    if args.folder:
        path = Path(args.folder).expanduser().resolve()
        if path.is_dir():
            organizer.target_folder = path
        else:
            print(f"Warning: '{args.folder}' is not a valid directory.", file=sys.stderr)

    if args.cli:
        cli_menu(organizer)
    else:
        gui = OrganizerGUI(organizer)
        gui.run()


if __name__ == "__main__":
    main()
