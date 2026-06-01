# Architecture

How the pieces of mart-forge fit together. For the rules and gates that
govern them, see `SPEC.md`. For the design principles that shaped them,
see `DESIGN.md`.

## The three layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Specification (SPEC.md)                                        │
│  — defines lifecycle, gates, artifacts, quality rubric           │
└─────────────────────────────────────────────────────────────────┘
                              ↑ governs
┌─────────────────────────────────────────────────────────────────┐
│  Framework artifacts (this repo)                                │
│  — templates, skills, linters, tests, plugin                     │
└─────────────────────────────────────────────────────────────────┘
                              ↑ produces
┌─────────────────────────────────────────────────────────────────┐
│  Conformance mart (a separate repo or examples/<mart-name>/)   │
│  — BRD, TDD, dbt models, seeds, dashboard, DQC scorecard         │
└─────────────────────────────────────────────────────────────────┘
```

The framework layer is the product. The conformance mart layer is the
proof. Mixing them is the failure mode mart-forge exists to prevent.

## Subsystem map

### Skills (`.claude/skills/`)

Two families.

**Methodology skills** drive the warehouse lifecycle:

| Skill | Phase | Reads | Writes |
|-------|-------|-------|--------|
| `using-mart-forge` | router | `mart.yml`, project state | console output |
| `source-discovery` | A0 | stakeholder input | `docs/source_catalog.json` |
| `mart-brd` | A | `source_catalog.json` | `docs/business-requirements.md` |
| `mart-tdd` | B | signed BRD | `docs/tech-design-doc.md` |
| `mart-bootstrap` | C | signed TDD | full dbt project + dashboard |
| `mart-dqc` | D | dbt `target/run_results.json` | `dqc_scorecard.json` |
| `mart-review` | review | all artifacts | readiness verdict |
| `schema-evolve` | maintenance | TDD + new column spec | model diffs + migration notes |

**Lifecycle skills** standardize how agents iterate on the warehouse
itself:

| Skill | Purpose |
|-------|---------|
| `commit` | Produce a single atomic commit with verifiable message |
| `debug` | Investigate a failure with explicit hypothesis log |
| `land` | Open a PR with full description and reviewer assignment |
| `pull` | Sync a remote branch into a new worktree |
| `push` | Push the current worktree to remote |
| `linear` | Operate on the issue tracker (issues, comments, status) |

### Templates (`templates/`)

Every artifact produced by a methodology skill is generated from a
template. Templates are versioned with the spec; changes go through the
spec edit process.

| Template | Used by | Output |
|----------|---------|--------|
| `business-requirements.template.md` | `mart-brd` | BRD draft |
| `tech-design-doc.template.md` | `mart-tdd` | TDD draft |
| `mart.yml.template` | `using-mart-forge` (init) | project manifest |
| `models/ods/template.sql` | `mart-bootstrap` | ODS model |
| `models/dim/template.sql` | `mart-bootstrap` | DIM model |
| `models/dwd/template.sql` | `mart-bootstrap` | DWD model |
| `models/dws/template.sql` | `mart-bootstrap` | DWS model |
| `models/ads/template.sql` | `mart-bootstrap` | ADS model |
| `seeds/dim_date.csv` | `mart-bootstrap` | dim_date seed |
| `seeds/raw_sample_data.csv` | `mart-bootstrap` | sample seed |
| `tests/template_singular.sql` | `mart-bootstrap` | singular test pattern |
| `dashboard/app.py` | `mart-bootstrap` | dashboard skeleton |
| `dashboard/requirements.txt` | `mart-bootstrap` | dashboard deps |
| `pipeline/daily.yml.template` | `mart-bootstrap` | CI workflow |

### Linters (`scripts/`)

Every linter is paired with an adversarial probe test in `tests/`.

| Linter | Enforces | Adversarial probe |
|--------|----------|-------------------|
| `lint_brd.py` | B-1 through B-4 present; every metric in B-3 has required fields | Missing section, missing field, bogus link_status |
| `lint_tdd.py` | T-1 through T-21 present; T-8 column rows have all 6 fields; T-9 ODS contract complete | Missing section, prose-in-calculation, contract field absent |
| `lint_layer_direction.py` | ODS->DIM->DWD->DWS->ADS direction in `ref()` calls | Upward reference (DWD referencing ADS) |
| `validate_dogfood.py` | `.skill-invocations.jsonl` schema valid; **rejects `"reconstructed": true`** | Reconstructed-true entry, missing required field |
| `confidentiality_scan.py` | No banned strings appear anywhere in the repo | Banned string in a docstring, comment, JSON field |
| `lint_docs_freshness.py` | Cross-references resolve; no stale references to deleted files | Dangling link, missing referenced file |

### Tests (`tests/`)

- `tests/test_lint_*.py` — pytest unit tests for each linter, including
  adversarial probe cases.
- `tests/test_validate_dogfood.py` — rejects bypass attempts, especially
  the `"reconstructed": true` shape from the prior failed iteration.
- `tests/test_confidentiality.py` — rejects banned strings and verifies
  the scanner does not produce false positives in legitimate prose.
- `tests/skill-testing/` — behavioral specs for every skill, plus
  catalog and quality rubric. The static checks here run as part of
  `pytest tests/`.

### CI (`.github/workflows/`)

| Workflow | Trigger | Steps |
|----------|---------|-------|
| `framework-ci.yml` | push, PR | lint, run linters with adversarial probes, pytest, confidentiality scan |
| `pr-description-lint.yml` | PR | verify PR body lists acceptance criteria with checkboxes |

### Plugin (`.claude-plugin/plugin.json`)

Registers the skills with Claude Code so they become available as slash
commands the moment a session opens the repository.

## Data flow for a new mart

```
stakeholder doc
      |
      v
/source-discovery   ──► docs/source_catalog.json
      |
      v
/mart-brd           ──► docs/business-requirements.md (signed)
      |
      v
/mart-tdd           ──► docs/tech-design-doc.md (signed)
      |
      v
/mart-bootstrap     ──► models/, seeds/, tests/, dashboard/, mart.yml
      |
      v
dbt seed && dbt run && dbt test
      |
      v
/mart-dqc           ──► dqc_scorecard.json, coverage_manifest.json
      |
      v
/mart-review        ──► readiness verdict
```

Each arrow is a hard gate. Each step writes a line to
`.skill-invocations.jsonl` so the chain is auditable end-to-end.

## What lives where

| Concern | Owned by |
|---------|----------|
| Lifecycle rules and gate definitions | `SPEC.md` |
| Skill execution and gate enforcement at runtime | `.claude/skills/<name>/SKILL.md` |
| Structural validation independent of the agent | `scripts/lint_*.py` |
| Adversarial probe coverage | `tests/test_lint_*.py` |
| Behavioral coverage of skills | `tests/skill-testing/specs/*.spec.md` |
| Per-skill quality grade | `QUALITY_SCORE.md` |
| Confidentiality enforcement | `scripts/confidentiality_scan.py` plus `SECURITY.md` |
