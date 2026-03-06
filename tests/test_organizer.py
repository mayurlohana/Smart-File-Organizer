"""Test script for Smart File Organizer components."""

from pathlib import Path
import tempfile
import os

from organizer.classifier import FileClassifier
from organizer.logger import FileLogger
from organizer.history import FileHistory
from organizer.file_organizer import FileOrganizer


def test_classifier():
    c = FileClassifier()
    print("Classifier:", c)
    print("  .jpg =>", c.classify(Path("photo.jpg")))
    print("  .pdf =>", c.classify(Path("doc.pdf")))
    print("  .xyz =>", c.classify(Path("data.xyz")))
    assert c.classify(Path("photo.jpg")) == "Images"
    assert c.classify(Path("doc.pdf")) == "Documents"
    assert c.classify(Path("data.xyz")) == "Other"
    print("  PASS: classifier\n")


def test_history():
    h = FileHistory(Path(tempfile.mktemp(suffix=".json")))
    h.add_record(Path("/a/b.txt"), Path("/a/Documents/b.txt"), "Documents")
    h.add_record(Path("/a/c.jpg"), Path("/a/Images/c.jpg"), "Images")
    print("History:", h)
    assert h.record_count == 2
    rec = h.pop_last_record()
    print("  Popped:", rec)
    assert rec.category == "Images"
    assert h.record_count == 1
    h.clear()
    os.unlink(h.history_file)
    print("  PASS: history\n")


def test_organize_and_undo():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # Create test files
        for name in ["photo.jpg", "report.pdf", "song.mp3", "script.py", "mystery.xyz"]:
            (td / name).touch()

        org = FileOrganizer(target_folder=td)
        files = org.scan_files()
        print(f"Scanned {len(files)} files")
        assert len(files) == 5

        preview = org.preview()
        for cat, fs in sorted(preview.items()):
            print(f"  {cat}: {[f.name for f in fs]}")

        # Organize
        moved, skipped, errors = org.organize()
        print(f"Organize result: moved={moved}, skipped={skipped}, errors={errors}")
        assert moved == 5
        assert errors == 0

        # Check result
        for item in sorted(td.iterdir()):
            if item.is_dir():
                contents = [f.name for f in item.iterdir()]
                print(f"  {item.name}/: {contents}")

        # Undo all
        restored, failed = org.undo_all()
        print(f"Undo: restored={restored}, failed={failed}")
        assert restored == 5
        assert failed == 0

        # Verify undo
        remaining = [f.name for f in td.iterdir() if f.is_file()]
        print(f"Files after undo: {sorted(remaining)}")
        assert len(remaining) == 5
        print("  PASS: organize & undo\n")


def test_conflict_handling():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # Create a file and a pre-existing destination with same name
        (td / "photo.jpg").write_text("original")
        images_dir = td / "Images"
        images_dir.mkdir()
        (images_dir / "photo.jpg").write_text("existing")

        org = FileOrganizer(target_folder=td)
        moved, _, errors = org.organize()
        print(f"Conflict test: moved={moved}, errors={errors}")
        assert moved == 1
        assert (images_dir / "photo_1.jpg").exists()
        print("  PASS: conflict handling\n")


if __name__ == "__main__":
    test_classifier()
    test_history()
    test_organize_and_undo()
    test_conflict_handling()
    print("=" * 40)
    print("ALL TESTS PASSED!")
