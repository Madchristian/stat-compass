"""Build the bilingual CHANGELOG.md from changelog/CHANGELOG-<version>-en.md and -de.md pairs.

The pairs are the source; CHANGELOG.md is generated and never edited by hand. Fail-closed: a
missing language, an empty or identical pair, a title that does not match its file name, or an
unexpected file in changelog/ stops the run without writing anything.

    python tools/generate_changelog.py                     # write CHANGELOG.md
    python tools/generate_changelog.py --check             # exit 1 if CHANGELOG.md is stale
    python tools/generate_changelog.py --check --require 2026.10.3   # the tagged version must exist
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "changelog"
OUTPUT = ROOT / "CHANGELOG.md"
VERSION = r"(\d{4})\.(\d{1,2})\.(\d{1,2})(?:-(\d+))?"
NOTE = re.compile(rf"CHANGELOG-({VERSION})-(en|de)\.md")
HEADINGS = {"en": "English", "de": "Deutsch"}
INTRO = """# Stat Compass: Changelog / Änderungsverlauf

This file contains the complete public release history. Every version is listed once, English first, then German.

Diese Datei enthält die vollständige öffentliche Release-Historie. Jede Version steht genau einmal, zuerst Englisch, danach Deutsch.
"""


def version_key(version):
    match = re.fullmatch(VERSION, version)
    return tuple(int(part or 1) for part in match.groups())


def load():
    notes = {}
    for path in sorted(SOURCE.iterdir()):
        match = NOTE.fullmatch(path.name)
        if not match:
            raise ValueError(f"unexpected file in changelog/: {path.name}")
        version, language = match.group(1), match.group(6)
        text = path.read_text(encoding="utf-8").strip()
        lines = text.splitlines()
        if not lines or lines[0] != f"# Stat Compass {version}":
            raise ValueError(f"{path.name}: first line must be '# Stat Compass {version}'")
        body = "\n".join(lines[1:]).strip()
        if not re.search(r"[A-Za-zÄÖÜäöüß]{3}", re.sub(r"^#+.*$", "", body, flags=re.M)):
            raise ValueError(f"{path.name}: no text besides headings")
        notes.setdefault(version, {})[language] = body
    for version, pair in notes.items():
        if set(pair) != set(HEADINGS):
            raise ValueError(f"{version}: needs both CHANGELOG-{version}-en.md and -de.md")
        if pair["en"] == pair["de"]:
            raise ValueError(f"{version}: English and German text are identical")
    return notes


def demote(body):
    # version headings are ##, language headings ###, so note headings move down two levels
    return re.sub(r"^(#+)", lambda m: "#" * min(6, len(m.group(1)) + 2), body, flags=re.M)


def render(notes):
    parts = [INTRO]
    for version in sorted(notes, key=version_key, reverse=True):
        parts.append(f"## {version}\n")
        for language, heading in HEADINGS.items():
            parts.append(f"### {heading}\n\n{demote(notes[version][language])}\n")
        parts.append("---\n")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--require", help="version that must have a changelog pair (the release tag)")
    args = parser.parse_args()
    notes = load()
    if args.require and args.require not in notes:
        sys.exit(f"no changelog pair for {args.require}: add changelog/CHANGELOG-{args.require}-en.md and -de.md")
    text = render(notes)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != text:
            sys.exit("CHANGELOG.md is out of date: run python tools/generate_changelog.py")
        return
    OUTPUT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.exit(f"changelog: {exc}")
