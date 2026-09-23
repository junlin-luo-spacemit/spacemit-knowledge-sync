# spacemit-knowledge-sync

Local consistency checker for SpacemiT documentation. Finds terminology drift
and entity-description drift across `docs-chip` and `docs-product`, and reports
the exact file and line that needs updating.

## What it catches

**Terminology drift** (`lint_terms.py`) — a term written in a non-preferred
form somewhere in the corpus. Fully deterministic grep, backed by
[glossary.yaml](glossary.yaml).

**Description drift** (`lint_descriptions.py`) — entities (K1, K3, P1, P1S,
MUSE Pi, K3 products) described with values that contradict their canonical
description, or with inconsistent phrasing across files. Backed by
[entities/](entities).

Each finding names `repo/file.md:line`, so the fix location is unambiguous.

## Usage

```bash
pip install -r requirements.txt

# Whole corpus (both docs-chip and docs-product)
python scripts/lint_terms.py
python scripts/lint_descriptions.py

# Only specific files
python scripts/lint_terms.py --changed en/key_stone/k1/k1_docs/k1_ds.md

# Single entity, or a single language tree
python scripts/lint_descriptions.py --entity K1
python scripts/lint_terms.py --lang zh
```

## Layout

```
config.yaml              repo paths (docs-chip, docs-product)
glossary.yaml            preferred terms + forbidden variants + unit conventions
entities/*.yaml          canonical description + attributes per chip/product
scripts/lint_terms.py    terminology checks
scripts/lint_descriptions.py  entity description checks
```

## Adding a rule

**Terminology:** add an entry to `glossary.yaml` with `term`, the `zh`/`en`
preferred form, and `forbidden_zh` / `forbidden_en` lists.

**Description:** add an `attributes` entry to the relevant `entities/*.yaml`
with `canonical_en` / `canonical_zh` and the `variants_*` lists. Set
`conflict: true` when the en and zh sources legitimately disagree and a human
must decide.

## Tracked entities

- `k1.yaml` — K1 chip (8-core, 2.0 TOPS, LPDDR4X)
- `k3.yaml` — K3 chip (X100/A100 cores, 60 TOPS, 30B models)
- `p1.yaml` — P1 PMIC (6 buck + 12 LDO)
- `p1s.yaml` — P1S PMIC (6 buck + LDO conflict flagged)
- `muse_pi.yaml` — MUSE Pi product (K1-based)
- `k3_products.yaml` — K3 Pico, CoM260, RV2768 (K3-based)
