# Quality Rubric

Per-category pass/fail metrics that every skill spec under
`tests/skill-testing/specs/` must satisfy.

The rubric is enforced by `tests/test_skill_specs.py`, which loads
every spec referenced in `catalog.yaml` and runs the static assertions
appropriate for the skill's category.

## Lifecycle category

Skills: `source-discovery`, `mart-brd`, `mart-tdd`, `mart-bootstrap`.
Purpose: drive a Kimball lifecycle phase with a hard gate.

| ID | Metric | PASS criterion |
|----|--------|----------------|
| L1 | Hard gate declared | Spec body contains a `Hard gate` section |
| L2 | Prerequisite check | Spec lists ≥1 prerequisite artifact |
| L3 | Workflow numbered | Workflow steps are numbered (Step 1, Step 2, ...) |
| L4 | Dogfood log step | Workflow ends with an "Append skill-invocation log" step |
| L5 | NOT-for section | Spec carries a "NOT for" section enumerating out-of-scope cases |

## Quality category

Skills: `mart-dqc`.

| ID | Metric | PASS criterion |
|----|--------|----------------|
| Q1 | DQC control coverage | Spec references all 8 control classes |
| Q2 | Test linkage rule | Spec defines how dbt test names map to controls |
| Q3 | Non-pass never green | Spec asserts non-pass statuses never render green |
| Q4 | Coverage manifest updated | Spec includes a step updating `coverage_manifest.json` |
| Q5 | NOT-for section | Spec carries a "NOT for" section |

## Review category

Skills: `mart-review`.

| ID | Metric | PASS criterion |
|----|--------|----------------|
| R1 | Read-only declared | Spec states the skill makes no edits |
| R2 | Bidirectional traceability | Spec checks BRD -> TDD -> model -> dashboard |
| R3 | Verdict vocabulary strict | Verdicts are one of READY / NEEDS_WORK / BLOCKED |
| R4 | Findings categorized | Findings split into Blocking / Concerning / Notes |
| R5 | NOT-for section | Spec carries a "NOT for" section |

## Maintenance category

Skills: `schema-evolve`.

| ID | Metric | PASS criterion |
|----|--------|----------------|
| M1 | Additive-only declared | Spec body declares the skill is additive only |
| M2 | Removal rejected | Spec rejects removal / type change with a BLOCKED message |
| M3 | TDD updated | Spec updates T-8 / T-9 / T-18 / T-19 of the TDD |
| M4 | Smoke build run | Spec runs dbt smoke build before commit |
| M5 | NOT-for section | Spec carries a "NOT for" section |

## Router category

Skills: `using-mart-forge`.

| ID | Metric | PASS criterion |
|----|--------|----------------|
| RT1 | Reads mart.yml | Spec reads `mart.yml` to detect phase |
| RT2 | Ordered detection | Spec enumerates detection conditions in order |
| RT3 | Delegates explicitly | Spec announces the route and invokes the target skill |
| RT4 | NOT-for section | Spec carries a "NOT for" section |

## Utility category

Skills: `commit`, `debug`, `land`, `pull`, `push`, `linear`.

| ID | Metric | PASS criterion |
|----|--------|----------------|
| U1 | Single-purpose declared | Spec body declares the skill produces one outcome |
| U2 | Pre-action checks | Spec runs the local check suite or read-only inspection before any write |
| U3 | Atomic operation | Spec performs exactly one logical write (one commit, one PR, one push) |
| U4 | NOT-for section | Spec carries a "NOT for" section |

## Universal assertions

Every spec, regardless of category, must contain:

| ID | Metric | PASS criterion |
|----|--------|----------------|
| UA1 | Frontmatter complete | `name:`, `description:`, `user-invocable:` present |
| UA2 | "When to use" section | One paragraph on trigger conditions |
| UA3 | "Prerequisites" section | Bullet list of required state |
| UA4 | "Output format" section | Names the produced artifact(s) |
