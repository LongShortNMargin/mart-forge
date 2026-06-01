# Skill Spec: /pull

> **Category:** utility
> **Priority:** medium

## Skill Summary

Sync a remote branch into a new isolated worktree. Never modifies an
existing worktree.

## Static Assertions

- [ ] Skill uses `.claude/worktree_init.sh`.
- [ ] Hard gate: existing worktrees are never overwritten.
- [ ] Workflow picks a fresh worktree path if the default is taken.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path

**Fixture:** A remote branch not yet checked out locally.

**Assertions:**
- [ ] New worktree at `../mart-forge-<slug>`.
- [ ] Branch checked out.

**Case Verdict:** PASS

### Case 2: Existing worktree -> new path picked

**Fixture:** Default worktree path is already taken.

**Assertions:**
- [ ] Skill picks `..-2` or similar.
- [ ] Existing worktree untouched.

**Case Verdict:** PASS

### Case 3: Adversarial — agent tries to delete existing worktree

**Fixture:** N/A — the skill never offers this option.

**Assertions:**
- [ ] No `rm -rf` in the workflow.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Never resets / deletes an existing worktree.
- [ ] Skill emits dogfood log entry.

## Coverage Notes

Worktree primitive is in `.claude/worktree_init.sh` (16 lines or fewer).
