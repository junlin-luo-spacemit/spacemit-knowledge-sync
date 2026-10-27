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

# Check whether the rule copies used by documentation PR reviewers match this repository
python scripts/sync_review_rules.py

# After reviewing the reported differences, update both consumer repositories
python scripts/sync_review_rules.py --apply
```

## Canonical Rule Synchronization

This repository is the canonical source for `glossary.yaml` and `entities/*.yaml`.
The PR review workflows in `docs-chip` and `docs-product` consume copies under
`.github/doc-review-agent/`. Use `sync_review_rules.py` to keep them aligned:

- `python scripts/sync_review_rules.py` reports missing or different copies and
  exits with status `1` when synchronization is needed. It makes no changes.
- `python scripts/sync_review_rules.py --target docs-chip` checks one consumer.
- `python scripts/sync_review_rules.py --apply` copies canonical rules to both
  consumers. Review the target repositories' diffs before committing them.

The consumer repositories keep their existing PR workflows; synchronization
only updates the deterministic terminology and entity-description rules those
workflows use.

### Weekly Drift Check

[review-rule-drift.yml](.github/workflows/review-rule-drift.yml) runs every
Monday at 02:00 UTC and can also be started manually from the Actions tab. It
checks the canonical rules against the PR-review copies in both documentation
repositories without modifying either repository:

- When copies differ, it creates one `Review rules are out of sync` tracking
  issue here, or updates the existing open issue.
- When the copies match later, it closes that tracking issue automatically.
- It does not infer, change, or approve product specifications. Add approved
  product facts to the canonical YAML files before synchronizing them.

Before enabling the workflow, no additional secrets are required because
`spacemit-com/docs-chip` and `spacemit-com/docs-product` are public repositories.
The workflow uses its built-in `GITHUB_TOKEN` only to create or update the
tracking issue in this repository. If either documentation repository becomes
private in the future, add a `REVIEW_RULES_TOKEN` Actions secret — a
fine-grained PAT with read-only **Contents** access to both repositories — and
add `token: ${{ secrets.REVIEW_RULES_TOKEN }}` to both consumer checkout steps.

## Versioning and Rule Releases

Use Git history as the audit trail for every approved glossary, entity, fragment,
or checker change. Keep commits focused and use conventional-style summaries,
for example:

```text
feat(rules): add K4 canonical descriptions
fix(glossary): standardize I²C notation
chore(review-rules): sync spacemit-knowledge-sync@<commit-sha>
```

Create an annotated semantic-version tag for a reviewed rule-set milestone:

- **Minor version** (`v0.2.0`): new product coverage, rule categories, or checker capabilities.
- **Patch version** (`v0.1.1`): corrections to existing facts, terminology, tests, or tooling.
- **Major version** (`v1.0.0`): intentional breaking changes to rule formats or consumer behavior.

When copying canonical rules to a consumer repository, use the canonical source
commit SHA in that consumer commit message. This makes every PR-review rule set
traceable to a precise version of this repository.

## Fragment Registry and Impact Analysis

The [fragments/](fragments) registry stores canonical technical facts at a
subsystem level (for example, processor, connectivity, GPU, display, and
security) and maps each fact to documentation files that reuse it. Use it when
a source specification changes and you need to identify every downstream page
that may require a corresponding update:

```bash
# Verify every registered reference still contains its canonical value
python scripts/lint_fragments.py

# Check a single chip or one named fragment
python scripts/lint_fragments.py --chip K1
python scripts/lint_fragments.py --fragment ai_compute

# List all registered downstream references without validating them
python scripts/lint_fragments.py --impact ai_compute K1
```

Use `entities/*.yaml` for product-level descriptions and attributes checked on
individual lines. Use `fragments/*.yaml` for reusable subsystem facts and
cross-repository impact analysis. Add a `used_in` path whenever a canonical
fragment is intentionally reused in `docs-chip` or `docs-product`.

## Example Findings

```text
[WARN] TERM  'I2C' → prefer 'I²C'
      at docs-chip/en/key_stone/k1/k1_docs/k1_ds.md:81
      I2C (×10)

WARN  ai_compute: '2.0 TOPS' expected, line uses ['2 TOPS']
        at docs-chip/en/key_stone/k1/k1_docs/root_overview.md:13
```

Each finding identifies the repository-relative file and line. `WARN` records
a preferred wording or formatting update; `CONFLICT` means the configured
sources disagree and needs a human decision before a canonical rule is changed.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Layout

```
config.yaml              repo paths (docs-chip, docs-product)
glossary.yaml            preferred terms + forbidden variants + unit conventions
entities/*.yaml          canonical description + attributes per chip/product
scripts/lint_terms.py    terminology checks
scripts/lint_descriptions.py  entity description checks
scripts/sync_review_rules.py  canonical rule synchronization/checks
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
