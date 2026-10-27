#!/usr/bin/env python3
"""Open or update a tracking issue when canonical review rules drift.

This is used by the scheduled GitHub Actions workflow. It checks rule copies in
locally checked out documentation repositories and creates one issue when they
differ. It never modifies consumer repositories.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "scripts" / "sync_review_rules.py"
ISSUE_MARKER = "<!-- review-rule-sync -->"
ISSUE_TITLE = "Review rules are out of sync"


def run_check() -> str:
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def github_request(method: str, endpoint: str, token: str, **kwargs) -> requests.Response:
    response = requests.request(
        method,
        f"https://api.github.com{endpoint}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30,
        **kwargs,
    )
    response.raise_for_status()
    return response


def find_open_issue(repository: str, token: str) -> dict | None:
    response = github_request(
        "GET", f"/repos/{repository}/issues", token, params={"state": "open", "per_page": 100}
    )
    return next((issue for issue in response.json() if ISSUE_MARKER in issue.get("body", "")), None)


def issue_body(check_output: str) -> str:
    return f"""{ISSUE_MARKER}
## Scheduled review-rule synchronization check

The canonical review rules differ from the copies used by documentation PR reviewers.
No files were changed automatically.

```text
{check_output.strip()}
```

To review and apply the approved canonical rules locally:

```powershell
python scripts\\sync_review_rules.py
python scripts\\sync_review_rules.py --apply
```

Commit the resulting changes separately in `docs-chip` and `docs-product`.
"""


def main() -> int:
    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    output = run_check()
    print(output, end="")

    existing = find_open_issue(repository, token)
    if "All review rule copies are synchronized." in output:
        if existing:
            github_request(
                "PATCH",
                f"/repos/{repository}/issues/{existing['number']}",
                token,
                json={"state": "closed", "state_reason": "completed"},
            )
            print(f"Closed tracking issue #{existing['number']}.")
        return 0

    body = issue_body(output)
    if existing:
        github_request(
            "PATCH",
            f"/repos/{repository}/issues/{existing['number']}",
            token,
            json={"body": body},
        )
        print(f"Updated tracking issue #{existing['number']}.")
    else:
        response = github_request(
            "POST",
            f"/repos/{repository}/issues",
            token,
            json={"title": ISSUE_TITLE, "body": body},
        )
        print(f"Created tracking issue #{response.json()['number']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
