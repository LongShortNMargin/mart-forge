# Product Specs

Product specs describe specific user-facing capabilities of mart-forge.
They sit one layer below `SPEC.md` (the governance contract) and one
layer above the skills that implement them.

This directory is intentionally empty in the first commit. Product
specs are added as new capabilities ship.

## Pattern

Each spec is a single file: `NNNN-<slug>.md` where `NNNN` is a
four-digit sequence number. The shape:

```markdown
# PS-NNNN — <Title>

**Status:** Draft | Accepted | Superseded.
**Owner:** <agent or human>.

## Why

What user problem this solves.

## How

The user-visible behavior. Acceptance criteria.

## Boundary

What this spec does NOT cover.

## References

Links to SPEC.md sections, skills, and tests that implement the spec.
```
