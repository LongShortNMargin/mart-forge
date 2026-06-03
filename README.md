# mart-forge

**Claude Code plugin pack for lifecycle-first Kimball data warehouses.**

mart-forge is a marketplace plugin pack: four installable plugins covering
the phased Kimball lifecycle, splitted into industrial standard process through gated artifacts (Business Requirement Document (BRD) → Technical Design Document (TDD) → scaffold → Data Quality Check), Git workflow
plumbing, a DuckDB / MotherDuck warehouse track, and a quality / signing
gate layer. It is a peer to `AltimateAI/data-engineering-skills` — that
pack focuses on dbt and Snowflake skill primitives; this pack covers the
complementary methodology layer (signed lifecycle artifacts, eight-control
DQC, naming and grain discipline) and the DuckDB warehouse track that the
AltimateAI pack does not cover today.

## Install (Claude Code)

```bash
/plugin marketplace add LongShortNMargin/mart-forge
/plugin install mart-forge-lifecycle@mart-forge
/plugin install mart-forge-workflow@mart-forge
/plugin install mart-forge-duckdb@mart-forge
/plugin install mart-forge-quality@mart-forge
```

Each plugin is independently installable. Most teams want
`mart-forge-lifecycle` + `mart-forge-quality` at minimum; add
`mart-forge-duckdb` if your warehouse runs on DuckDB / MotherDuck.

The manifest lives at `.claude-plugin/marketplace.json`. The four plugins
are:

| Plugin                 | Skills                                                                                                            |
|------------------------|-------------------------------------------------------------------------------------------------------------------|
| `mart-forge-lifecycle` | `source-discovery`, `mart-brd`, `mart-tdd`, `mart-bootstrap`, `mart-dqc`, `mart-review`, `schema-evolve`, `using-mart-forge` |
| `mart-forge-workflow`  | `commit`, `debug`, `land`, `linear`, `pull`, `push`                                                               |
| `mart-forge-duckdb`    | `creating-duckdb-mart`, `motherduck-deploy`, `duckdb-incremental-models`                                          |
| `mart-forge-quality`   | `8-control-dqc-audit`, `naming-conventions-lint`, `grain-rules-check`, `signing-enforcement`                      |

## What this pack is

- A **specification** (`SPEC.md`) that defines the lifecycle, gates,
  artifacts, and quality rubric for any Kimball warehouse mart-forge
  produces.
- A set of **methodology skills** under `./skills/lifecycle/` that
  translate the spec into agent-executable phases with hard signing
  gates between them.
- **Workflow skills** under `./skills/workflow/` for the git / tracker
  plumbing that every long-running mart needs.
- A **DuckDB warehouse track** under `./skills/duckdb/` for incremental
  models, MotherDuck deployment, and partition / backfill protocols.
- A **quality + gates track** under `./skills/quality/` for the
  eight-control DQC catalog, naming conventions, grain discipline, and
  the signing gates that the lifecycle relies on.
- **Templates** for every artifact: BRD, TDD, `mart.yml`, per-layer
  SQL, seeds, tests, dashboards, CI pipelines.
- **Linters with teeth** under `scripts/`: BRD structure linter (with
  per-row source-binding check), TDD structure linter, layer-direction
  enforcer, dogfood-log semantic validator, confidentiality scanner
  (allow-listed dot-dir traversal), signing-gate linters for BRD and
  TDD, marketplace-manifest validator. Every linter has adversarial
  probe tests in `tests/`.

## Quick start (after install)

```text
1. Drop your stakeholder document (PDF, markdown, transcript) into the
   working directory.
2. Invoke /source-discovery   — produces docs/source_catalog.json.
3. Invoke /mart-brd           — produces docs/business-requirements.md.
                                Stakeholder signs the signature block.
4. Invoke /mart-tdd           — gated on a signed BRD.
                                Engineering owner signs the signature block.
5. Invoke /mart-bootstrap     — gated on a signed TDD; produces the dbt
                                project (models, seeds, tests, dashboard).
6. Invoke /mart-dqc           — runs dbt test and writes dqc_scorecard.json.
7. Invoke /8-control-dqc-audit — audits the scorecard against the eight
                                control classes; emits the gap report.
8. Invoke /mart-review        — produces a readiness verdict.
```

Each arrow is enforced by code, not prose. `scripts/lint_signed_brd.py`
and `scripts/lint_signed_tdd.py` block the next phase when a signature
is missing.

## Local development

Clone the repository and run the local linter + test suite:

```bash
git clone https://github.com/LongShortNMargin/mart-forge
cd mart-forge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/run_all_lints.py     # the umbrella check
pytest tests/
```

`.claude/skills/` is a generated mirror of `./skills/{group}/{name}/`
(symlinks committed to the repo) so Claude Code's per-repo skill
auto-load picks the same skills the marketplace ships. See
`DESIGN.md` for why both shapes exist.

## Layout

```
mart-forge/
├── SPEC.md                       Specification (governance contract)
├── CLAUDE.md                     Onboarding for agent sessions
├── ARCHITECTURE.md               What the pack is made of
├── DESIGN.md                     Design principles + symlink rationale
├── METHODOLOGY.md                Generic Kimball lifecycle
├── RELIABILITY.md                How the pack stays trustworthy
├── SECURITY.md                   Confidentiality, sanitization, secrets
├── QUALITY_SCORE.md              Per-skill quality grades
├── MARKETPLACE.md                Submission tracking + clau.de checklist
├── PLANS.md                      Active exec-plans index
├── .claude/skills/               Symlinks → ./skills/{group}/{name} (local-dev mirror)
├── .claude-plugin/
│   └── marketplace.json          Marketplace manifest (4 plugins)
├── .github/workflows/            CI: linters + pytest + adversarial probes
├── skills/
│   ├── lifecycle/                Phase A0 → DQC review (8 skills)
│   ├── workflow/                 Git + tracker plumbing (6 skills)
│   ├── duckdb/                   DuckDB / MotherDuck (3 skills)
│   └── quality/                  DQC + naming + grain + signing (4 skills)
├── docs/                         Design docs, references, methodology subdocs
├── scripts/                      Linters with adversarial tests
├── templates/                    BRD, TDD, mart.yml, per-layer SQL, dashboard
└── tests/                        pytest suite + skill-testing framework
```

## Contributing

mart-forge is built and maintained by agents working through a
hard-gated lifecycle of its own. Human contributions follow the same
process:

1. Open an issue describing the change and its scope.
2. Branch from `main`.
3. Run the local lint + test suite (`python scripts/run_all_lints.py &&
   pytest tests/`).
4. Open a PR. CI must pass before review.

See `RELIABILITY.md` for the full set of checks and `SECURITY.md` for
what must never appear in a public commit. See `MARKETPLACE.md` for the
submission checklist if you want to publish a derivative pack.

## License

MIT — see `LICENSE`.
