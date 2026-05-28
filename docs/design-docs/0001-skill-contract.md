# DD-0001 — Skill Contract

**Status:** Accepted.
**Last updated:** 2026-05-28.

## Context

mart-forge runs as a Claude Code plugin. Each lifecycle phase is a
skill (a markdown file under `.claude/skills/<name>/SKILL.md`). The
agent runtime discovers skills by walking that directory; it loads the
frontmatter to decide whether a skill is callable in the current
context.

A skill without a clear contract becomes either a black box (no one
knows when to invoke it) or a footgun (it activates eagerly and
overwrites work). This DD nails the contract down.

## Decision

Every SKILL.md in this repo MUST have:

### 1. YAML frontmatter

```yaml
---
name: <kebab-case slug, matches the directory name>
description: "<one sentence, present tense, what the skill does and when to invoke it>"
user-invocable: true|false
---
```

Optional frontmatter fields:

- `argument-hint: "<one-line hint shown in completion>"`
- `allowed-tools: "Bash, Write, Edit, Read"`  (defaults to all)
- `model: sonnet | opus | haiku`             (defaults to inherit)

`user-invocable: true` makes the skill callable as `/<name>` from the
session. `user-invocable: false` reserves the skill for internal
chaining by another skill.

### 2. Body sections, in order

```markdown
# <name>

## When to use

One paragraph. Describe the trigger conditions. Be specific enough
that an agent can decide "yes/no, this skill applies" without reading
the rest of the file.

## Prerequisites

Bullet list of artifacts that must exist before this skill runs.
Include both file paths and state conditions (e.g., "mart.yml has
`brd_signed: true`").

## Hard gate

(Required for skills that enforce a lifecycle gate.)

```text
GATE: <one-line statement of what cannot proceed without this skill's output>
```

Followed by the precondition check: if the gate condition is not met,
the skill MUST reject the invocation with a one-line BLOCKED message
that points to the predecessor skill.

## Workflow

Numbered steps. Each step ends with the artifact it produces or the
state change it commits. Steps must be runnable in order from a cold
session.

## Output format

The path of the primary artifact and any secondary artifacts. If the
skill modifies `mart.yml`, list the keys it touches.

## NOT for

Bullet list of out-of-scope cases. This is the "negative space" of
the contract and prevents the skill from being invoked for the wrong
job.
```

### 3. Discoverability

The directory name MUST match the `name:` frontmatter slug. The
plugin manifest (`.claude-plugin/plugin.json`) declares the skills
directory once; individual skills are discovered by directory walk.

## Consequences

- **Pro.** Adding a skill is mechanical: copy a template, fill it in,
  drop it under `.claude/skills/<name>/`.
- **Pro.** A linter can statically check that every skill has the
  required sections. (`tests/skill-testing/` runs this check.)
- **Con.** Some skills (like `using-mart-forge`) do not have a hard
  gate and must omit that section. The linter accepts both shapes
  (hard-gate present or absent) as long as the rest is intact.

## Alternatives considered

- **One big SKILLS.md.** Rejected: forces the agent to grep for the
  active skill on every invocation. Slow and noisy.
- **Skills as Python modules.** Rejected: forces a Python runtime
  inside the agent loop. The skill is supposed to be readable by the
  agent and by a human reviewer alike.

## References

- `SPEC.md` §3 (Product Architecture).
- `tests/skill-testing/quality-rubric.md` (the rubric the linter
  enforces against every spec).
