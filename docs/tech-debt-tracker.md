# Technical Debt Tracker

A registry of known compromises and the trigger that should force them
to be paid down.

Each entry: ID, summary, why-it-exists, trigger-to-fix, owner.

## TD-001 — Skill testing framework runs static checks only

**Summary.** `tests/skill-testing/` covers static structural validation
(every spec file has the required sections, every catalog entry resolves
to a spec). Full behavioral runs that drive a skill end-to-end and
assert against the produced artifact are not yet wired into CI.

**Why.** End-to-end skill runs require a Claude Code (or equivalent
agent runtime) inside CI, which is environment-heavy. The static checks
already catch the spec-level defects observed in prior iterations
(missing acceptance criteria, missing adversarial probes).

**Trigger to fix.** Once a CI-friendly agent runtime is available (or
when a recurring class of bug escapes the static checks), wire
behavioral runs in.

**Owner.** Framework maintainers.

## TD-002 — `lint_docs_freshness.py` uses mtime-based heuristics

**Summary.** The freshness linter flags docs whose mtime is older than
the spec by more than a threshold. On a fresh git clone, all mtimes
collapse to the checkout time, so the heuristic is silent in CI.

**Why.** True freshness tracking requires either git log archeology
(slow) or a manifest file tracked alongside docs (extra bookkeeping).
The mtime heuristic is correct on developer machines, where it matters
most.

**Trigger to fix.** If a stale doc lands on `main` and the linter does
not catch it, replace the heuristic with `git log -1 --format=%ct
<path>` and the spec's last-modified timestamp.

**Owner.** Framework maintainers.

## TD-003 — Provider abstraction is documentation-only

**Summary.** `docs/provider-abstraction.md` describes the contract a
provider must meet but does not provide a runtime adapter layer.

**Why.** A runtime layer would add a second mental model on top of dbt
(see `DESIGN.md` §2 — boring tech). The contract is enforced at the
ODS-spec level instead.

**Trigger to fix.** If multiple marts repeatedly write near-identical
adapter code, extract the common shape into a helper module (not a
framework).

**Owner.** Framework maintainers.

## TD-004 — `schema-evolve` skill has no behavioral coverage

**Summary.** `/schema-evolve` is specified but has only a static spec
in `tests/skill-testing/specs/`. There is no behavioral test driving a
column-addition end-to-end.

**Why.** Schema evolution requires a real prior mart to evolve, which
is deferred to the conformance dispatch.

**Trigger to fix.** First conformance mart that needs a column added.

**Owner.** Maintainer of `schema-evolve`.

## TD-005 — Dashboard live-mode connection is per-install

**Summary.** `templates/dashboard/app.py` ships with a fixture-mode
connection. The live-mode connection (to a hosted warehouse) requires
an environment variable (e.g., `MOTHERDUCK_TOKEN`). There is no shared
secret in the repo.

**Why.** Secrets must never be committed (`SECURITY.md`). Live-mode is
intentionally per-install.

**Trigger to fix.** Not a fix — this is the correct shape. The entry
exists so the gap is visible.

**Owner.** Per-install operator.

## TD-006 — `validate_dogfood` is a coherence gate, not invocation proof

**Summary.** `scripts/validate_dogfood.py --check-semantics` verifies
that `.skill-invocations.jsonl` entries are structurally well-formed:
the `skill_name` exists in the on-disk catalog, the artifact paths or
refs resolve, the timestamp parses and is not in the future, input and
output artifacts are distinct, and when `output_artifact` is a git SHA
the commit must touch `input_artifact`. The gate does NOT prove the
named skill actually ran — an operator can pick two distinct existing
repo paths (or a historical SHA that touched the named input) and the
entry will pass.

**Why.** Real invocation proof requires the agent runtime to write the
log itself, contemporaneous with the call. After-the-fact entries
authored by any actor can only ever be checked for coherence. The
round-3 reviewer (EMB-322, 2026-06-01) reproduced the path-vs-path
shape (`{input: README.md, output: SPEC.md, skill: mart-brd}` passes)
and the historical-SHA shape (`{output: <real SHA touching README>}`
passes regardless of `skill_name`). The orchestrator's ruling accepted
the gate as coherence-only and tracked the residual gap here.

**Trigger to fix.** Phase G — the conformance-mart dispatch wires a
Claude Code runtime that emits skill invocations directly to the log
file at the moment the skill runs. At that point the validator can
add an "entry was written by the runtime within N seconds of its
recorded timestamp" check, or pivot the schema to require a
runtime-supplied `run_id` that has no off-line bypass.

**Owner.** Framework maintainers / Phase-G dispatcher.
