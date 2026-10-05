# ADR-011: Verification Before Completion

- **Status:** Accepted.
- **Decision:** A Worker result enters verification. Completion is projected
  only after all required Work verification records pass and the PWU is
  satisfied; a failed record yields `VERIFICATION_FAILED`.
- **Context:** A successful model/tool response is a claim, not verified
  software production.
- **Reason:** Repository consistency, tests and required artifacts must be
  observed and preserved before claiming production completion.
- **Consequence:** Verification failures keep Work visibly incomplete, with
  exact result and owner evidence retained for repair or retry.
