# spacemit-knowledge-sync

Cross-repo consistency checker for SpacemiT documentation. Finds terminology
drift and entity-description drift between `docs-chip` (and later
`docs-product`), and reports the exact file and line that needs updating.

## What it catches

**Terminology drift** (`lint_terms.py`) — a term written in a non-preferred
form somewhere in the corpus. Fully deterministic grep, backed by
[glossary.yaml](glossary.yaml).

**Description drift** (`lint_descriptions.py`) — an entity (K1, K3, P1, P1S)
described with values that contradict its canonical description, or with
inconsistent phrasing across files. Backed by [entities/](entities).

Each finding names `repo/file.md:line`, so the fix location is unambiguous.

## Usage

```bash
pip install -r requirements.txt

# Whole corpus
python scripts/lint_terms.py
python scripts/lint_descriptions.py

# Only files changed in a PR
python scripts/lint_terms.py --changed en/key_stone/k1/k1_docs/k1_ds.md

# Single entity, or a single language tree
python scripts/lint_descriptions.py --entity K1
python scripts/lint_terms.py --lang zh
```

## Layout

```
config.yaml              repo paths, check toggles, exclusions
glossary.yaml            preferred terms + forbidden variants (+ unit conventions)
entities/*.yaml          canonical description + attributes per product
scripts/lint_terms.py    terminology checks
scripts/lint_descriptions.py  entity description checks
.github/workflows/       sync-checker.yml — runs on repository_dispatch
```

## Adding a rule

Terminology: add an entry to `glossary.yaml` with `term`, the `zh`/`en`
preferred form, and `forbidden_zh` / `forbidden_en` lists.

Description: add an `attributes` entry to the relevant `entities/*.yaml` with
`canonical_en` / `canonical_zh` and the `variants_*` lists. Set
`conflict: true` when the en and zh sources legitimately disagree and a human
must decide.

## CI wiring

`docs-chip` fires a `docs-updated` repository_dispatch on every PR touching
`en/**/*.md` or `zh/**/*.md` (see `.github/workflows/notify-knowledge-sync.yml`
in that repo). This repo's workflow checks out both, runs the linters, and
posts the findings back as a PR comment.

Required secrets/vars:

| Where | Name | Purpose |
|---|---|---|
| docs-chip | `KNOWLEDGE_SYNC_DISPATCH_TOKEN` | PAT with `repo` scope on this repo |
| this repo | `DOCS_READ_TOKEN` | clone docs-chip |
| this repo | `DOCS_WRITE_TOKEN` | comment on docs-chip PRs |
| this repo | `vars.DOCS_CHIP_REPO` | e.g. `yourusername/docs-chip` |

The check posts a comment only — it never blocks merge.
