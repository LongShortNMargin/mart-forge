# Agent Orchestration Specification

## Design Principle

The issue tracker is the control plane. Agents pull work from issues, produce artifacts, and humans review. Inspired by the pattern where structured methodology guides agent behavior through enforceable gates.

## Agent Roles

### Builder Agent
- Reads `mart.yml` + methodology docs
- Scaffolds the full layer stack (ODS → DIM → DWD → DWS → ADS)
- Writes dbt tests (generic + singular)
- Configures pipeline (GitHub Actions)
- Delivers: git branch + PR

### Reviewer Agent
- Adversarial posture — assumes the builder's code has bugs
- Audits: DAG refresh order, idempotency, NULL propagation, boundary conditions, schema drift resilience
- Validates: DQC coverage, naming convention compliance, grain correctness
- Delivers: review markdown with severity-ranked findings

## Quality Gates

Each gate produces a machine-readable artifact. Gates are enforced by CI (automated) or issue tracker (human-verified).

| Gate | Required Artifact | Enforced By |
|------|-------------------|-------------|
| G1: Scaffold complete | All model files exist | CI (file check) |
| G2: Tests pass | `dbt test` exit 0 + `run_results.json` | CI (GitHub Actions) |
| G3: DQC scorecard green | `dqc_scorecard.json` all controls pass | CI (scorecard validator) |
| G4: Review clean | `review_report.json` with max_severity ≤ medium | Reviewer agent |
| G5: Human approval | PR approved | GitHub PR review |

## Issue Lifecycle

```
todo ──[dispatch]──► in_progress ──[agent done]──► in_review ──[approved]──► done
```

**Key constraint:** Agents never self-promote past `in_review`. Human gate on final approval.

## Transition Preconditions

- `in_progress → in_review`: G1 + G2 + G3 artifacts present
- `in_review → done`: G4 + G5 satisfied

## Promotion Rule

An issue cannot move to `done` unless both G3 scorecard and G4 review report are attached.

## Skill Dispatch

The `using-mart-forge` session bootstrap detects the current phase and routes to the appropriate skill:

```
Phase A → mart-brd (BRD generation)
Phase B → mart-tdd (TDD generation)
Phase C → mart-bootstrap (scaffold)
Phase D → mart-dqc (DQC generation + scorecard)
Phase E → dashboard (presentation)
Review  → mart-review (readiness assessment)
```

Hard gates between phases prevent premature advancement.
