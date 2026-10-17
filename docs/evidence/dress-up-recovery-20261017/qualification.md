# Local qualification and limitations

Exact composed sources: Watt pending source on the original branch; ECF
`1d3feddf0c7e7726fea23c58d194d64034547a7a`; independently published Guardian
`26bb402563bb781731749b7b8fb4fe5aed74f669`, canonical src digest
`e5973aa54cca9ecfbf339a872fa8683a957519c2d6603dc4fccc19b16b2a89a9`.

- 137 targeted source/obligation/static-verifier tests pass, repeated against
  these exact composed Owner pins.
- 69 Verification/Guardian-adapter/Preview/security regression tests pass.
- Independent Guardian full suite: 350 pass.
- 31 PostgreSQL Verification/Preview tests pass in an explicitly isolated local
  database. The first run's 55 receipt-fixture setup errors were the fixture's
  deliberate database-name guard, before any of those cases ran.
- Re-running the receipt fixture in its required local
  `c1_contract_continuity` sandbox produced 1 pass and 6 failures before the
  remaining cases were interrupted. The identical seven-case selection on
  unchanged Watt `f6595557e45368fb2de4351d62231f80620f16ff` also produced
  1 pass and the same 6 failing cases: legacy no-model content-verification
  fixtures and incomplete controlled wire-default Review fixtures. This is
  preserved baseline failure evidence, not a full receipt-suite PASS.

The real failed source-only fixture has all original facts, IR, constraints,
records and paths. It admits 20 pending bindings with no extra model call and
round/episode identity preserved. Guardian independently checks eligibility;
this fixture claims no executed PWU, produced Candidate or successful preview.
Live recovery and user-facing observations are recorded separately.

Preview audio follow-through: 34 affected tests pass, including exact bytes
larger than the text inspection limit through both Human and private Guardian
static preview surfaces, correct MP3/WAVE MIME and Candidate revision/tree
headers. Stale fingerprints, undeclared/secret paths, symlinks, oversized audio
and unchanged oversized-text limits remain rejected. CSP is unchanged. This
transport fixture claims no audio quality verdict.
