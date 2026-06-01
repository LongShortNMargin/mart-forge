# Design Principles

The principles below are why mart-forge looks the way it does. They are
not negotiable preferences — each one closes a specific failure mode
observed in a prior iteration.

## 1. Source-native preference

When a data provider exposes a metric directly, ingest it as a
pass-through field. Compute derived metrics only when no provider offers
the metric natively.

**Why.** Computation introduces drift from authoritative sources, and
every formula becomes a maintenance liability. A native field that you
pass through is wrong only when the provider is wrong; a derived field
can be wrong because the provider is wrong *or* because your formula
is wrong, and you cannot tell which without re-deriving from first
principles every time something looks off.

**How enforced.** The `mart-tdd` skill requires `calculation` for native
columns to read `pass-through from <provider.field>`. The linter
rejects "derived", "computed", "see model", or any other prose where
SQL belongs.

## 2. Boring tech

mart-forge uses dbt, DuckDB, and Streamlit (or a dashboard equivalent).
It does not use a new query language, a new orchestration framework, or
a new test runner. It does not introduce abstractions over dbt that
require an agent to think in two layers.

**Why.** The user of mart-forge is a data engineer with industry skills,
not a framework user with mart-forge-specific skills. Boring tech
maximizes the overlap.

**How enforced.** Provider abstractions live in `docs/provider-abstraction.md`
as a deliberate seam, not as a runtime layer. Templates are stock
dbt, not a wrapper DSL.

## 3. Single living spec

There is one specification, `SPEC.md`. Versioned, feedback-suffixed,
and iteration-suffixed copies are forbidden — the freshness linter
rejects them by regex. Version history lives in git.

**Why.** Filename proliferation is the symptom of an unwilling editor.
Every spec branch that survives is a contract the agent has to honor;
every dead spec branch is a hazard.

**How enforced.** `lint_docs_freshness.py` rejects dangling references
to spec filenames other than `SPEC.md`.

## 4. Incremental checkpoint delivery

Each lifecycle phase merges a reviewable artifact to `main`. Intermediate
checkpoints represent saved-states, not success states.

**Why.** Prior iterations shielded all delivery behind prerequisite gates,
and `main` stayed empty while feature branches accumulated. A reviewer
could not tell whether progress was 20% or 90%, and an agent could not
recover from a multi-branch context loss without help.

**How enforced.** The lifecycle skills each end at a single checkpoint
PR. The `commit`, `land`, and `push` lifecycle skills assume one
reviewable change per invocation.

## 5. Hard gates, no waivers without ledger

No scaffold without a signed TDD. No TDD without a signed BRD. No BRD
without verified source bindings. A gate may only be waived through an
explicit Classification Ledger entry recorded by the orchestrator.

**Why.** The agent's natural bias is to ship implementation. Without
gates, design becomes vestigial. With gates and no ledger, the agent
simply learns which incantation makes the gate yield.

**How enforced.** Each skill that depends on a prior artifact begins
with a precondition check. The check fails closed if the artifact is
absent or unsigned.

## 6. Honest labels on every surface

Every metric on every dashboard carries a status badge:
`verified`, `proxy`, `stale`, or `unsupported`. Silent fixture
substitution and silent proxy substitution are CI-blocking defects.

**Why.** A trustworthy system that lies once is no longer trustworthy.
Downstream consumers calibrate on what they see; the moment a
dashboard renders a fixture value with a "verified" badge, every
prior interpretation becomes suspect.

**How enforced.** `G-HONEST-LABEL` (see SPEC §9) gates the dashboard.
The dashboard template emits the badge component inline with every
metric value; removing it triggers a CI failure.

## 7. Real dogfood or none

Every entry in `.skill-invocations.jsonl` records an actual skill run.
If a skill cannot be invoked in the current environment, the gap is
documented in the active exec-plan — it is not fabricated.

**Why.** Prior iterations recorded `"reconstructed": true` entries in
the dogfood log to pass CI without having actually invoked the skills.
The framework was untested in the very loop that was supposed to prove
it. The fix is to enforce that the log entry can only come from a real
invocation, and to delete or block any other shape.

**How enforced.** `validate_dogfood.py` rejects any entry containing
`"reconstructed": true`. The accompanying adversarial test
(`test_validate_dogfood.py::test_rejects_reconstructed_entry`) exists
specifically to defeat the prior bypass.

