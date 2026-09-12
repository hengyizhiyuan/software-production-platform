# Watt-native Executor Qualification Amendment v3

Date: 2026-09-12

## Authority and retained history

The Human Qualification Owner explicitly authorized this amendment after the
first v2 execution exposed and retained a runtime terminal-decision defect.

This amendment does not alter or reclassify prior evidence:

- v1 digest `e57d664eb9dbe2988949c0cecf1bb37ab010ecdaf07808dc1921d93bcac91c57`
  retains all 36 completed executions and its conservative RMB 3.69511347 cost;
- v2 digest `6f04b354694d9fdd9b536d49d7879f18c136d8149d8d73a59677d0dd5abdfc97`
  retains failed execution `T5-1-B` and its RMB 0.04529831 cost.

The combined conservative Provider spend before v3 is RMB 3.74041178.

## Authorized runtime correction

The v2 failure occurred after a `CONTINUE` response proposed the final writes and
predicted an empty residual list. The kernel removed all tools before observing
those effects, preventing the next step from running required verification. It
then reached the truthful but unsuccessful `UNABLE_TO_COMPLETE` terminal.

The corrected kernel treats `CONTINUE` as non-terminal. Tools remain available
after its effects even when that response predicts no residual work. The existing
three consecutive read/check-only round bound still forces a terminal decision
and prevents unbounded repeated verification. Settled Tool receipts are retained
cumulatively in each checkpoint so the terminal decision sees the complete
evidence frontier.

## Frozen v3 benchmark

V3 preserves Amendment v2 without task substitution or relaxation:

- six meaningful tasks, three A/B pairs each;
- 18 paired trials and 36 executions;
- identical randomization seed and resulting order;
- identical A/B injection assignments;
- identical acceptance criteria and engineering-quality anchors;
- primary `deepseek-flash / high`;
- replacement `deepseek-v4-pro / high` only for T3-2-B, T4-1-B and T5-2-B;
- sequential real Provider requests with no automatic retry;
- the same combined RMB 100 hard cap, including all v1 and v2 known and
  response-unknown cost.

The v2 Landlock per-delivery isolation boundary remains mandatory. V3 runs in a
new database, workspace, checkpoint volume, evidence namespace, Compose project,
and port. V1 and v2 runtimes and evidence are not reused as execution state.

Every failed v3 execution remains in the v3 result. V3 passes only if the original
Qualification Contract and Amendment v2 gates pass, including all 18 B outcomes,
zero material intent drift, hard-invariant safety, recovery without technical
Human mission repair, and paired engineering-quality equivalence.
