# Skill Spec: /push

> **Category:** utility
> **Priority:** medium

## Skill Summary

Push a worktree to its remote. Refuses to push to `main`. Refuses
force-push without operator authorization.

## Static Assertions

- [ ] Hard gate: never push to `main`.
- [ ] Hard gate: never force-push without explicit authorization.
- [ ] Workflow uses `--force-with-lease` when force-pushing.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path

**Fixture:** Feature branch with commits ahead of remote.

**Assertions:**
- [ ] `git push` succeeds.
- [ ] Branch tracking set on first push.

**Case Verdict:** PASS

### Case 2: Adversarial — push to main rejected

**Fixture:** Current branch is `main`.

**Assertions:**
- [ ] BLOCKED message printed.
- [ ] No push attempted.

**Case Verdict:** PASS

### Case 3: Adversarial — force without lease rejected

**Fixture:** Agent tries `--force` without operator authorization.

**Assertions:**
- [ ] Skill refuses; offers `--force-with-lease` only with explicit
  operator instruction.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Branch protection awareness.
- [ ] Skill emits dogfood log entry.

## Coverage Notes

Branch protection is enforced server-side; this skill's role is to
keep the agent from learning the wrong default.
