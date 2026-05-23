# mart-bootstrap — Scaffold from Signed-Off TDD

**Trigger:** "bootstrap a mart for {domain}" or Phase C detection by using-mart-forge.

**Prerequisite:** Signed-off TDD (Grade A or waived) must exist.

## Behavior

1. Read signed-off TDD and generate `mart.yml` from TDD specifications.
2. Create directory structure:
   ```
   examples/{mart-name}/
   ├── mart.yml
   ├── brd.md (signed, from Shot 1)
   ├── tdd.md (signed, from Shot 1)
   ├── models/
   │   ├── ods/
   │   ├── dim/
   │   ├── dwd/
   │   ├── dws/
   │   └── ads/
   ├── seeds/
   ├── tests/
   ├── fixtures/ (if applicable)
   ├── dashboard/
   │   ├── app.py
   │   ├── requirements.txt
   │   └── README.md
   ├── dqc_scorecard.json
   ├── dbt_project.yml
   ├── profiles.yml
   └── .github/workflows/daily.yml
   ```
3. Generate dimension seeds (date calendar, entity config) from TDD T-7.
4. Generate ODS model from TDD T-6 (incremental, provenance, partition logic).
5. Generate DWD model from TDD T-8 (dedup, business keys, native pass-through, derived SQL).
6. Generate DWS models from TDD T-9/T-10 (aggregations with explicit SQL).
7. Generate ADS model from TDD T-11 (OBT with explicit column list).
8. Generate `schema.yml` with generic tests implementing all applicable control classes.
9. Generate singular tests for business-logic assertions.
10. Generate `dqc_scorecard.json` template with all control classes.
11. Generate GitHub Actions workflow from mart.yml schedule.
12. Generate dashboard app.py with metric cards tracing to TDD + link_status display.

## Hard Gate

**No scaffold without signed-off TDD.** Refuse if TDD is missing or unsigned.

## Template Sources

All generated code uses templates from `templates/`:
- `templates/models/{ods,dim,dwd,dws,ads}/template.sql`
- `templates/seeds/dim_date.csv`
- `templates/tests/template_singular.sql`
- `templates/dashboard/app.py`
- `templates/pipeline/daily.yml.template`

## Output

- Complete dbt project directory under `examples/{mart-name}/`
- All models, seeds, tests, pipeline, and dashboard files
- `dqc_scorecard.json` template ready for `dbt test` linkage
