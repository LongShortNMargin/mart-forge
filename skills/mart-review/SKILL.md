# mart-review — Production Readiness Assessment

**Trigger:** "review {mart} for production readiness"

## Behavior

1. **Naming convention compliance:** Check all models follow the naming pattern `{prefix}_{layer}_{entity}`.
2. **Bus matrix coverage:** Verify every fact table connects to declared dimensions.
3. **Grain declaration:** Confirm every fact table has an explicit grain statement.
4. **Incremental strategy audit:** Check no `current_timestamp()` in model logic; verify idempotency.
5. **Provenance columns:** Verify ODS models have provider, pull_ts_utc, quote_ts_utc, run_id.
6. **DQC coverage audit:** Run the dqc-audit skill (all 8 control classes).
7. **Metric traceability:** Verify BRD metric → TDD column → model → test → dashboard chain.
8. **Confidentiality scan:** Check for private paths, proprietary identifiers, operator data.
9. **Template compliance:** Verify BRD has all B-sections, TDD has all T-sections.

## Output

Production readiness scorecard:

| Category | Status | Findings |
|----------|--------|----------|
| Naming | Pass/Fail | {details} |
| Bus Matrix | Pass/Fail | {details} |
| Grain | Pass/Fail | {details} |
| Idempotency | Pass/Fail | {details} |
| Provenance | Pass/Fail | {details} |
| DQC Coverage | Pass/Fail | {details} |
| Traceability | Pass/Fail | {details} |
| Confidentiality | Pass/Fail | {details} |
| Templates | Pass/Fail | {details} |

**Overall Grade:** A / B / C / D / F

Grading criteria:
- **A:** All categories pass, no Critical/High findings
- **B:** No Critical findings, ≤2 High findings
- **C:** No Critical findings, >2 High findings
- **D:** ≤1 Critical finding
- **F:** >1 Critical finding
