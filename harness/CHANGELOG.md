# Harness changelog

Patient records carry the harness version in every file they write
(`harness:` in frontmatter, `Harness:` in commit bodies). Entries here say
what changed and whether a record written under an older version needs
migrating.

## 1.0.0 — 2026-11-03

Initial release.

- `AGENTS.md` entry point, `CLAUDE.md` pointer, `harness/PRINCIPLES.md`.
- Schemas for profile, summary, labs, visits, other inputs, symptoms,
  diagnoses and chats; canonical analyte list.
- Procedures: session-start, onboarding, commit (with corrections),
  summary-refresh.
- `harness/scripts/msdh.py`: session, status, check-remote, validate,
  commit, tag, labs rebuild/list/trend, symptoms.

Not yet in this version: ingest, visit, adhoc, second-opinion and
harness-update procedures. `AGENTS.md` tells agents to refuse those
operations until the procedure file exists.
