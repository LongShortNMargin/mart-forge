# Skill Spec: /signing-enforcement

> **Category:** quality
> **Priority:** critical

## Skill Summary

Enforce the lifecycle signing gates programmatically — block
`/mart-tdd` on an unsigned BRD, block `/mart-bootstrap` on an
unsigned TDD, audit the whole repo for unsigned docs.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] Body declares the three invocation patterns (from `/mart-tdd`,
  from `/mart-bootstrap`, as a standalone audit).
- [ ] Body declares the signature shape (`## Signature` section +
  table with Name + Date + Signature columns).
- [ ] Body declares templates are skipped (the linter does not
  reject placeholder rows on `*.template.md`).
- [ ] Body declares failed-signature behaviour: no partial scaffold,
  no silent fall-through.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path — signed BRD passes

**Fixture:** A real BRD with one filled signature row.

**Expected behavior:** Exit 0; `/mart-tdd` proceeds.

**Assertions:**
- [ ] Exit code 0.

**Case Verdict:** PASS

### Case 2: Unsigned BRD blocks /mart-tdd

**Fixture:** BRD with only placeholder rows.

**Expected behavior:** Exit 1; `/mart-tdd` refuses to start;
remediation message points at the §Signature section.

**Assertions:**
- [ ] Exit code 1.
- [ ] No TDD scaffolded.

**Case Verdict:** PASS

### Case 3: Adversarial — placeholder rows that look real

**Fixture:** Signature row with `Name: ___________` (long underscores
masquerading as a name).

**Expected behavior:** Exit 1 — the placeholder detection strips
underscores and rejects empty content.

**Assertions:**
- [ ] Exit code 1.

**Case Verdict:** PASS

### Case 4: Template files exempt

**Fixture:** `templates/business-requirements.template.md` with the
default unsigned table.

**Expected behavior:** Skipped silently (templates are always
unsigned by design).

**Assertions:**
- [ ] Template returns exit 0.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Dogfood log entry on every invocation.
- [ ] No banned strings in output.
- [ ] No bypass flag exposed.

## Coverage Notes

This skill is the answer to "what stops a buggy agent from invoking
/mart-bootstrap directly". The check is mechanical and there is no
prose to honour.
