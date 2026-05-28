# Skill Spec: /linear

> **Category:** utility
> **Priority:** medium

## Skill Summary

Operate on the issue tracker bound to the mart. Subcommands: read,
comment, status, comments.

## Static Assertions

- [ ] Skill reads `issue_tracker` block from `mart.yml`.
- [ ] Subcommands map to provider-specific CLIs (gh, linear-cli, multica).
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Read an issue

**Fixture:** A known issue key.

**Assertions:**
- [ ] Issue body printed.

**Case Verdict:** PASS

### Case 2: Post a comment

**Fixture:** A known issue and a comment body.

**Assertions:**
- [ ] Comment created.

**Case Verdict:** PASS

### Case 3: Adversarial — auto-close attempt

**Fixture:** Agent tries to mark an issue `done` without orchestrator
sign-off.

**Assertions:**
- [ ] Skill refuses without explicit instruction.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Tracker action recorded in dogfood log.
- [ ] No bulk operations.

## Coverage Notes

Tracker bindings are provider-specific; behavioral coverage requires a
sandboxed tracker (deferred).
