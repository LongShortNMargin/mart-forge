# Reliability

What makes mart-forge trustworthy isn't that the agent is careful — it's
that the loops which catch carelessness are baked in.

## The verification stack

```
┌──────────────────────────────────────────────────────────────┐
│  Hard gates in skills                                         │
│  — every skill rejects unsigned / missing prerequisites       │
└──────────────────────────────────────────────────────────────┘
                          ↓ caught by
┌──────────────────────────────────────────────────────────────┐
│  Linters (scripts/lint_*.py)                                  │
│  — structural validation independent of the agent             │
└──────────────────────────────────────────────────────────────┘
                          ↓ caught by
┌──────────────────────────────────────────────────────────────┐
│  Adversarial probe tests (tests/test_lint_*.py)               │
│  — every linter has bypass tests it must reject               │
└──────────────────────────────────────────────────────────────┘
                          ↓ caught by
┌──────────────────────────────────────────────────────────────┐
│  Skill behavioral specs (tests/skill-testing/specs/*.spec.md) │
│  — happy path + rejection path + edge cases per skill         │
└──────────────────────────────────────────────────────────────┘
                          ↓ caught by
┌──────────────────────────────────────────────────────────────┐
│  CI (.github/workflows/framework-ci.yml)                      │
│  — runs the whole stack on every PR                           │
└──────────────────────────────────────────────────────────────┘
```

A defect that escapes one layer is caught by the next.

## The linters

| Linter | Rejects |
|--------|---------|
| `lint_brd.py` | Missing B-1..B-4, missing per-metric fields, bogus `link_status`, B-3 metric without source binding |
| `lint_tdd.py` | Missing T-1..T-21, T-8 row missing any of the 6 fields, prose in `calculation` for derived columns, T-9 ODS contract missing a required field |
| `lint_layer_direction.py` | `ref()` upward (DWD -> ADS, DWS -> DIM, etc.). Maintains the strict ODS->DIM->DWD->DWS->ADS direction. |
| `validate_dogfood.py` | Any entry containing `"reconstructed": true`. Invalid JSONL line. Missing required field. |
| `confidentiality_scan.py` | Any banned string anywhere in tracked files. |
| `lint_docs_freshness.py` | Dangling cross-references; references to deleted files; stale spec filenames. |

Every linter exits non-zero on failure. CI runs every linter on every
PR. None of them can be disabled without changing the workflow file,
which is itself code review.

## The tests

Three categories under `tests/`:

1. **Linter unit tests** — for every linter, a `tests/test_lint_*.py`
   that covers happy path, structural failure, and one or more
   adversarial probes.
2. **Adversarial dogfood test** — `tests/test_validate_dogfood.py`
   includes the specific case that defeated the prior iteration:
   `"reconstructed": true`. It also covers missing fields, malformed
   JSONL, and empty logs.
3. **Skill testing framework** — `tests/skill-testing/` carries a
   catalog (`catalog.yaml`), a rubric (`quality-rubric.md`), and
   per-skill behavioral specs. Static structural checks against every
   spec file run as part of `pytest tests/`.

The pytest suite line count is at least equal to the `scripts/` line
count — this is a discipline metric, not a target. If the linters grow,
the tests grow with them.

## CI

`.github/workflows/framework-ci.yml` runs on push and pull request:

1. Install Python deps.
2. Run `python scripts/confidentiality_scan.py .` first — fail-fast on
   any banned string.
3. Run `python scripts/lint_brd.py templates/business-requirements.template.md`.
4. Run `python scripts/lint_tdd.py templates/tech-design-doc.template.md`.
5. Run `python scripts/lint_layer_direction.py templates/models/`.
6. Run `python scripts/validate_dogfood.py .skill-invocations.jsonl`.
7. Run `python scripts/lint_docs_freshness.py .`.
8. Run `pytest tests/`.

`.github/workflows/pr-description-lint.yml` runs on pull requests and
fails if the PR body does not list the acceptance criteria with
checkboxes.

## Local equivalence

A contributor SHOULD be able to reproduce CI locally:

```bash
python scripts/confidentiality_scan.py .
python scripts/lint_brd.py templates/business-requirements.template.md
python scripts/lint_tdd.py templates/tech-design-doc.template.md
python scripts/lint_layer_direction.py templates/models/
python scripts/validate_dogfood.py .skill-invocations.jsonl
python scripts/lint_docs_freshness.py .
pytest tests/
```

If any of these diverges from CI, the divergence is the bug.

## What does NOT belong in this stack

- **Type checking the templates.** Templates are markdown, not Python.
  Their validation is structural.
- **End-to-end runs against live providers.** The framework does not
  ship a live data provider; the conformance example runs that loop.
- **Performance benchmarks.** mart-forge is not a runtime; benchmarking
  it would benchmark dbt and DuckDB, which their own projects already
  do.

## When a check fails

1. Read the error message. Every check is required to print the file,
   the location, and the remediation.
2. Fix the underlying artifact (template, doc, skill).
3. Re-run only the failing check first. If it passes, run the full
   suite.
4. If the linter is wrong, fix the linter (and its test). Do not
   suppress.

## When CI is wrong

CI is the last layer; a CI bug is worse than a linter bug because it
hides defects behind a green check. If CI passes when a local run
fails:

- The CI workflow is the bug. Fix the workflow.
- If the local environment is the bug, document the difference in
  `pyproject.toml` and in this file.
