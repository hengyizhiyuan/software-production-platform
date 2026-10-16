# Multi-PWU Guardian evidence repair — 2026-10-16

## Scope and cause

Work `e88d6f02-a69a-51f8-8f5a-b70a34e1f01d` produced a sealed Candidate and a
READY static Preview. Guardian passed the terminal Join but rejected both
branches, each with six `CONTEXT_COVERAGE_GAP` findings. The terminal Candidate's
verification IDs were incorrectly required to include each branch's proof.

Candidate `1ebbf1e5-2df3-560f-ac5e-94009800131d` seals commit
`d2bcf59a11084f65e21d7a529bf9df80d74b2744`. The existing terminal verification
list correctly belongs to that proposal. Appending branch records would violate
the existing admissibility and integration contracts.

## Repair

Guardian independently validates nonterminal evidence through the exact persisted
production graph, published branch baseline, proposal admission and terminal seal.
Watt adds only three raw Owner resolver references: production-run,
production-plan and proposal-admissibility. The Owner lock pins the repaired
Guardian source. Existing terminal verification, Native lineage, protected-context
and phase gates remain in force. ECF, UI, retry policy and production data are
outside this change.

This is a deterministic evidence-consumer repair under the existing Owner
responsibilities. Legitimate variation is a branch output differing from the
final integrated output; identities, versions, admission and dependency linkage
must remain exact. Missing evidence still blocks, rather than invoking model
refinement or inventing authority.

## Validation

- Guardian complete suite: **281 passed**. Includes two independent graph shapes
  (parallel branches with Join, serial dependencies), retained single-PWU cases,
  and rejection of wrong plans/versions/generations, missing publication or
  admission, wrong parents/terminal proof, incomplete obligations and cycles.
- Watt adapter, Candidate verification history and C3 evidence projection:
  **65 passed**. Resolver tests cover present/missing records and exact lookup IDs.
- Owner staging validated the Git archive against `owners.lock`: repaired
  Guardian `3836a9b2877584b4be5933da5545576e4b9bf1e7`, source digest
  `1a9fc85142acc8b906e9f55403d77596269865d84cab6d878d6b1f83607cb09c`.
  ECF remains at its previous pin.
- Real Owner evidence replay: PostgreSQL forced read-only transactions; patched
  modules loaded only into a separate diagnostic process in the API container.
  No service files changed, no `assess()` call, no new Guardian result, no model
  call and no Work transition. Each of the three requests resolved **6/6**
  protected obligations; both previously rejected branches passed exact lineage.

| PWU | Request | Protected evidence after repair |
| --- | --- | --- |
| `5972c96d-2400-539b-9dd2-8e56fdd62ef2` | `1aba6999-b252-5b5b-b055-da0eb13e0b50` | 6/6 |
| `b335b8a7-c807-5c90-a96c-6f9101bad75a` | `34f1a6bf-7e1f-5165-a05c-55d3ab5ae247` | 6/6 |
| `bdce1f6c-2cb4-574b-9574-33093868ff33` | `f5516a90-063d-514e-94fc-ef9773881334` | 6/6 |

The original runtime was Watt `9ca6cc4b`, Guardian `ab26128`, ECF `1d3fedd`.
The local diagnostic evidence is retained under
`D:/hy/spp-claude/diagnostics/e88d6f02-20261016/`, including
`guardian-predicate-replay-patched.json`. Full Work content is not added here.

## Runtime recovery boundary

This source repair and read-only replay do not replace the stored BLOCKED results
or claim Human acceptance. After deployment, a fresh assurance request is needed.
The existing stop/recreate Preview path can issue one for the same Candidate;
merely refreshing a READY Preview or restarting the service reuses old results.
Deployment and Work recovery were not performed as part of this source change.
