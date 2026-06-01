# Skill Spec: /commit

> **Category:** utility
> **Priority:** high

## Skill Summary

Produce a single atomic commit with verifiable message after a local
green check.

## Static Assertions

- [ ] Skill declares single-purpose (one atomic commit).
- [ ] Workflow runs the full local check suite before committing.
- [ ] Workflow stages files explicitly (no `git add -A`).
- [ ] Workflow rejects amending.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path

**Fixture:** A clean worktree with one logical change.

**Assertions:**
- [ ] Local checks run.
- [ ] One commit created.
- [ ] Commit message follows `<type>: <summary>` format.

**Case Verdict:** PASS

### Case 2: Local check fails -> commit blocked

**Fixture:** Pending change has a confidentiality violation.

**Assertions:**
- [ ] No commit created.
- [ ] Output names the failing check.

**Case Verdict:** PASS

### Case 3: Adversarial — mixed logical units

**Fixture:** Working tree has changes spanning two unrelated features.

**Assertions:**
- [ ] Skill stops and asks how to split.
- [ ] No commit created without user input.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] One commit per invocation.
- [ ] Never `--amend`.
- [ ] Never `git add -A`.
- [ ] Skill emits dogfood log entry.

## Coverage Notes

This is a thin wrapper; behavioral verification is the local check
suite itself.
