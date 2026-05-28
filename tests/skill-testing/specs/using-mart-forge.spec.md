# Skill Spec: /using-mart-forge

> **Category:** router
> **Priority:** high

## Skill Summary

The default entry point. Reads `mart.yml` and the project state to
decide which phase skill applies next, then delegates.

## Static Assertions

- [ ] Skill reads `mart.yml`.
- [ ] Detection conditions are enumerated in order (numbered table).
- [ ] Skill announces the route before delegating.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Fresh repo -> /source-discovery

**Fixture:** Empty docs/, mart.yml minimal.

**Assertions:**
- [ ] Route printed: `/source-discovery`.

**Case Verdict:** PASS

### Case 2: BRD draft -> /mart-brd (resume)

**Fixture:** BRD exists, signature block empty.

**Assertions:**
- [ ] Route printed: `/mart-brd (resume)`.

**Case Verdict:** PASS

### Case 3: Signed TDD, no models -> /mart-bootstrap

**Fixture:** TDD signed, no models/ directory.

**Assertions:**
- [ ] Route printed: `/mart-bootstrap`.

**Case Verdict:** PASS

### Case 4: Adversarial — corrupted mart.yml

**Fixture:** mart.yml exists but is invalid YAML.

**Assertions:**
- [ ] Skill reports the parse error.
- [ ] Skill does NOT delegate to any phase skill.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Router does not write any artifact directly.
- [ ] Router emits dogfood log entry.

## Coverage Notes

Router logic is amenable to unit testing; full coverage deferred to
the conformance dispatch (TD-001).
