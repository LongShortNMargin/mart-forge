# mart-forge

Methodology-first, agent-executable specification for scaffolding and reviewing
Kimball data warehouses. See SPEC.md for the full governance contract.

## Principles (Karpathy)

1. **Think Before Coding** — clarify before implementing.
2. **Simplicity First** — minimum code that solves the problem.
3. **Surgical Changes** — touch only what you must.
4. **Goal-Driven Execution** — define success criteria, loop until verified.

## Lifecycle

```
source-discovery → BRD → sign-off → TDD → sign-off → scaffold → DQC → dashboard
```

No scaffold without signed TDD. No TDD without signed BRD.

## Agent Coordination

@.claude/docs/coordination-rules.md

## Technical Preferences

@.claude/docs/technical-preferences.md

## First Session?

Run `/source-discovery` with your stakeholder document to begin.
