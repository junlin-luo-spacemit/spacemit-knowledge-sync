#!/usr/bin/env python3
"""Synchronize canonical review rules to documentation repositories.

By default, compare the canonical glossary and entity YAML files in this
repository with the copies used by each documentation repository's PR reviewer.
Use --apply to update only the files that differ.

Usage:
    python scripts/sync_review_rules.py
    python scripts/sync_review_rules.py --target docs-chip
    python scripts/sync_review_rules.py --apply
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = ROOT / "glossary.yaml"
ENTITIES = ROOT / "entities"
CONSUMER_ROOT = Path(os.environ.get("SYNC_CONSUMER_ROOT", ROOT.parent))

TARGETS = {
    "docs-chip": CONSUMER_ROOT / "docs-chip" / ".github" / "doc-review-agent",
    "docs-product": CONSUMER_ROOT / "docs-product" / ".github" / "doc-review-agent",
}


def configure_output() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in {"utf-8", "utf-8-sig"}:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def canonical_files() -> list[Path]:
    return [GLOSSARY, *sorted(ENTITIES.glob("*.yaml"))]


def destination(source: Path, target_root: Path) -> Path:
    if source == GLOSSARY:
        return target_root / source.name
    return target_root / "entities" / source.name


def sync_target(name: str, target_root: Path, apply: bool) -> list[Path]:
    if not target_root.is_dir():
        raise FileNotFoundError(f"{name}: review-agent directory not found: {target_root}")

    differing: list[Path] = []
    for source in canonical_files():
        target = destination(source, target_root)
        if target.is_file() and filecmp.cmp(source, target, shallow=False):
            continue

        differing.append(target)
        status = "MISSING" if not target.exists() else "DIFFERS"
        print(f"{status}  {name}/{target.relative_to(target_root).as_posix()}")

        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            print(f"UPDATED  {name}/{target.relative_to(target_root).as_posix()}")

    if not differing:
        print(f"OK       {name}: canonical rules are synchronized")
    return differing


def main() -> int:
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=sorted(TARGETS),
        action="append",
        help="check or update only this documentation repository (repeatable)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="copy canonical files to targets that differ",
    )
    args = parser.parse_args()

    targets = args.target or sorted(TARGETS)
    differences: list[Path] = []
    for name in targets:
        differences.extend(sync_target(name, TARGETS[name], args.apply))

    if args.apply:
        print(f"\nUpdated {len(differences)} file(s).")
        return 0

    if differences:
        print(f"\n{len(differences)} file(s) differ. Run with --apply after reviewing the changes.")
        return 1

    print("\nAll review rule copies are synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
