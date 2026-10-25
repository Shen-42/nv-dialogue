"""Check the CSVs written by export/fnvedit/NVDialogueExport.pas (card 2).

Usage:
    python ingest/check_export.py data/export
    python ingest/check_export.py data/export --sample 20

Exits with code 1 if any check fails, so card 3's loader can refuse to
load a broken export. Uses only the standard library.
"""

import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

HEADERS = {
    "lines.csv": [
        "info_form_id", "response_index", "topic_form_id", "topic_editor_id",
        "topic_text", "quest_form_id", "quest_editor_id", "speaker_form_id",
        "speaker_editor_id", "speaker_name", "speaker_conditions", "text",
        "source_file",
    ],
    "npcs.csv": ["form_id", "editor_id", "name", "record_type", "factions", "source_file"],
    "factions.csv": ["form_id", "editor_id", "name", "source_file"],
    "quests.csv": ["form_id", "editor_id", "name", "source_file"],
}

FORM_ID_LENGTH = 8


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    """Read a CSV that FNVEdit may have saved as UTF-8 or Windows-1252.

    Returns the header and the rows.
    """
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"{path.name}: not UTF-8 or Windows-1252")
    reader = csv.DictReader(text.splitlines())
    rows = list(reader)
    return list(reader.fieldnames or []), rows


def is_form_id(value: str) -> bool:
    if len(value) != FORM_ID_LENGTH:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "0.0%"


def check(export_dir: Path) -> tuple[list[str], list[str], dict]:
    """Return (errors, notes, tables). Errors fail the check; notes don't."""
    errors: list[str] = []
    notes: list[str] = []
    tables: dict[str, list[dict]] = {}

    for name, header in HEADERS.items():
        path = export_dir / name
        if not path.exists():
            errors.append(f"{name}: missing")
            continue
        try:
            found, rows = read_csv(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if found != header:
            errors.append(f"{name}: header is {found}, expected {header}")
            continue
        tables[name] = rows

    lines = tables.get("lines.csv")
    if lines is None:
        return errors, notes, tables
    if not lines:
        errors.append("lines.csv: no rows")
        return errors, notes, tables

    keys = Counter((r["info_form_id"], r["response_index"]) for r in lines)
    dupes = [k for k, n in keys.items() if n > 1]
    if dupes:
        errors.append(f"lines.csv: {len(dupes)} duplicate (info_form_id, response_index) pairs, e.g. {dupes[0]}")

    bad_ids = [r["info_form_id"] for r in lines if not is_form_id(r["info_form_id"])]
    if bad_ids:
        errors.append(f"lines.csv: {len(bad_ids)} rows with a bad info_form_id, e.g. {bad_ids[0]!r}")

    empty = sum(1 for r in lines if not r["text"].strip())
    if empty:
        errors.append(f"lines.csv: {empty} rows with empty text")

    total = len(lines)
    no_speaker = sum(1 for r in lines if not r["speaker_form_id"])
    no_speaker_no_cond = sum(
        1 for r in lines if not r["speaker_form_id"] and not r["speaker_conditions"]
    )
    no_quest = sum(1 for r in lines if not r["quest_form_id"])
    notes.append(f"lines: {total}")
    notes.append(f"lines with no named speaker: {no_speaker} ({pct(no_speaker, total)})")
    notes.append(
        f"lines with no speaker and no speaker condition: {no_speaker_no_cond} "
        f"({pct(no_speaker_no_cond, total)})"
    )
    notes.append(f"lines with no quest: {no_quest} ({pct(no_quest, total)})")
    if total and no_speaker / total > 0.6:
        notes.append("WARNING: over 60% of lines have no named speaker; check the speaker paths in ReadSpeaker")
    if total and no_quest / total > 0.2:
        notes.append("WARNING: over 20% of lines have no quest; check the QSTI paths in ExportInfo")

    actors = tables.get("npcs.csv")
    if actors is not None:
        known = {r["form_id"] for r in actors}
        unknown = {r["speaker_form_id"] for r in lines if r["speaker_form_id"]} - known
        notes.append(f"actors: {len(actors)}")
        if unknown:
            notes.append(f"speakers not in npcs.csv: {len(unknown)} (fine if they come from another plugin)")

    quests = tables.get("quests.csv")
    if quests is not None:
        known = {r["form_id"] for r in quests}
        unknown = {r["quest_form_id"] for r in lines if r["quest_form_id"]} - known
        notes.append(f"quests: {len(quests)}")
        if unknown:
            notes.append(f"quests not in quests.csv: {len(unknown)}")

    factions = tables.get("factions.csv")
    if factions is not None:
        notes.append(f"factions: {len(factions)}")

    top = Counter(r["quest_editor_id"] or "(no quest)" for r in lines).most_common(5)
    notes.append("top quests by lines: " + ", ".join(f"{q} {n}" for q, n in top))

    return errors, notes, tables


def sample(lines: list[dict], n: int, seed: int) -> list[dict]:
    """Pick n lines with a fixed seed, for the hand spot-check against the game."""
    rng = random.Random(seed)
    return rng.sample(lines, min(n, len(lines)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export_dir", nargs="?", default="data/export", type=Path)
    parser.add_argument("--sample", type=int, default=0, help="print N lines to spot-check")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    errors, notes, tables = check(args.export_dir)
    for note in notes:
        print(note)
    for error in errors:
        print(f"ERROR: {error}")

    if args.sample and "lines.csv" in tables:
        print(f"\nSpot-check sample ({args.sample} lines, seed {args.seed}):")
        for r in sample(tables["lines.csv"], args.sample, args.seed):
            speaker = r["speaker_name"] or r["speaker_editor_id"] or r["speaker_conditions"] or "?"
            print(f"- [{r['info_form_id']}] {speaker} / {r['quest_editor_id'] or '?'}: {r['text']}")

    print("\nFAILED" if errors else "\nOK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
