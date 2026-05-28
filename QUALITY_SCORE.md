# Quality Score

A self-assessed grade for every skill and template in this commit. The
purpose is to make trade-offs visible: a grade-B skill is still
shippable if the grade-B label is explicit and the gap is documented.

Grades:

- **A** — Production-ready. Behavioral spec passes, adversarial probes
  covered, error messages include remediation, edge cases handled.
- **B** — Shippable with documented gap. Happy path tested, at least
  one adversarial probe, gap noted in this file.
- **C** — Functional but unverified. No adversarial coverage yet.
- **D** — Skeleton only. Schema present, behavior incomplete.

## Methodology skills

| Skill | Grade | Gap |
|-------|-------|-----|
| `using-mart-forge` | B | Router logic verified by static check; behavioral spec covers happy path only — corruption of `mart.yml` is not yet a covered failure mode. |
| `source-discovery` | B | Five-point verification logic specified; the actual provider-reach test is environment-dependent and not yet covered by an adversarial probe. |
| `mart-brd` | A | Linter covers structural validation and bypass cases (missing section, missing field, bogus link_status). Skill enforces signed-BRD gate. |
| `mart-tdd` | A | Linter covers all 21 sections plus T-8 column-row validation plus T-9 ODS contract. Adversarial probe covers prose-in-calculation. |
| `mart-bootstrap` | B | Generates the full scaffold from a signed TDD. Adversarial probe (mismatched TDD vs scaffold) is in scope but not yet implemented end-to-end. |
| `mart-dqc` | B | Reads `target/run_results.json` and writes scorecard; "non-pass never green" rule enforced. Adversarial probe (silent green when test failed) covered by the static schema check. |
| `mart-review` | B | Readiness rubric defined; bidirectional traceability check (BRD -> TDD -> model) implemented; end-to-end pass on a real conformance mart pending Phase G. |
| `schema-evolve` | C | Specifies the contract for adding a column to ODS and propagating to DWD; no test coverage in this commit. |

## Lifecycle skills

| Skill | Grade | Gap |
|-------|-------|-----|
| `commit` | A | Atomic-commit shape verified by static check; commit message convention enforced. |
| `debug` | B | Hypothesis-log discipline specified; no test exercises the loop. |
| `land` | B | PR-open shape verified; PR description acceptance criteria checked by `pr-description-lint.yml`. |
| `pull` | A | Worktree primitive verified; conflict handling specified (never overwrite an existing worktree). |
| `push` | A | Worktree push verified; branch-protection awareness specified. |
| `linear` | B | Issue tracker interface specified; provider-specific bindings (GitHub Issues vs alternatives) deferred to per-installation config. |

## Templates

| Template | Grade | Gap |
|----------|-------|-----|
| `business-requirements.template.md` | A | B-1..B-4 complete, every required field present, validation in `lint_brd.py`. |
| `tech-design-doc.template.md` | A | T-1..T-21 complete, T-8 column format enforced, T-9 ODS contract enforced. |
| `mart.yml.template` | B | Required keys documented; schema validator not yet wired into a skill. |
| `models/ods/template.sql` | A | Pass-through pattern with provenance columns. |
| `models/dim/template.sql` | A | Surrogate key + SCD-type pattern. |
| `models/dwd/template.sql` | A | Business key join pattern with FK integrity hooks. |
| `models/dws/template.sql` | A | Aggregation pattern; separate count vs performance shapes covered. |
| `models/ads/template.sql` | A | One-big-table pattern with link-status columns. |
| `seeds/dim_date.csv` | A | 30 days of dates; extendable. |
| `seeds/raw_sample_data.csv` | A | Generic 10-row sample. |
| `tests/template_singular.sql` | A | Singular test pattern with explicit fail criterion. |
| `dashboard/app.py` | B | Dashboard skeleton with link-status badges; live-mode connection requires a per-install env var. |
| `dashboard/requirements.txt` | A | Minimal deps. |
| `pipeline/daily.yml.template` | A | GitHub Actions workflow with CI-green default. |

## Linters

| Linter | Grade | Gap |
|--------|-------|-----|
| `lint_brd.py` | A | Section presence, per-metric fields, bogus link_status all rejected. Adversarial probes in `test_lint_brd.py`. |
| `lint_tdd.py` | A | All 21 sections, T-8 column rows, T-9 ODS contract, prose-in-calculation all rejected. |
| `lint_layer_direction.py` | A | Upward `ref()` rejected; same-layer references allowed. |
| `validate_dogfood.py` | A | Rejects `"reconstructed": true`. This is the specific defeat for the prior iteration's bypass. |
| `confidentiality_scan.py` | A | Category-based banned strings, self-exclusion, line-by-line reporting. |
| `lint_docs_freshness.py` | B | Cross-link resolution covered; stale-doc detection by mtime is conservative (false positives possible on a fresh clone). |

## Documents

| Document | Grade | Gap |
|----------|-------|-----|
| `SPEC.md` | A | Sixteen sections plus two appendices; refined and public-portable. |
| `CLAUDE.md` | A | 90 lines (cap is 120); table-of-contents pattern; non-negotiable rules explicit. |
| `README.md` | A | Honest install instructions (no PyPI claim, no false dogfood claim). |
| `ARCHITECTURE.md` | A | Subsystem map, data flow, ownership table. |
| `DESIGN.md` | A | Ten principles, each with a failure-mode rationale. |
| `METHODOLOGY.md` | A | Lifecycle phases summarized; SPEC referenced for enforcement. |
| `RELIABILITY.md` | A | Verification stack, CI flow, local equivalence documented. |
| `SECURITY.md` | A | Categories, banned-string source-of-truth, secret-handling, incident response. |
| `PLANS.md` | A | Active exec-plan index. |
