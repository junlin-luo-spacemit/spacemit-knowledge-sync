#!/usr/bin/env python3
"""Scan doc repos for missing bilingual counterparts.

For every .md file under en/ there must be a matching file under zh/,
and vice versa — unless the path matches an en_only or zh_only pattern
in config.yaml. Reports each missing counterpart as repo/file:missing with
the direction (EN→ZH or ZH→EN) so the fix location is unambiguous.

Usage:
    python scripts/lint_bilingual.py                 # whole corpus
    python scripts/lint_bilingual.py --repo docs-chip
    python scripts/lint_bilingual.py --summary       # one line per repo
"""

from __future__ import annotations

import argparse
import fnmatch
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


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def is_exempt(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns)


def md_files(lang_root: Path) -> set[str]:
    if not lang_root.is_dir():
        return set()
    return {
        p.relative_to(lang_root).as_posix()
        for p in lang_root.rglob("*.md")
    }


def scan(repo_name: str, repo_cfg: dict, summary: bool) -> tuple[list[str], int, int]:
    repo_path = (ROOT / repo_cfg["path"]).resolve()
    if not repo_path.is_dir():
        return [f"SKIP  repo '{repo_name}' not found at {repo_path}"], 0, 0

    en_only = repo_cfg.get("en_only", [])
    zh_only = repo_cfg.get("zh_only", [])

    en_files = md_files(repo_path / "en")
    zh_files = md_files(repo_path / "zh")

    findings: list[str] = []
    missing_zh = 0
    missing_en = 0

    for rel in sorted(en_files):
        if is_exempt(rel, en_only):
            continue
        if rel not in zh_files:
            missing_zh += 1
            if not summary:
                findings.append(
                    f"MISSING ZH  {repo_name}/en/{rel}\n"
                    f"            → expected zh/{rel}"
                )

    for rel in sorted(zh_files):
        if is_exempt(rel, zh_only):
            continue
        if rel not in en_files:
            missing_en += 1
            if not summary:
                findings.append(
                    f"MISSING EN  {repo_name}/zh/{rel}\n"
                    f"            → expected en/{rel}"
                )

    return findings, missing_zh, missing_en


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None, help="check one repo only")
    parser.add_argument(
        "--summary", action="store_true",
        help="one line per repo instead of per-file findings"
    )
    args = parser.parse_args()

    config = load_config()
    repos = config.get("repos", {})

    if args.repo and args.repo not in repos:
        sys.exit(f"Unknown repo '{args.repo}'. Available: {', '.join(repos)}")

    total_missing = 0
    all_findings: list[str] = []

    for name, cfg in repos.items():
        if args.repo and name != args.repo:
            continue
        findings, mzh, men = scan(name, cfg, args.summary)
        total_missing += mzh + men
        if args.summary:
            en_count = len(md_files((ROOT / cfg["path"]).resolve() / "en"))
            zh_count = len(md_files((ROOT / cfg["path"]).resolve() / "zh"))
            exempt = len(cfg.get("en_only", [])) + len(cfg.get("zh_only", []))
            status = "OK" if (mzh + men) == 0 else "GAPS"
            print(
                f"{status}  {name}: en={en_count} zh={zh_count} "
                f"missing_zh={mzh} missing_en={men} "
                f"(exempt patterns: {exempt})"
            )
        else:
            all_findings.extend(findings)

    if not args.summary:
        if not all_findings:
            print("All bilingual counterparts present.")
            return 0
        for finding in all_findings:
            print(finding)
            print()
        print(f"{total_missing} missing counterpart(s).")

    return 1 if total_missing > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
