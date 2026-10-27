#!/usr/bin/env python3
"""Scan doc repos for forbidden terminology variants.

Loads glossary.yaml and greps every .md file for forbidden strings,
reporting each hit as repo/file:line with the preferred form.

Usage:
    python scripts/lint_terms.py                       # whole corpus
    python scripts/lint_terms.py --changed a.md b.md   # PR-changed files only
    python scripts/lint_terms.py --lang zh             # one language only
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
GLOSSARY_PATH = ROOT / "glossary.yaml"


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_glossary() -> list[dict]:
    with GLOSSARY_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def is_excluded(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pat) for pat in patterns)


def lang_of(rel_path: str) -> str:
    return "zh" if rel_path.replace("\\", "/").startswith("zh/") else "en"


def iter_markdown(repo_path: Path, exclude: list[str], lang_filter: str | None):
    for path in sorted(repo_path.rglob("*.md")):
        rel = path.relative_to(repo_path).as_posix()
        if is_excluded(rel, exclude):
            continue
        if lang_filter and lang_of(rel) != lang_filter:
            continue
        yield path, rel


def scan(repo_name: str, repo_cfg: dict, glossary: list[dict],
         config: dict, changed: list[str] | None,
         lang_filter: str | None) -> list[tuple[str, str]]:
    """Return list of (severity, message) tuples."""
    repo_path = (ROOT / repo_cfg["path"]).resolve()
    if not repo_path.is_dir():
        return [("SKIP", f"repo '{repo_name}' not found at {repo_path}")]

    exclude = config.get("exclude", [])
    results = []

    for path, rel in iter_markdown(repo_path, exclude, lang_filter):
        if changed is not None and rel not in changed:
            continue
        lang = lang_of(rel)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            results.append(("SKIP", f"{repo_name}/{rel} — not valid UTF-8"))
            continue

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Skip code blocks and indented code
            if stripped.startswith("```") or stripped.startswith("    "):
                continue
            # Skip lines that are pure URLs or Markdown link syntax
            if re.search(r'^\[.*\]\(.*\)$', stripped) or stripped.startswith("http"):
                continue
            
            # Strip inline code spans, URLs, and Markdown links before checking
            clean_line = re.sub(r'`[^`]+`', '', line)
            clean_line = re.sub(r'https?://[^\s]+', '', clean_line)
            clean_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_line)
            # Strip signal/pin identifiers like I2C0_SDA, CAM_I2C0_SCL, GPIO[3]_50
            clean_line = re.sub(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b', '', clean_line)
            clean_line = re.sub(r'\bGPIO\[\d+\]_\d+', '', clean_line)

            for entry in glossary:
                scope = entry.get("scope", "both")
                if scope != "both" and scope != lang:
                    continue

                forbidden_key = f"forbidden_{lang}"
                forbidden = entry.get(forbidden_key, [])
                preferred = entry.get(lang) if lang == "zh" else entry.get("term")

                for variant in forbidden:
                    if variant in clean_line:
                        msg = (
                            f"TERM  '{variant}' → prefer '{preferred}'\n"
                            f"      at {repo_name}/{rel}:{lineno}\n"
                            f"      {stripped[:160]}"
                        )
                        results.append(("WARN", msg))

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed", nargs="*", default=None,
                        help="only check these repo-relative paths")
    parser.add_argument("--lang", choices=["en", "zh"], default=None,
                        help="restrict to one language tree")
    args = parser.parse_args()

    config = load_config()
    glossary = load_glossary()

    print(f"Loaded {len(glossary)} glossary entries\n")

    all_results = []
    for repo_name, repo_cfg in config["repos"].items():
        all_results.extend(
            scan(repo_name, repo_cfg, glossary, config,
                 args.changed, args.lang)
        )

    if not all_results:
        print("No terminology violations found.")
        return 0

    for severity, msg in all_results:
        print(f"[{severity}] {msg}\n")

    print(f"{len(all_results)} finding(s).")
    return 1 if any(s == "ERROR" for s, _ in all_results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
