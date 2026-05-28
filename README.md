# mart-forge

A methodology-first, agent-executable framework for scaffolding and reviewing
Kimball data warehouses through coordinated AI agents.

mart-forge reads stakeholder requirements, discovers data sources, produces
signed Business Requirements Documents (BRDs) and Technical Design Documents
(TDDs), and generates a complete dbt-duckdb warehouse with tests, a Data
Quality Contract (DQC) scorecard, and a presentation dashboard.

## Status

**v3 first commit** — framework-only. The canonical conformance example
(a working warehouse built end-to-end through the framework's own skills)
is intentionally deferred to a follow-up dispatch so this commit can be
reviewed as a pure framework artifact. See `docs/exec-plans/active/0001-first-commit-build-log.md`
for what is and is not included.

## What this is

- A **specification** (`SPEC.md`) that defines the lifecycle, gates, artifacts,
  and quality rubric for any Kimball warehouse mart-forge produces.
- A set of **methodology skills** (`.claude/skills/`) — `source-discovery`,
  `mart-brd`, `mart-tdd`, `mart-bootstrap`, `mart-dqc`, `mart-review`,
  `schema-evolve`, `using-mart-forge` — that translate the spec into
  agent-executable phases with hard gates between them.
- A set of **lifecycle skills** (`commit`, `debug`, `land`, `pull`, `push`,
  `linear`) borrowed from the Symphony pattern to standardize how agents
  iterate on the warehouse itself.
- **Templates** for every artifact: BRD, TDD, `mart.yml`, per-layer SQL,
  seeds, tests, dashboards, CI pipelines.
- **Linters with teeth** (`scripts/`): BRD structure linter, TDD structure
  linter, ODS->DIM->DWD->DWS->ADS layer-direction enforcer, dogfood-log
  validator, confidentiality scanner, and docs-freshness checker. Every
  linter has adversarial probe tests (`tests/`) that exercise the
  bypass cases.
- A **Skill Testing Framework** (`tests/skill-testing/`) with a catalog,
  quality rubric, and per-skill behavioral specs.

## What this is not

- This is **not** a hosted SaaS product. It is a framework you clone and
  drive locally through Claude Code or a compatible agent runtime.
- This is **not** a published Python package on PyPI. There is no
  `pip install mart-forge`. Install instructions are below.
- This is **not** a dbt fork or competitor. mart-forge uses dbt as the
  transform engine.
- This is **not** opinionated about which cloud warehouse you target.
  The reference implementation is dbt-duckdb + MotherDuck because the
  reference example runs on it; other adapters are out of scope for v3.

## Install

mart-forge ships as a Claude Code plugin plus a small Python package for
the linters and CLI scripts. To use it:

```bash
git clone <this-repository> mart-forge
cd mart-forge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

If you use Claude Code, the `.claude-plugin/plugin.json` manifest registers
the skills automatically when you open the repository in an agent session.
If you do not use Claude Code, the methodology in `SPEC.md`, the templates
under `templates/`, and the linters under `scripts/` are still useful by
themselves — they encode the contract you would otherwise have to enforce
by hand.

## Quick start

A typical first-time session looks like this:

```text
1. Drop your stakeholder document (PDF, markdown, or transcript) into the
   working directory.
2. Run /source-discovery   — produces docs/source_catalog.json.
3. Run /mart-brd            — produces docs/business-requirements.md.
                              Stakeholder signs the signature block.
4. Run /mart-tdd            — produces docs/tech-design-doc.md.
                              Engineering owner signs the signature block.
5. Run /mart-bootstrap      — produces the dbt project under models/, seeds/,
                              tests/, dashboard/.
6. Run /mart-dqc            — runs dbt test and generates dqc_scorecard.json.
7. Run /mart-review         — produces a readiness verdict.
```

Each skill enforces a hard gate against the artifact produced by the previous
one. You cannot scaffold without a signed TDD. You cannot write a TDD without
a signed BRD. You cannot sign a BRD without verified source bindings.

## Layout

```
mart-forge/
├── SPEC.md                    Specification (governance contract)
├── CLAUDE.md                  Onboarding for agent sessions
├── ARCHITECTURE.md            What the framework is made of
├── DESIGN.md                  Design principles
├── METHODOLOGY.md             Generic Kimball lifecycle
├── RELIABILITY.md             How the framework stays trustworthy
├── SECURITY.md                Confidentiality, sanitization, secrets
├── QUALITY_SCORE.md           Per-skill quality grades
├── PLANS.md                   Active exec-plans index
├── .claude/                   Skills, settings, worktree init
├── .claude-plugin/            Plugin manifest
├── .github/workflows/         CI: linters + pytest + PR description lint
├── docs/                      Design docs, references, methodology subdocs
├── scripts/                   Linters with teeth (each with adversarial tests)
├── templates/                 BRD, TDD, mart.yml, per-layer SQL, dashboard
└── tests/                     pytest suite + skill-testing framework
```

## Contributing

mart-forge is built and maintained by agents working through a hard-gated
lifecycle of its own. Human contributions follow the same process:

1. Open an issue describing the change and its scope.
2. Branch from `main`.
3. Run the local lint + test suite (`make check` or, if Make is absent,
   `python -m pytest tests/ && python scripts/confidentiality_scan.py .`).
4. Open a PR. CI must pass before review.

See `RELIABILITY.md` for the full set of checks and `SECURITY.md` for what
must never appear in a public commit.

## License

MIT — see `LICENSE`.
