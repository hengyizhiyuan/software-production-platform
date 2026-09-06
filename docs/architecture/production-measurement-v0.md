# Production Measurement v0

## Status and Authority

**DCP-2: IMPLEMENTED / FOCUSED VALIDATION PASS**

Production Measurement v0 is the first implementation slice under the closed
[Duration & Capacity Semantic
Foundation](duration-capacity-semantic-foundation.md). It normalizes currently
observable production timing and reconstructs a planning-time TaskShapeSnapshot.
It does not estimate duration or influence production decisions.

## Implementation Boundary

DCP-2 uses:

```text
existing authoritative lifecycle facts
→ deterministic read-only projection
→ normalized ProductionMeasurementV0 / TaskShapeSnapshotV0
```

No measurement table or migration is introduced. Existing timestamps remain
owned by their lifecycle records. Stable measurement and snapshot identities
are derived from semantic version plus exact source-fact basis.

The internal `ProductionMeasurementService` is a query seam only. It opens
read transactions, constructs projections, and commits no state. Measurement
failure cannot admit production, dispatch an Executor, satisfy Verification,
seal/authorize a Candidate, integrate a repository, or create a Runtime Commit.

## ProductionMeasurementV0

Every normalized measurement records:

- semantic version;
- kind, scope, and production phase;
- availability and derivation status;
- exact subject, Work, PWU, and Attempt identity where applicable;
- observed start/end timestamps only when authoritative;
- exact derived duration in microseconds;
- source fact/field references;
- deterministic basis fingerprint and measurement identity;
- aggregate internal-turn metadata when present in the Provider Report.

`Observed Fact`, `Derived Interval`, and unavailable timing remain distinct.
No `task_duration` or Estimate exists.

## Supported Measurement Reality

| Measurement | v0 Reality | Provenance |
|---|---|---|
| Machine execution | Supported for one aggregate governed Provider execution | `ProviderExecutionReport.started_at → finished_at`; internal Turns remain Executor-internal |
| Human wait | Supported after exact authorization | `BaselineCandidate.sealed_at → HumanAuthorization.authorized_at` |
| Integration convergence | Supported after convergence | `RepositoryIntegrationEffect.prepared_at → converged_at` |
| Total cycle | Scoped to completed `LONG_LIVED_STEERING` Work | `ADMIT_LONG_LIVED_WORK.created_at → COMPLETE SteeringDecision.created_at` |
| Verification total | Explicitly unavailable | No universal authoritative Verification start/end pair exists |
| Individual Verification duration | Exposed only when the Verification record carries authoritative `evidence.metadata.duration_ms` | Exact Verification record/evidence field |
| Semantic Provider duration | Unavailable | No governed semantic execution start/end pair exists |
| Runtime Commit duration | Unavailable | Only `committed_at` exists |

Verification record creation times are not treated as starts. Attempt creation
is not treated as execution start. Work creation is not treated as Work
admission. Missing facts remain unavailable.

## TaskShapeSnapshotV0

The snapshot is historically reconstructed at the admitted PWU boundary from:

- Work Runtime Binding;
- production Plan Revision;
- immutable PWU objective and Completion Contract;
- exact Source Baseline.

It captures:

- Work, Plan Revision, Production Plan Proposal, PWU, Resource, and Baseline
  identities;
- repository identity and target kind;
- exact target-path, CREATE, and UPDATE counts;
- allowed and forbidden scope counts where authoritative;
- required output/change counts;
- Verification obligation count;
- ordered planning-step count.

The snapshot uses PWU creation time as the planning/admission capture boundary.
Later Attempt generations, execution results, PWU condition changes, repository
observations, or Runtime Commit state cannot alter its basis or identity.

Context-reference count and Executor capability/profile are explicitly
unavailable in v0 because they are not preserved as authoritative facts at this
exact planning boundary. DCP-2 does not reconstruct them from later execution
preparation and does not invent inferred complexity labels.

## Measurement Access

The internal query seam supports:

- TaskShapeSnapshot reconstruction for one exact PWU;
- machine execution for one exact Attempt;
- Human wait and Integration convergence for one exact Candidate;
- Verification measurement for one exact PWU;
- total-cycle measurement for one exact Work;
- a normalized historical sample view for one exact PWU.

No HTTP endpoint, analytics dashboard, ETA, or scheduling UI is introduced.

## Production Non-interference

DCP-2 does not change:

- PLAN-1B or `ONE_PWU_FIT` classification;
- Work or production admission;
- PWU scope or Completion Contract;
- Attempt, Dispatch, or Executor self-refine semantics;
- Verification obligations or independent trust;
- Candidate sealing or Human Authorization;
- Integration or Runtime Commit.

Measurement observes production. Measurement does not govern production.

## Deferred

The following remain **NOT IMPLEMENTED**:

- DurationEstimate, duration buckets, heuristics, and statistical prediction;
- SizingAdvisory runtime behavior and duration-aware PLAN-1B;
- automatic decomposition and PLAN-1A Multi-PWU;
- Production Demand, Queue, Scheduler, capacity admission, worker pool, routing,
  priority/fairness, and autoscaling;
- Production Scheduling Experience or ETA UI.

Watt should eventually expose a strong software-production and scheduling
mental model driven by real production Reality, not decorative UI labels. That
Product Experience remains separately deferred.

## Focused Evidence

DCP-2 focused validation proves:

- exact observed/derived/unavailable semantics;
- persisted Provider timing projection and aggregate internal-Turn metadata;
- Candidate/Authorization Human wait;
- Integration convergence;
- long-lived Work admission-to-COMPLETE scope;
- truthful unavailable aggregate Verification timing and bounded individual
  duration evidence;
- planning-time TaskShapeSnapshot reconstruction and post-execution stability;
- query idempotence and zero persistence mutation;
- PLAN-1B and production trust/authority non-interference.
