"""Tests for check_export.py. The fixture text is invented, not game dialogue.

Run with: python -m unittest discover -s ingest/tests
(pytest also picks these up.)
"""

import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_export  # noqa: E402

LINE_ROWS = [
    ["0A000001", "1", "0B000001", "TopicGreet", "Hello", "0C000001", "QuestOne",
     "0D000001", "TestNpcA", "Test Npc A", "", "Welcome to the test town.", "Test.esm"],
    ["0A000001", "2", "0B000001", "TopicGreet", "Hello", "0C000001", "QuestOne",
     "0D000001", "TestNpcA", "Test Npc A", "", "We keep the \"water\" clean here.", "Test.esm"],
    ["0A000002", "1", "0B000002", "TopicTrade", "Trade", "", "",
     "", "", "", "GetInFaction TestFaction", "Caps first, then goods.", "Test.esm"],
]


def write_export(folder: Path, line_rows=None, encoding="utf-8", lines_header=None):
    tables = {
        "lines.csv": (lines_header or check_export.HEADERS["lines.csv"], line_rows if line_rows is not None else LINE_ROWS),
        "npcs.csv": (check_export.HEADERS["npcs.csv"], [["0D000001", "TestNpcA", "Test Npc A", "NPC_", "0E000001:0", "Test.esm"]]),
        "factions.csv": (check_export.HEADERS["factions.csv"], [["0E000001", "TestFaction", "Test Faction", "Test.esm"]]),
        "quests.csv": (check_export.HEADERS["quests.csv"], [["0C000001", "QuestOne", "Quest One", "Test.esm"]]),
    }
    for name, (header, rows) in tables.items():
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writerow(header)
        writer.writerows(rows)
        (folder / name).write_bytes(buf.getvalue().encode(encoding))


class CheckExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_export_passes(self):
        write_export(self.dir)
        errors, notes, tables = check_export.check(self.dir)
        self.assertEqual(errors, [])
        self.assertIn("lines: 3", notes)
        self.assertEqual(tables["lines.csv"][1]["text"], 'We keep the "water" clean here.')

    def test_counts_lines_without_speaker(self):
        write_export(self.dir)
        _, notes, _ = check_export.check(self.dir)
        self.assertIn("lines with no named speaker: 1 (33.3%)", notes)
        self.assertIn("lines with no speaker and no speaker condition: 0 (0.0%)", notes)

    def test_missing_file_fails(self):
        write_export(self.dir)
        (self.dir / "quests.csv").unlink()
        errors, _, _ = check_export.check(self.dir)
        self.assertIn("quests.csv: missing", errors)

    def test_wrong_header_fails(self):
        header = check_export.HEADERS["lines.csv"][:-1]
        write_export(self.dir, line_rows=[r[:-1] for r in LINE_ROWS], lines_header=header)
        errors, _, _ = check_export.check(self.dir)
        self.assertTrue(any(e.startswith("lines.csv: header") for e in errors))

    def test_duplicate_response_fails(self):
        write_export(self.dir, line_rows=LINE_ROWS + [LINE_ROWS[0]])
        errors, _, _ = check_export.check(self.dir)
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_bad_form_id_fails(self):
        bad = list(LINE_ROWS[2])
        bad[0] = "XYZ"
        write_export(self.dir, line_rows=LINE_ROWS[:2] + [bad])
        errors, _, _ = check_export.check(self.dir)
        self.assertTrue(any("bad info_form_id" in e for e in errors))

    def test_empty_text_fails(self):
        blank = list(LINE_ROWS[2])
        blank[11] = "   "
        write_export(self.dir, line_rows=LINE_ROWS[:2] + [blank])
        errors, _, _ = check_export.check(self.dir)
        self.assertTrue(any("empty text" in e for e in errors))

    def test_no_rows_fails(self):
        write_export(self.dir, line_rows=[])
        errors, _, _ = check_export.check(self.dir)
        self.assertIn("lines.csv: no rows", errors)

    def test_reads_windows_1252(self):
        accented = list(LINE_ROWS[2])
        accented[11] = "Order the café special."
        write_export(self.dir, line_rows=LINE_ROWS[:2] + [accented], encoding="cp1252")
        errors, _, tables = check_export.check(self.dir)
        self.assertEqual(errors, [])
        self.assertEqual(tables["lines.csv"][2]["text"], "Order the café special.")

    def test_sample_is_repeatable(self):
        write_export(self.dir)
        _, _, tables = check_export.check(self.dir)
        first = check_export.sample(tables["lines.csv"], 2, seed=7)
        second = check_export.sample(tables["lines.csv"], 2, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(len(check_export.sample(tables["lines.csv"], 99, seed=7)), 3)

    def test_main_exit_codes(self):
        write_export(self.dir)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(check_export.main([str(self.dir), "--sample", "2"]), 0)
        self.assertIn("Spot-check sample", out.getvalue())
        (self.dir / "npcs.csv").unlink()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(check_export.main([str(self.dir)]), 1)


if __name__ == "__main__":
    unittest.main()
