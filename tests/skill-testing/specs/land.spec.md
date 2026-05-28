# Skill Spec: /land

> **Category:** utility
> **Priority:** high

## Skill Summary

Open a pull request with full description, acceptance criteria
checkboxes, and reviewer assignment.

## Static Assertions

- [ ] Skill runs the local check suite before opening the PR.
- [ ] PR body contains Summary, Acceptance criteria, Test plan, References.
- [ ] Acceptance criteria are checkboxes (matches `pr-description-lint`).
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path

**Fixture:** Branch ahead of `main` with passing local checks.

**Assertions:**
- [ ] PR URL printed.
- [ ] PR body parses with the required headings.

**Case Verdict:** PASS

### Case 2: Dirty worktree -> blocked

**Fixture:** Uncommitted changes present.

**Assertions:**
- [ ] Skill defers to /commit before continuing.

**Case Verdict:** PASS

### Case 3: Adversarial — empty acceptance criteria

**Fixture:** Agent writes a PR body without checkboxes.

**Assertions:**
- [ ] `pr-description-lint.yml` rejects the PR.
- [ ] /land warns before submitting.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] One PR per invocation.
- [ ] Reviewer assigned per dispatch.
- [ ] Skill emits dogfood log entry.

## Coverage Notes

PR shape is enforced server-side by `pr-description-lint.yml`.
