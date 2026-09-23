#!/usr/bin/env python3
"""Scan doc repos for entity-description drift.

Locates every mention of a registered entity (via its aliases) and checks the
surrounding line against the entity's canonical attributes. Output is one line
per finding, with file:line so the fix location is unambiguous.

Usage:
    python scripts/lint_descriptions.py                 # whole corpus
    python scripts/lint_descriptions.py --changed a.md b.md
    python scripts/lint_descriptions.py --entity K1
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
ENTITIES_DIR = ROOT / "entities"

SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_entities(only: str | None = None) -> list[dict]:
    entities = []
    for path in sorted(ENTITIES_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if only and data["entity"].lower() != only.lower():
            continue
        data["_path"] = path
        entities.append(data)
    return entities


def is_excluded(rel_path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pat) for pat in patterns)


def lang_of(rel_path: str) -> str:
    return "zh" if rel_path.replace("\\", "/").startswith("zh/") else "en"


def iter_markdown(repo_path: Path, exclude: list[str]):
    for path in sorted(repo_path.rglob("*.md")):
        rel = path.relative_to(repo_path).as_posix()
        if is_excluded(rel, exclude):
            continue
        yield path, rel


def alias_spans(line: str, aliases: list[str]):
    """Yield (alias, start, end) for each alias occurrence in the line."""
    for alias in aliases:
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])")
        for match in pattern.finditer(line):
            yield alias, match.start(), match.end()


def check_attributes(line: str, entity: dict, lang: str) -> list[str]:
    """Flag attributes whose canonical form the line contradicts."""
    findings = []
    for attr in entity.get("attributes", []):
        canonical = attr.get(f"canonical_{lang}")
        variants = attr.get(f"variants_{lang}", [])
        if not canonical or not variants:
            continue
        # Only judge attributes the line actually talks about.
        if not any(v in line for v in variants):
            continue
        if canonical in line:
            continue
        if attr.get("conflict"):
            findings.append(
                f"CONFLICT  {attr['key']}: line uses {[v for v in variants if v in line]}, "
                f"canonical_{lang} is '{canonical}' — en/zh sources disagree, needs human decision"
            )
        else:
            findings.append(
                f"WARN  {attr['key']}: '{canonical}' expected, "
                f"line uses {[v for v in variants if v in line]}"
            )
    return findings


def scan(repo_name: str, repo_cfg: dict, entities: list[dict],
         config: dict, changed: list[str] | None) -> list[str]:
    repo_path = (ROOT / repo_cfg["path"]).resolve()
    if not repo_path.is_dir():
        return [f"SKIP  repo '{repo_name}' not found at {repo_path}"]

    exclude = config.get("exclude", [])
    results = []

    for path, rel in iter_markdown(repo_path, exclude):
        if changed is not None and rel not in changed:
            continue
        lang = lang_of(rel)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            results.append(f"SKIP  {repo_name}/{rel} — not valid UTF-8")
            continue

        for lineno, line in enumerate(lines, start=1):
            for entity in entities:
                if not list(alias_spans(line, entity["aliases"])):
                    continue
                for finding in check_attributes(line, entity, lang):
                    results.append(
                        f"{finding}\n"
                        f"        at {repo_name}/{rel}:{lineno}\n"
                        f"        {line.strip()[:160]}"
                    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed", nargs="*", default=None,
                        help="only check these repo-relative paths")
    parser.add_argument("--entity", default=None,
                        help="only check one entity, e.g. K1")
    args = parser.parse_args()

    config = load_config()
    entities = load_entities(args.entity)
    if not entities:
        sys.exit("No entities matched.")

    print(f"Loaded {len(entities)} entities: "
          f"{', '.join(e['entity'] for e in entities)}\n")

    all_results = []
    for repo_name, repo_cfg in config["repos"].items():
        all_results.extend(
            scan(repo_name, repo_cfg, entities, config, args.changed)
        )

    if not all_results:
        print("No description drift found.")
        return 0

    for block in all_results:
        print(block)
        print()

    errors = sum(1 for r in all_results if r.startswith("CONFLICT"))
    print(f"{len(all_results)} finding(s), {errors} conflict(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
