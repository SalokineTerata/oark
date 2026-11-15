import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("journal_ia", Path(__file__).resolve().parents[1] / "scripts" / "journal_ia.py")
journal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journal)


class JournalTests(unittest.TestCase):
    def test_rotation_preserves_entries_and_never_overwrites_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            journal.add_entry(directory, "premier", "A" * 8000)
            journal.add_entry(directory, "deuxième", "B" * 8000)
            self.assertIn("A" * 8000, (directory / "archives" / "journal-0001.md").read_text(encoding="utf-8"))
            self.assertIn("B" * 8000, (directory / "courant.md").read_text(encoding="utf-8"))
            journal.add_entry(directory, "troisième", "C" * 8000)
            self.assertIn("B" * 8000, (directory / "archives" / "journal-0002.md").read_text(encoding="utf-8"))
            self.assertLessEqual((directory / "courant.md").stat().st_size, journal.MAX_BYTES)

    def test_oversized_entry_fails_without_modifying_journal(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            journal.add_entry(directory, "valide", "contenu")
            before = (directory / "courant.md").read_bytes()
            with self.assertRaises(ValueError):
                journal.add_entry(directory, "trop long", "é" * journal.MAX_BYTES)
            self.assertEqual(before, (directory / "courant.md").read_bytes())

    def test_lock_prevents_concurrent_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / ".verrou").write_text("occupé", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                journal.add_entry(directory, "titre", "texte")
            self.assertFalse((directory / "courant.md").exists())

    def test_status_distinguishes_existing_unverified_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "exports").mkdir()
            (root / "exports" / "Livre-1_Audiobook.mp3").write_bytes(b"mp3")
            report = journal.status(root)
            self.assertIn("3 octets (non vérifié)", report)
            self.assertIn("audio absent", report)


if __name__ == "__main__":
    unittest.main()
