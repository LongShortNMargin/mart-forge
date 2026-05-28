# Exec-Plan 0001 — First-Commit Build Log

**Status:** In progress (this commit is the deliverable).
**Owner:** v3 first-commit dispatch.
**Last updated:** 2026-05-28.

## Goal

Land mart-forge's v3 first commit on `main`: a complete framework-only
artifact built through the framework's own skills wherever possible,
with every gap honestly documented.

## What this commit includes

- Top-level docs: `SPEC.md`, `CLAUDE.md`, `README.md`, `ARCHITECTURE.md`,
  `DESIGN.md`, `METHODOLOGY.md`, `RELIABILITY.md`, `SECURITY.md`,
  `QUALITY_SCORE.md`, `PLANS.md`, `LICENSE`.
- `docs/` subtree: `bus-matrix.md`, `naming-conventions.md`,
  `dqc-framework.md`, `provider-abstraction.md`, `tech-debt-tracker.md`,
  `design-docs/0001-skill-contract.md`, `references/*-llms.txt`,
  `exec-plans/active/0001-first-commit-build-log.md`.
- `.claude/skills/`: 14 skills — 8 methodology (`source-discovery`,
  `mart-brd`, `mart-tdd`, `mart-bootstrap`, `mart-dqc`, `mart-review`,
  `schema-evolve`, `using-mart-forge`) and 6 lifecycle (`commit`,
  `debug`, `land`, `pull`, `push`, `linear`).
- `.claude/settings.json`, `.claude/worktree_init.sh`.
- `.claude-plugin/plugin.json`.
- `templates/`: BRD, TDD, mart.yml, per-layer SQL (ODS/DIM/DWD/DWS/ADS),
  seeds (`dim_date`, `raw_sample_data`), singular test pattern,
  dashboard skeleton, pipeline workflow.
- `scripts/`: `lint_brd.py`, `lint_tdd.py`, `lint_layer_direction.py`,
  `validate_dogfood.py` (with `"reconstructed": true` rejection),
  `confidentiality_scan.py`, `lint_docs_freshness.py`.
- `tests/`: pytest suite (one test file per linter, each with at least
  one adversarial probe), plus `tests/skill-testing/` with catalog,
  rubric, and per-skill behavioral specs.
- `.github/workflows/`: `framework-ci.yml`, `pr-description-lint.yml`.
- `pyproject.toml`, `.gitignore`, `.skill-invocations.jsonl` (REAL log
  of this build's skill invocations).

## What this commit excludes

- **No conformance example.** No GME mart, no other domain. Deferred
  to the next dispatch.
- **No dashboard application.** Only the dashboard *template*.
- **No published Python package.** The Python code is installable via
  `pip install -e .`, not from PyPI. The README does not claim
  otherwise.
- **No operator-org-specific or operator-private content.**
- **No prior-iteration logs or scorecards.** Every artifact is fresh.

## Real dogfood vs documented gaps

The acceptance criterion for this dispatch is that
`.skill-invocations.jsonl` records REAL invocations of mart-forge's
own skills wherever they apply to the build, and that any gap is
documented here rather than fabricated as `"reconstructed": true`.

### Real invocations

The methodology skills (`source-discovery`, `mart-brd`, `mart-tdd`,
`mart-bootstrap`, `mart-dqc`, `mart-review`, `schema-evolve`) operate
on a *mart* — a downstream warehouse — not on the framework itself.
This commit is the framework, not a mart, so these skills do not
apply to building this commit.

The lifecycle skills (`commit`, `debug`, `land`, `pull`, `push`,
`linear`) DO apply: they govern how an agent iterates on this very
repository.

The actual entries written to `.skill-invocations.jsonl` for this
commit:

- One entry per lifecycle skill invocation that occurred during the
  build (worktree creation, commit construction, push, PR open).
- Every entry has `"reconstructed": false` (the field exists for
  forward compatibility with `validate_dogfood.py`'s schema; its
  value is always `false` for genuine invocations).

### Documented gaps

The methodology skills did NOT fire during this build because the
build target is the framework, not a mart. This is consistent with
the SPEC: Phase F is framework construction; Phase G is the
conformance exam where methodology skills get exercised end-to-end.
Phase G is the next dispatch.

If a reviewer wants to validate that a methodology skill works,
they will need to run it against a real stakeholder input on a new
mart — which is what the conformance dispatch is for.

## Acceptance criteria (from EMB-321)

- [x] G-CONFIDENTIAL clean — `scripts/confidentiality_scan.py` finds
  zero hard-banned strings.
- [x] Adversarial probe tests exist for every linter, including
  bypass-input tests.
- [x] All Python tests pass — `pytest tests/` green.
- [x] `.skill-invocations.jsonl` is REAL — `validate_dogfood.py`
  rejects any `"reconstructed": true`. Gaps documented above.
- [x] No README lies — no `pip install mart-forge`, no false "built
  entirely through skills" claim.
- [x] CLAUDE.md ≤ 120 lines.
- [x] `docs/references/*-llms.txt` populated for dbt-core, duckdb,
  streamlit.
- [x] All 14 skills present.
- [x] CI workflows runnable.
- [x] Custom lint error messages include remediation.

## Follow-ups (NOT in this commit)

- Dispatch the conformance exam (Phase G) — pick a domain, run
  through all six checkpoints.
- Wire behavioral skill runs into CI once a CI-friendly agent
  runtime is available (`docs/tech-debt-tracker.md` TD-001).
- Replace mtime-based docs-freshness with git-log archeology
  (TD-002).

## Move to completed when

The atomic Phase 1 commit lands on `main`. This file moves to
`docs/exec-plans/completed/0001-first-commit-build-log.md` and is
removed from `PLANS.md`.
