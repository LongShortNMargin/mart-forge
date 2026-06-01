# Business Requirements Document: {mart_name}

> **Date:** {date}
> **Author:** {author}
> **Status:** Draft

---

## B-1: Version History

| Version | Date       | Author   | Changes                        |
|---------|------------|----------|--------------------------------|
| 0.1     | {date}     | {author} | Initial draft                  |

---

## B-2: Business Context

### Business Process

<!-- Describe the business process this mart supports. -->

_TODO: Identify the core business process (order fulfillment, user
engagement, inventory management, etc.) and describe its scope._

### Purpose

<!-- What decisions will this mart enable? -->

_TODO: State the analytical goal. Example: "Enable daily monitoring of
conversion rates across marketing channels to optimize spend
allocation."_

### Stakeholders

| Role              | Name / Team | Interest                          |
|-------------------|-------------|-----------------------------------|
| Business Owner    |             |                                   |
| Data Consumer     |             |                                   |
| Engineering Owner |             |                                   |

### Domain Glossary

| Term              | Definition                                                  |
|-------------------|-------------------------------------------------------------|
| _example_term_    | _Plain-language definition scoped to this mart's domain._   |

### Data Sources

| Source Name | Source System | Extraction Method | Grain               | Freshness | Verification Result |
|-------------|---------------|-------------------|---------------------|-----------|---------------------|
|             |               | API / File / DB   |                     |           | Verified / Pending  |

> **Verification**: Each source must have at least one confirmed
> row-count or schema check before proceeding to design.

---

## B-3: Metrics Breakdown

| metric_name | metric_definition | source_type | link_status | public_classification | candidate_verification_evidence |
|-------------|-------------------|-------------|-------------|-----------------------|---------------------------------|
|             |                   | native / derived / hybrid | exact / proxy / unsupported / unverified | public / internal | _Describe how the metric was verified against an authoritative source._ |

### source_type Legend

- **native**: Metric is directly available from a single source field.
- **derived**: Metric is computed from two or more source fields.
- **hybrid**: Metric combines native extraction with a derived
  calculation.

### link_status Legend

- **exact**: Metric value matches an authoritative external source
  within tolerance.
- **proxy**: No exact external match exists; a related metric is used
  for directional validation.
- **unsupported**: No external comparator is available; metric is
  validated only by internal DQC.
- **unverified**: Verification has not yet been attempted.

---

## B-4: Notable / Known Limitations

### Declared Constraints

| ID   | Constraint Description                                      | Impact                | Mitigation              |
|------|-------------------------------------------------------------|-----------------------|-------------------------|
| L-1  | _TODO_                                                      |                       |                         |

### Unsupported Metrics

| metric_name | Reason Unsupported | Resource-Exhaustion Evidence |
|-------------|--------------------|-------------------------------|
|             | _e.g., API rate limit, source discontinued_ | _Describe the investigation steps that confirmed the metric cannot be sourced._ |

> Any metric listed here must include **resource-exhaustion evidence**
> showing that reasonable effort was made to source it before declaring
> it unsupported.

---

## Signature

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Stakeholder | ________________ | __________ | __________ |
| Data Engineer | ________________ | __________ | __________ |
