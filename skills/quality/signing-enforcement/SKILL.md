---
name: signing-enforcement
description: "Enforce the lifecycle signing gates programmatically — block /mart-tdd if the BRD lacks a signature block, block /mart-bootstrap if the TDD lacks a signature block, and surface every unsigned BRD/TDD in the repo"
user-invocable: true
---

# signing-enforcement — Lifecycle Signing Gates

## Why this skill exists

The CLAUDE.md non-negotiable rule reads: *"No TDD without a signed
BRD; no scaffold without a signed TDD."* Without this skill, the rule
is markdown-deep — any agent that calls `/mart-bootstrap` directly can
bypass it. This skill wraps the two signing linters in a callable
gate that the lifecycle skills invoke before they do destructive work.

The reviewer of EMB-321 named this as a blocking gap (finding #6).
This skill closes it.

## When to use

Three invocation patterns:

1. **From `mart-tdd`** — before scaffolding a TDD, call this skill on
   the BRD. If unsigned, refuse.
2. **From `mart-bootstrap`** — before writing any model file, call this
   skill on the TDD. If unsigned, refuse.
3. **As a standalone audit** — run on the whole repo to find unsigned
   docs lying around.

## Prerequisites

- A path to a BRD or TDD file (relative or absolute).
- The BRD/TDD itself ends with a `## Signature` section that follows
  the table shape declared below.
- `scripts/lint_signed_brd.py` and `scripts/lint_signed_tdd.py` are
  present and executable.

## Signature shape

Both BRD and TDD end with a `## Signature` section containing this
table:

```markdown
## Signature

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Stakeholder | <name> | <yyyy-mm-dd> | <signature> |
| Data Engineer | <name> | <yyyy-mm-dd> | <signature> |
```

A document is **signed** when at least one row has non-placeholder
`Name`, `Date`, and `Signature` cells. Templates (paths containing
`templates/` or filenames matching `*.template.md`) are skipped —
they always carry placeholder rows by design.

## Workflow

### Step 1 — Locate the document

For lifecycle calls, the caller passes the path of the BRD or TDD
explicitly. For audits, walk `docs/marts/**` looking for files matching
`*business-requirements*.md` / `*tech-design*.md`.

### Step 2 — Check the signature

Invoke the linter:

```sh
python scripts/lint_signed_brd.py docs/marts/<mart>/business-requirements.md
python scripts/lint_signed_tdd.py docs/marts/<mart>/tech-design-doc.md
```

Exit code 0 → document is signed.
Exit code 1 → document is not signed; abort the calling skill with a
remediation pointer.

### Step 3 — On audit, render a report

When run without a specific path, produce:

```
Signed-doc audit:
  - docs/marts/example/business-requirements.md      [signed]
  - docs/marts/example/tech-design-doc.md            [unsigned]
  - docs/marts/legacy/business-requirements.md       [unsigned]

2 unsigned docs found. They MUST be signed before any downstream
lifecycle skill is invoked. See CLAUDE.md non-negotiable rule #1.
```

## CI wiring

The `framework-ci.yml` workflow runs both linters in `audit` mode on
every PR. A PR that introduces an unsigned BRD/TDD is blocked.

## Failure semantics

When `/mart-tdd` or `/mart-bootstrap` invokes this skill and the
signature check fails:

- Do not partially scaffold (no half-written models).
- Emit the linter's remediation message verbatim to the operator.
- Mark the calling skill's invocation `failed` in
  `.skill-invocations.jsonl` (do not skip the log line).

## Adversarial guarantees

This skill is the answer to "what stops a buggy agent from calling
`/mart-bootstrap` directly". The lifecycle pre-step is mandatory and
mechanical — there is no prose to read or honour. The signature shape
is fixed; cell content is checked for non-placeholder text, not for
SHA validity.

If a future iteration of mart-forge requires cryptographic signatures,
extend `scripts/lint_signed_brd.py` — do not add bypass flags to this
skill.

## Output format

- Exit code 0 when the document is signed; exit code 1 otherwise.
- In audit mode, a printed signed/unsigned table per discovered
  document.
- An entry appended to `.skill-invocations.jsonl`
  (`skill_name: signing-enforcement`, output_artifact = path to the
  checked BRD/TDD).

## NOT for

- Cryptographic signing (today's gate is a written commitment,
  reviewer-verifiable).
- Approvals workflow integration with external trackers.
- Auto-signing on behalf of the operator.
- Validating BRD/TDD structure (use `lint_brd.py` / `lint_tdd.py`).