With `--check-semantics` the validator also runs a **coherence check**:
the `skill_name` must exist in the on-disk catalog, artifacts must
resolve as paths or git refs, timestamps must parse and not be in the
future, input and output artifacts must differ, and a SHA-typed
`output_artifact` must touch the path named in `input_artifact`. This
is a coherence gate, not invocation proof — an after-the-fact author
can still pick two distinct existing files and pass the check. That
residual gap is recorded under `TD-006` in
`docs/tech-debt-tracker.md` and is the Phase-G runtime concern.

## 8. Confidentiality is part of correctness

The repository is public. Operator-private data, private file paths,
and internal project names are CI-blocking defects, not style issues.

**Why.** A leak in a public framework is unrecoverable — search engines
and downstream forks make removal impossible.

**How enforced.** `confidentiality_scan.py` runs on every PR. The banned
string list is the policy; `SECURITY.md` documents the categories.

## 9. Linters with teeth

Every linter rejects bypass inputs, not just well-formed inputs that
happen to be wrong. Every linter has an adversarial probe test.

**Why.** A linter that only catches honest mistakes will catch fewer
mistakes over time as the agent learns which honest-looking inputs
sail through. A linter that catches deliberate bypasses scales with
adversarial pressure.

**How enforced.** For every `scripts/lint_*.py`, there is a
`tests/test_lint_*.py` with a test class named `class TestAdversarial`
that exercises bypass cases.

## 10. Marketplace shape with a local-dev mirror

mart-forge ships as a Claude Code marketplace plugin pack:
`.claude-plugin/marketplace.json` declares four plugins, each pointing
into `./skills/{group}/{name}/`. The lifecycle / workflow / duckdb /
quality split is for installability — a team can pull only the layers
it needs.

For local development against the repo itself (i.e., agents working on
mart-forge), `.claude/skills/<name>/` is a tree of **symlinks** into
`./skills/{group}/{name}/`. Claude Code's per-repo skill auto-load
walks `.claude/skills/`, and the symlinks make it see the same skills
the marketplace ships.

**Why two shapes.** The marketplace consumer wants logical groupings
(lifecycle vs. workflow vs. duckdb vs. quality) so they can install
subsets. The per-repo Claude Code agent does not care about grouping —
it just wants a flat list of invocable skills. The symlink mirror is
the cheapest way to satisfy both without duplication.

**Source of truth.** `./skills/{group}/{name}/` is the source of truth.
`.claude/skills/<name>/` is generated. If a skill is added or moved,
update the marketplace.json and re-create the symlink. The committed
symlinks survive `git clone` on macOS / Linux. On Windows, run
`python scripts/sync_local_skills.py` (a helper that recreates the
mirror) — symbolic-link permissions there are not always available.

**How enforced.** `scripts/validate_marketplace.py` walks the manifest
and checks every skill path resolves to a directory containing a valid
`SKILL.md`. The pytest suite asserts the manifest declares exactly
four plugins and the skill count matches the on-disk tree.

`scripts/sync_local_skills.py --check` (also wired into CI) detects
drift between the manifest and the `.claude/skills/` mirror: a missing
symlink, an unexpected entry, a real directory where a symlink belongs,
or a symlink pointing at the wrong target all exit 1. This prevents the
two surfaces from diverging if a PR edits `marketplace.json` without
re-running the sync helper.

`sync_local_skills.py` refuses to delete a non-symlink directory under
`.claude/skills/<name>/` unless `--force` is passed; the warning prints
the path being clobbered. This protects users on Windows or zip-
extracted clones who may have authored real content there.

## 11. Custom error messages include remediation

When a linter fails, the error message names the file, the location,
the rule, and the fix — usually with a pointer to the template that
specifies the correct shape.

**Why.** A linter that says "TDD §T-9 is malformed" forces the agent
to read the SPEC, recall what T-9 contains, locate the file, and
guess at the fix. A linter that says "TDD §T-9 missing required field
`provenance_columns`; add per template at
`templates/tech-design-doc.template.md:118`" closes the loop in one
read.

**How enforced.** Linter unit tests assert error messages contain
remediation tokens (file path, line number, or template reference).
