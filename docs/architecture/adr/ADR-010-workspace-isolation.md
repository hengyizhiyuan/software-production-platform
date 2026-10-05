# ADR-010: Workspace Isolation

- **Status:** Accepted.
- **Decision:** Every Attempt uses an isolated, persisted Git workspace at an
  exact source commit, with Task path bounds and retention status.
- **Context:** Direct edits to an authoritative checkout can contaminate later
  Work and erase the source basis of evidence.
- **Reason:** Exact source and a separate workspace make change attribution,
  retry and cleanup tractable.
- **Consequence:** Worker observes source and changed paths, stores a bounded
  diff and artifact hashes, and invokes retention cleanup. Filesystem quota
  remains an explicit follow-up beyond v1 observation checks.
