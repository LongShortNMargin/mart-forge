# mart-forge — agent onboarding

This file is auto-loaded into every agent session in this repo. Keep it short.
For depth, follow the links — each section name below is also a file at the
top of the repo.

## What you are working on

mart-forge is a Claude Code marketplace plugin pack for lifecycle-first
Kimball data warehouses. The product is the **plugin pack itself** — the
skills under `./skills/{lifecycle,workflow,duckdb,quality}/`, the
templates, the linters, and the SPEC that an agent uses to build a
warehouse for a specific mart. The pack lives on `main`; specific
warehouses live elsewhere.

The governance contract is `SPEC.md`. Read it before making decisions about
gate behavior, lifecycle, or artifact format.

## The lifecycle, in one paragraph

A new mart starts with `/source-discovery`, which produces a verified
`source_catalog.json`. `/mart-brd` turns that into a signed Business
Requirements Document. `/mart-tdd` turns the signed BRD into a signed
Technical Design Document. `/mart-bootstrap` turns the signed TDD into a
dbt project (ODS → DIM → DWD → DWS → ADS), seeds, tests, and a dashboard.
`/mart-dqc` runs the tests and generates a scorecard. `/mart-review` grades
the result. Each arrow is a hard gate — no skipping.

## The non-negotiable rules

1. **No scaffold without a signed TDD.** No TDD without a signed BRD. No
   BRD without verified source bindings. The skills enforce this; do not
   route around them.
2. **Source-native preference.** If a provider exposes a metric directly,
   ingest it as a pass-through field. Compute only what no provider offers
   natively.
3. **Honest labels.** Every metric on every dashboard carries a status
   badge (`verified`, `proxy`, `stale`, `unsupported`). Silent fixture or
   proxy substitution is a CI-blocking defect.
4. **Real dogfood only.** Every entry in `.skill-invocations.jsonl` records
   an actual skill run. If a skill cannot be invoked in the current
   environment, document the gap in the active exec-plan — do not write
   `"reconstructed": true`.
5. **Public repo discipline.** This is a public, MIT-licensed repository.
   Operator-private data, private file paths, and internal project names
   must never appear. `scripts/confidentiality_scan.py` blocks the commit.

## Table of contents

| File | What it covers |
|------|----------------|
| `SPEC.md` | Full governance contract: lifecycle, gates, artifacts, quality rubric |
| `ARCHITECTURE.md` | What the framework is made of and how the pieces fit |
| `DESIGN.md` | Design principles (boring tech, source-native, single living spec) |
| `METHODOLOGY.md` | Generic Kimball 4-tier methodology reference |
| `RELIABILITY.md` | How the framework stays trustworthy (linters, CI, tests) |
| `SECURITY.md` | Confidentiality boundary, sanitization rules, secret handling |
| `QUALITY_SCORE.md` | Per-skill and per-template quality grades |
| `PLANS.md` | Active exec-plans (in-flight tickets) and completed ones |

## Agent coordination

| File | What it covers |
|------|----------------|
| `.claude/skills/` | Symlinks → `./skills/{group}/{name}` (local-dev mirror; auto-loaded by Claude Code) |
| `./skills/` | Source of truth: 21 skills in 4 groups (lifecycle, workflow, duckdb, quality) |
| `.claude-plugin/marketplace.json` | Marketplace manifest — installs by plugin group |
| `.claude/settings.json` | Hooks and permissions |
| `.claude/worktree_init.sh` | Worktree primitive (used by `/pull`, `/push`) |
| `docs/design-docs/0001-skill-contract.md` | What a SKILL.md must contain |

## When you start a session

1. Read this file (you are doing that now).
2. Read `SPEC.md` if you have not seen it this session, or you are about
   to touch gate behavior or artifact format.
3. Read the active exec-plan at the top of `PLANS.md`.
4. If you do not know which skill to run, run `/using-mart-forge` — it
   inspects the project state and routes you.

## When you end a session

1. Update the exec-plan you worked on under `docs/exec-plans/active/`.
2. If a plan finished, move it to `docs/exec-plans/completed/` and remove
   it from `PLANS.md`.
3. If you invoked a skill, the skill itself wrote a line to
   `.skill-invocations.jsonl` — verify it landed.

## Words to avoid

The confidentiality scanner blocks a defined set of strings (see
`SECURITY.md`). The scanner is the source of truth — this list is a
reminder, not a substitute. If you find yourself about to type a private
project name, an operator codename, or a private file path, stop and ask.
