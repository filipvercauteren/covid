"""Zip the Streamlit app's source code + the presentation PDF (no data, no dependencies).

Usage:  python make_source_zip.py [output.zip]

Included: *.py, requirements.txt, markdown docs, and the presentation PDF.
Excluded: data (csv/parquet/db/json/xlsx), notebooks, caches, virtualenvs, .git, .claude.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "covid-resilience-source.zip"

SOURCE_SUFFIXES = {".py", ".md"}
SOURCE_NAMES = {"requirements.txt", ".gitignore"}
PRESENTATION_PDF = "COVID Resilience (NL, kort).pdf"  # default output of build_deck.py
EXCLUDED_DIRS = {
    ".git", ".claude", ".venv", "venv", "__pycache__", ".mypy_cache",
    ".ipynb_checkpoints", "app-data", "node_modules",
}


def is_wanted(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
        return False
    return (
        path.name == PRESENTATION_PDF
        or path.name in SOURCE_NAMES
        or path.suffix in SOURCE_SUFFIXES
    )


def collect_files(output: Path) -> list[Path]:
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and p != output and is_wanted(p))


def write_zip(output: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT))


def main(argv: list[str]) -> int:
    output = Path(argv[1]).resolve() if len(argv) > 1 else DEFAULT_OUTPUT
    files = collect_files(output)
    if not any(p.name == PRESENTATION_PDF for p in files):
        print(f"Presentation PDF not found: {PRESENTATION_PDF}", file=sys.stderr)
        return 1
    write_zip(output, files)
    for path in files:
        print(path.relative_to(ROOT))
    print(f"\n{len(files)} files -> {output} ({output.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
