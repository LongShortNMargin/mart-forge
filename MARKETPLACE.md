# MARKETPLACE.md — Submission tracking

This file tracks the path of mart-forge into the Claude Code plugin
directory. The submission itself is an operator action (the operator
owns the GitHub identity that submits to the directory); this file
captures the readiness checklist and any in-flight submissions.

## Submission target

**Primary:** `anthropics/claude-plugins-community`
**Submission URL:** `clau.de/plugin-directory-submission`
**Promotion path:** community → official (`anthropics/claude-plugins-official`)
once the pack has demonstrated stable usage in the community marketplace.

## Pre-submission checklist

A submission is ready when every box below is checked.

### Manifest

- [x] `.claude-plugin/marketplace.json` parses as JSON.
- [x] Manifest declares **4 plugins**: `mart-forge-lifecycle`,
      `mart-forge-workflow`, `mart-forge-duckdb`, `mart-forge-quality`.
- [x] Every plugin lists at least one skill.
- [x] Every skill path resolves to a directory containing a `SKILL.md`
      with valid YAML frontmatter (`name:` + `description:`).
- [x] `scripts/validate_marketplace.py` exits 0 on the manifest.

### Skill coverage

- [x] `./skills/lifecycle/` — 8 skills (source-discovery, mart-brd,
      mart-tdd, mart-bootstrap, mart-dqc, mart-review, schema-evolve,
      using-mart-forge).
- [x] `./skills/workflow/` — 6 skills (commit, debug, land, linear,
      pull, push).
- [x] `./skills/duckdb/` — 3 skills (creating-duckdb-mart,
      motherduck-deploy, duckdb-incremental-models).
- [x] `./skills/quality/` — 4 skills (8-control-dqc-audit,
      naming-conventions-lint, grain-rules-check, signing-enforcement).
- [x] **Total: 21 skills** (matches AC#2 of EMB-322).

### Confidentiality

- [x] `scripts/confidentiality_scan.py` walks `.claude/`,
      `.claude-plugin/`, `.github/`, `./skills/` (the dot-dir bypass
      from EMB-321 finding #1 is closed).
- [x] `EXCLUDED_PATHS` matches by relative path, not basename
      (EMB-321 finding #9 is closed).
- [x] The scanner exits 0 on the full tree.

### Dogfood + signing gates

- [x] `.skill-invocations.jsonl` schema is validated by
      `scripts/validate_dogfood.py` with `--require-non-empty` and
      `--check-semantics` wired into CI.
- [x] `scripts/lint_signed_brd.py` + `scripts/lint_signed_tdd.py`
      block any unsigned BRD/TDD from sliding into a merge.

### CI

- [x] `.github/workflows/framework-ci.yml` runs:
  - `validate_marketplace.py`
  - `confidentiality_scan.py`
  - `lint_brd.py` (template)
  - `lint_tdd.py` (template)
  - `lint_layer_direction.py`
  - `validate_dogfood.py --require-non-empty --check-semantics`
  - `lint_signed_brd.py` (audit mode on docs/)
  - `lint_signed_tdd.py` (audit mode on docs/)
  - `lint_docs_freshness.py`
  - `pytest tests/`

### Public-repo hygiene

- [x] `LICENSE` is MIT and present.
- [x] `README.md` leads with the marketplace install command.
- [x] No `pip install mart-forge` claim (the pack is not on PyPI).
- [x] No "framework" framing in the top of `README.md` (positioned as
      a plugin pack).
- [x] No banned strings: third-party company names, internal program
      codenames, private operator handles, or repo-org strings. The
      authoritative pattern list lives in `scripts/confidentiality_scan.py`;
      a green run of that scanner is the proof.

## Submission steps

When every box above is checked:

1. Tag the release commit (`v3.0.0` or whatever the next semver is).
2. Open a PR against `anthropics/claude-plugins-community` adding
   `your-mart-org/mart-forge` to the community directory file.
3. Reference the tag in the PR description.
4. Wait for the community reviewer.
5. After merge, post the install commands in the project README's
   "Install" section (already pre-staged in `README.md`).

## In-flight submissions

| Date | Target | PR / URL | Status |
|------|--------|----------|--------|
|      |        |          |        |

Operator: please record each submission here.

## Post-submission

- Watch for downstream community feedback on the four plugins.
- Triage findings into the EMB-32x ticket line, not into ad-hoc patches.
- Any incompatible change requires a new major version + a deprecation
  notice in this file.
