# Security

This document covers what must not appear in the public repository and
how the framework enforces that boundary.

## Confidentiality boundary

The repository is public. Anything committed is permanently retrievable
even if later deleted (git history, search engine indexing, downstream
forks). The repository's security posture is therefore "nothing
confidential ever enters."

The categories below are CI-blocking. A commit that contains any of
them is reverted and the cause is logged.

### Categories of confidential content

| Category | Examples |
|----------|----------|
| Operator-specific data | Trading/business holdings, acquisition references, account identifiers, tactical rules, risk protocol parameters |
| Private file paths | Cloud-drive paths, local user home directories, paths into private repositories |
| Internal project identifiers | Names of private projects, internal agent persona names, private repository names |
| Confidential methodology names | Proprietary reference documents, proprietary company names, proprietary template standards |
| Personal credentials | API tokens, secrets, OAuth client secrets, database passwords |

### Banned strings

The list of literal strings the scanner rejects lives in
`scripts/confidentiality_scan.py`. The scanner is the source of truth —
this file is a reminder of *categories*, not a substitute. New banned
strings are added to the scanner with a test in
`tests/test_confidentiality.py`.

## How the scanner works

`scripts/confidentiality_scan.py` walks every tracked file and checks
each line against a list of regex patterns grouped by category. Hits
print the filename, line number, category, and matched text, and the
process exits non-zero.

The scanner excludes itself (otherwise the pattern list would trigger).
That exclusion is the only one. Documentation that needs to discuss the
*categories* uses generic phrasing — never an example of the banned
string itself.

## Secret handling

Secrets MUST be environment-sourced. They MUST NEVER be committed:

- `.env` files are gitignored. The repo carries `.env.example` with
  empty values and a comment explaining what each variable is for.
- API tokens for the live dashboard target are read from environment
  variables only.
- Test fixtures that mimic a provider's response use fictitious
  identifiers — no real account IDs, no real tickers tied to a private
  position.

## Pull requests and review

A reviewer's job includes a confidentiality pass. If the diff includes
any of the categories above, the PR is rejected even if CI passed —
CI is fallback, not the only check.

Reviewers SHOULD check:

- New documentation. Prose is the easiest channel to leak through.
- New tests. Test fixtures sometimes include real-looking data copied
  from a development session.
- New comments in code. Comments often carry context that is fine in a
  private repository and toxic in a public one.

## What to do if confidential content has been committed

1. **Do not push.** If the commit is local, amend or reset and rebuild
   the change from scratch with the sensitive content removed.
2. **If pushed to a feature branch.** Force-push the cleaned branch and
   rotate any leaked credentials.
3. **If merged to `main`.** Treat as an incident. Rotate every
   credential that could have been in the diff. File an issue. Consider
   that the leaked content is now permanent and assume an attacker has
   seen it.

## Trust posture

| Action | Authority required |
|--------|-------------------|
| Code changes in worktrees | Autonomous within ticket scope |
| Orchestration ticket management | Autonomous |
| CI operations | Autonomous |
| Merge to `main` | Reviewer approval + CI green (branch protection) |
| Credential handling | Environment only; never committed |
| Force-push, branch delete, DB drop | Human operator approval |
| Public-facing content (README, docs) | Orchestrator approval + confidentiality scan |

## Reporting

If you find a confidentiality issue in this repository, file a private
report via the repository's security advisory channel before opening a
public issue.
