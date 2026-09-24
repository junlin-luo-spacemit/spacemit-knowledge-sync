#!/usr/bin/env python3
"""Fragment impact linter.

Reads fragments/*.yaml and verifies every `used_in` reference:
  1. The file exists in the mapped repo.
  2. The canonical value appears on or near the mapped line.

When a fragment's canonical value changes, this script tells you
exactly which other files also reference that value and need updating.

Usage:
    python scripts/lint_fragments.py                    # check all fragments
    python scripts/lint_fragments.py --chip K1          # one chip only
    python scripts/lint_fragments.py --fragment ai_compute  # one fragment
    python scripts/lint_fragments.py --impact ai_compute K1 # impact analysis
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
FRAGMENTS_DIR = ROOT / "fragments"
CONFIG_PATH = ROOT / "config.yaml"
def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_fragments(chip_filter: str | None = None) -> list[dict]:
    result = []
    for path in sorted(FRAGMENTS_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if chip_filter and data.get("chip", "").lower() != chip_filter.lower():
            continue
        data["_file"] = path
        result.append(data)
    return result


def repo_path(config: dict, ref: str) -> Path | None:
    """Resolve 'docs-chip/en/foo.md' to an absolute path."""
    parts = ref.split("/", 1)
    if len(parts) < 2:
        return None
    repo_name = parts[0]
    repos = config.get("repos", {})
    if repo_name not in repos:
        return None
    base = (ROOT / repos[repo_name]["path"]).resolve()
    return base / parts[1]


def check_fragment(frag_name: str, frag: dict, config: dict,
                   fragment_filter: str | None) -> list[str]:
    findings = []
    for key, spec in frag.get("fragments", {}).items():
        if fragment_filter and key != fragment_filter:
            continue

        canonical_en = spec.get("canonical_en") or spec.get("canonical", "")
        canonical_zh = spec.get("canonical_zh") or spec.get("canonical", "")
        conflict = spec.get("conflict", False)

        if conflict:
            findings.append(
                f"CONFLICT  {frag_name}/{key}: "
                f"canonical_en='{canonical_en}' canonical_zh='{canonical_zh}' — "
                f"needs human decision\n  {spec.get('note', '')}"
            )

        for ref in spec.get("used_in", []):
            abs_path = repo_path(config, ref)
            if abs_path is None:
                findings.append(f"WARN  {frag_name}/{key}: unknown repo in ref '{ref}'")
                continue
            if not abs_path.exists():
                findings.append(
                    f"WARN  {frag_name}/{key}: file not found\n  {ref}"
                )
                continue

            try:
                content = abs_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                findings.append(f"SKIP  {frag_name}/{key}: UTF-8 decode error\n  {ref}")
                continue

            # Pick the right canonical based on path language
            lang = "zh" if "/zh/" in ref.replace("\\", "/") else "en"
            canonical = canonical_zh if lang == "zh" else canonical_en

            if not canonical:
                continue

            if canonical not in content:
                findings.append(
                    f"DRIFT  {frag_name}/{key} ({lang}): "
                    f"expected '{canonical}' not found\n"
                    f"  in {ref}"
                )

    return findings


def impact_report(fragment_key: str, chip_filter: str | None,
                  fragments: list[dict], config: dict) -> None:
    """Print every file that references a given fragment key."""
    print(f"\nImpact report for fragment '{fragment_key}'")
    print("=" * 60)
    found = False
    for frag in fragments:
        chip = frag.get("chip", "?")
        for key, spec in frag.get("fragments", {}).items():
            if key != fragment_key:
                continue
            found = True
            canonical_en = spec.get("canonical_en") or spec.get("canonical", "")
            canonical_zh = spec.get("canonical_zh") or spec.get("canonical", "")
            print(f"\nChip: {chip}")
            print(f"  canonical_en: {canonical_en}")
            print(f"  canonical_zh: {canonical_zh}")
            if spec.get("note"):
                print(f"  note: {spec['note']}")
            print(f"\n  Used in {len(spec.get('used_in', []))} location(s):")
            for ref in spec.get("used_in", []):
                abs_path = repo_path(config, ref)
                exists = "✓" if (abs_path and abs_path.exists()) else "✗ MISSING"
                print(f"    [{exists}] {ref}")
    if not found:
        print(f"  No fragment named '{fragment_key}' found.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chip", help="Filter to one chip (K1, K3, P1, P1S)")
    parser.add_argument("--fragment", help="Filter to one fragment key (e.g. ai_compute)")
    parser.add_argument("--impact", nargs="+",
                        help="Show impact report for fragment key(s) without validation")
    args = parser.parse_args()

    config = load_config()
    chip_filter = args.chip
    fragments = load_fragments(chip_filter)

    if not fragments:
        print("No fragments matched.")
        return 0

    print(f"Loaded {len(fragments)} fragment file(s): "
          f"{', '.join(f['chip'] for f in fragments)}\n")

    if args.impact:
        for key in args.impact:
            impact_report(key, chip_filter, fragments, config)
        return 0

    all_findings = []
    for frag in fragments:
        all_findings.extend(
            check_fragment(frag["chip"], frag, config, args.fragment)
        )

    if not all_findings:
        print("All fragment references verified — no drift found.")
        return 0

    for finding in all_findings:
        print(finding)
        print()

    drifts = sum(1 for f in all_findings if f.startswith("DRIFT"))
    conflicts = sum(1 for f in all_findings if f.startswith("CONFLICT"))
    missing = sum(1 for f in all_findings if f.startswith("WARN"))

    print(f"{len(all_findings)} finding(s): "
          f"{drifts} drift, {conflicts} conflict, {missing} warning.")
    return 1 if drifts > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
