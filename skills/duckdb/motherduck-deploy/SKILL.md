---
name: motherduck-deploy
description: "Deploy a DuckDB mart to MotherDuck cloud — connection profile, token via env, fixture-mode vs live-mode toggle, and a deploy preflight that aborts if the cloud schema has drifted from the local build"
user-invocable: true
---

# motherduck-deploy — MotherDuck Deployment

## When to use

Reach for this skill when a `creating-duckdb-mart`-shaped warehouse
needs to publish to MotherDuck. The skill assumes the local dev target
already builds clean; it handles only the cloud-promotion step.

## Prerequisites

- A green `dbt build --target dev` against the local DuckDB file.
- A MotherDuck account and a service token exported as
  `MOTHERDUCK_TOKEN` (never committed; never inlined in `profiles.yml`).
- `mart.yml` declares `motherduck_database: <db_name>`.

## Workflow

### Step 1 — Resolve credentials from env only

`profiles/<mart_name>.yml` references the token by env variable, not
by literal value:

```yaml
<mart_name>:
  outputs:
    prod:
      type: duckdb
      path: "md:{{ env_var('MOTHERDUCK_DATABASE', 'mart_forge_example') }}"
      schema: main
      threads: 4
      extensions: [httpfs, motherduck]
      attach:
        - path: "md:{{ env_var('MOTHERDUCK_DATABASE', 'mart_forge_example') }}"
          alias: cloud
```

The token comes from `MOTHERDUCK_TOKEN` automatically — DuckDB's
MotherDuck driver reads it at connect time. Do not echo the token into
the dbt log.

### Step 2 — Pick a deploy mode

mart-forge supports two MotherDuck deploy modes:

| Mode      | When to use                                          | What it does                                         |
|-----------|------------------------------------------------------|------------------------------------------------------|
| `fixture` | Reviewer is auditing the warehouse offline.          | Builds against parquet seeds. No cloud calls.        |
| `live`    | Production cutover or canary against real source.    | Reads upstream sources. Writes to MotherDuck.        |

Set the mode with `--vars '{deploy_mode: fixture}'`. Default is
`fixture`. A `live` run cannot start without a current-day token
verification (see Step 4).

### Step 3 — Preflight schema-drift check

Before the first `live` deploy of the day, run:

```sh
python scripts/motherduck_preflight.py \
  --local ./warehouse/<mart_name>.duckdb \
  --remote "md:$MOTHERDUCK_DATABASE"
```

The preflight script:

1. Lists every table in `main` on both sides.
2. Compares column lists (name + dtype).
3. Compares row-counts on dim_* tables (these are slowly changing; a
   delta here is a red flag).
4. Exits 1 if any drift exceeds the tolerances declared in TDD §T-19.

A drifted cloud schema means someone modified the warehouse outside the
mart-forge pipeline; reconcile before deploying.

### Step 4 — Deploy

```sh
dbt build --target prod --vars '{deploy_mode: live}' \
  --select "tag:warehouse" --fail-fast
```

`--fail-fast` aborts on the first failing model; in a cloud context
this avoids a half-published warehouse.

### Step 5 — Post-deploy DQC

Run `mart-dqc` against the prod target. A failing DQC class on prod is
treated as a P1 incident; promote a rollback target (`prev_prod`) if the
scorecard drops below the SLA in TDD §T-20.

## Failure modes

- **Token missing** → DuckDB raises a clear error at connect; surface it
  to the operator. Do not retry silently.
- **Network partition** → `live` deploys cannot fall through to
  `fixture`; abort and queue a rerun.
- **Schema drift not reconciled** → preflight blocks; do not pass
  `--no-preflight` to bypass.

## Output format

- A printed preflight summary (drift report) and a deploy summary
  (models built, rows written, target).
- The MotherDuck-side warehouse updated to the new dbt build.
- An entry appended to `.skill-invocations.jsonl`
  (`skill_name: motherduck-deploy`, output_artifact = the new
  `target/run_results.json`).

## NOT for

- IAM / org-level MotherDuck configuration.
- Cross-region replication strategy.
- Cost optimization for query-heavy ADS views.
- Authoring incremental models (use `duckdb-incremental-models`).
- Initial DuckDB scaffold (use `creating-duckdb-mart`).
