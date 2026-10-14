# C3 Formation — semantic contribution compilation and per-source restatement

2026-10-14/15 (Asia/Shanghai). Branch `claude/c3-formation-ai-native-convergence`. **C3 status is
not changed by this report and remains PARTIAL; Human owns the status.**

## 1. Problem and evidence base

Cross-sample read-only corpus (generation2–34, live21/22b/24b, trial12, five 1014 probes; mixed
source/contract versions, so cross-condition evidence, not a success rate):

| Uncovered-character class | Trials |
| --- | --- |
| punctuation or conjunction only | 9 |
| sub-word fragment (offset arithmetic) | 5 |
| governing negation/qualifier dropped | 3 |
| most/all of a source | 5 |

The model split multi-requirement sources per consumer and lost shared separators; in round-1 it
also wrote quotes that do not exist in the source (`Excluded from this Work: Do not deploy.` for
`Do not deploy, publish, …`). Duplicate/linked-proof failures came from local route edits whose
whole-candidate effect was invisible. Common root: **semantic choice and character/ordinal
bookkeeping were coupled in one model output** (Maturity Reassessment §3.3 D, §5.1).

## 2. Changes (existing Formation Owner, negotiated marker only)

| Commit | Change |
| --- | --- |
| `f9519044` | marker v1: Owner attaches **pure punctuation** between a source's own chosen components (never words, negation or qualifiers; coverage gate unchanged); construction path receives the shared-basis/dedup guidance; repair treats the complete candidate as the unit |
| `397d106f` | marker v2: repair has **one representation** — complete contribution sets for the sources being changed, unlisted sources retained verbatim; no route ordinals; an omitted source can be restored; decisions are encoded in the restatement |
| `e13d8258` | B-class fix: `_group_repeated_feedback_predicates` treated two distinct consumption checks of one source as identity drift, ending a lawful negative Review as `WIRE_FEEDBACK_IDENTITY_DRIFT` (observed live, ordinary41-t3) |

Unchanged: `validate_projection_candidate`, coverage predicate, component/consumer dedup,
linked-proof uniqueness, independent Review, Guardian, two candidates / one feedback / four
logical calls, tokens, timeout, transport. Old receipts are not upgraded; marker drift stops
without a model call. Rejected alternative: Owner-side clause splitting — it would be a
keyword/separator rule substituting for semantic judgment (§14.5).

## 3. Qualification (protocol fixed before calls — `protocol.md`)

Fresh bounded Formation per trial, both candidates real model calls, ordinary34 (19 sources) and
ordinary41 (23 sources) × 3, deepseek-flash / reasoning none / 16 384 / 120 s, isolated container
without database or socket. Holdout not read.

| Criterion | Round-1 (`f9519044`) | Round-2 (`397d106f`) |
| --- | --- | --- |
| false admission (hard) | 0 | **0** — admitted plan re-validated offline: no duplicate, full coverage, all-positive Review |
| Owner attachments only punctuation | 2/2 | 10/10 |
| terminal replay without calls | 6/6 | 6/6 |
| reached independent Review | 1/6 | 4/6 |
| **lawfully admitted** | 0/6 | **1/6** (ordinary34-t3, first candidate) |
| tokens | 955 411 | 1 203 271 |

**Protocol deviation:** the token stop was checked only before each trial, so the last round-2 trial
started at 0.97M and finished above the remaining allowance. Total actual spend 2 158 682 tokens,
exceeding the protocol's 2.0M hard stop by 158 682. No additional trial was started after the cap.

Round-1 failures: 3/6 the model combined the additional restatement with route edits
(representation ambiguity, fixed by v2), 1 invalid JSON, 2 semantic. Round-2 failures: 1 B-class
platform defect (fixed in `e13d8258`; replay of the exact outputs now ends at the Review's actual
predicate), 1 schema deviation (object instead of string ref), 3 genuine semantic errors correctly
rejected by Review (Seal attached to pure content clauses; reviewable-Candidate Seal missing;
"add pages" → DENY_PREVIEW), plus an unresolved Review-boundary question: whether GIT_DIFF_SCOPE
can express "do not add pages / change README" is judged inconsistently across trials (same open
item as the earlier Category D). Six trials do not establish generalisation; independent Holdout
requalification remains with `.c3-holdout-reviewer`. Round-1's first launch exited before any call
(runner bug, preserved on ECS as `trials-aborted-runner-1`).

Exact-image regression (each round and the release): attestation, installed focused suite and
isolated PostgreSQL 10/10 PASS. Local non-PG C3 suite: failure set identical to the `9d735741`
baseline (20 pre-existing environment failures), 944 passed.

## 4. Deployment

Release image `sha256:8485427d327b10a7d862eda57cc58af47f031a5855e4ddeef147b36217f683b0`
(`e13d8258`), built offline from the exact archive, replaced only the formal API image of
`watt-cloud-worker` (previously `32db38ca` trace image). Existing compose files preserved,
API-only override, quiescence admission (0 allocations / 0 queue), health and runtime smoke
(provider configured, marker v2) PASS; only the API container changed; rollback tag
`watt-cloud-worker:c3-predeploy-rollback-e13d8258`. The C3 branch already contains the converged
Trace modules (2026-10-13 decision); migrations identical; dependencies differ only by test-only
`jsonschema`. Worker/coordinator/tool-host images were not changed. Receipts in `receipts/release/`.

Private requests, responses and Owner receipts: ECS
`/data/watt/ai-native-evolution-20261013/semantic-compilation-20261014/{trials,round-2/trials}/private/`.

## 5. Remaining obligations

- Review consistency on Diff-expressed exclusions (independent Review Owner), and recurring
  model semantic errors (Seal placement) — candidate variance handled by existing Review/repair,
  not new Formation rules.
- Broader non-Holdout and independent Holdout qualification on the deployed revision.
- Model-, monetary and energy cost beyond token counts: UNKNOWN.
