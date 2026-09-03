# ORCH Dogfood #1 Failure Finding: Artifact and Verification Contract Mismatch

## Evidence Status

This document preserves the first real MVP-ORCH-1 dogfood failure as historical Watt production evidence. It records observed Runtime facts and the narrow product finding; it does not repair the Work, authorize a retry, or introduce a new implementation commitment.

## Scenario

The Human submitted a documentation Work asking Watt to place a formal Production Orchestration Lite product/architecture explanation in an appropriate location in the existing documentation system. After Human Work Draft Approval, Production Orchestration Lite advanced the Work without manual Advance and stopped at Human Attention when Verification returned `FAIL`.

| Fact | Observed Reality |
| --- | --- |
| Work | `d1e21fe3-4510-4f0e-b17d-134342040ac2` |
| Run | `bd60c3f1-4cfb-414e-b0e5-dc94a9f288ac` |
| PWU | `eeec5e92-b775-4555-9357-ed1fe8c65275` |
| Attempt | `b7fc4637-ff24-4324-97c6-5e8ef7342b2e`, generation 1 |
| Source revision | `e6d370503cfdb4fb750e138fa24a2034da605093` |
| Provider Outcome | `SUCCESS` |
| Independent Observation | one `ADDED` path: `docs/work-d1e21fe34510.md` |
| Completion | `PRODUCED`; required artifact and required change both `PASS` |
| Verification | `FAIL` |
| Work projection | `BLOCKED / VERIFICATION`; `trusted_result=false` |
| Later governance | no Candidate, Authorization, Integration Effect, or Runtime Commit |

The produced Markdown was substantive and relevant to the requested topic. It covered Human-in-the-loop versus Human-as-the-loop, bounded automatic progression, Human Attention, current MVP boundaries, future evolution, architecture invariants, and product acceptance. The failure is not evidence that the Executor failed to produce an artifact.

## Exact Failure

Work refinement selected:

```text
docs/work-d1e21fe34510.md
```

That exact path was propagated into the PWU Completion Contract, Materialized Execution Input, and Executor authorized paths. Independent Observation confirmed that it was the only changed path.

The active `provider:mvp-e2e-markdown` verifier instead retained the historical fixed target:

```text
docs/mvp-e2e/first-real-governed-work.md
```

Its evidence reported:

```yaml
exact_path_only: false
headings_present: true
statements_present: true
readable_non_empty: true
diff_valid: true
```

`exact_path_only` was the only false sub-check. The other content checks concerned the verifier's pre-existing fixed target in the proposed tree, not the newly produced artifact. Verification therefore did not evaluate the semantic content of the admitted Work product.

## Why the Artifact Path Was Chosen

The path was not selected by the Executor. When refinement receives no explicit `expected_artifact_path`, the current application fallback is:

```python
request.expected_artifact_path or f"docs/work-{work.id.hex[:12]}.md"
```

The first twelve hexadecimal characters of the Work identity are `d1e21fe34510`, producing the observed path. The admitted execution instruction then prohibited the Executor from modifying any other repository path.

Repository Reality contained enough information to identify architecture and roadmap placement candidates, including `AI_context.md`, `docs/architecture/mvp-architecture.md`, `docs/architecture/architecture-principles.md`, and `docs/roadmap/mvp-scope-calibration.md`. The Context Package also exposed the ORCH-1 Source-of-Truth section and roadmap link. The remaining gap was not total context absence: refinement/planning did not make a repository-aware placement decision before fixing the authorized path.

## Finding Classification

```text
Primary:
    VERIFICATION_CONTRACT_GAP

Contributing:
    REFINEMENT_GAP
    PLANNING_GAP
    PRODUCT_SCOPE_GAP

Not supported by the evidence:
    EXECUTOR_FAILURE
    CONTEXT_GAP
```

The successful orchestration behavior is itself evidence: Watt automatically reached the real governance boundary, preserved Provider and Production Reality separately, and stopped instead of manufacturing Verification `PASS` or continuing toward Candidate formation.

## Narrow Product Finding

> Artifact placement, execution authorization, Completion, and Verification must bind the same admitted artifact target and semantic expectation.

The narrowest follow-up capability is a repository-aware Artifact Placement Contract during refinement/planning. It should make the proposed path Human-visible before Work Draft Approval and propagate the same admitted target through PWU, Materialized Execution Input, authorized changed paths, Completion, and a target-independent verifier. This is a product improvement finding, not an implementation authorization.

## Preservation Boundary

The blocked Work remains historical Dogfood Evidence. No retry, replacement Attempt, Runtime mutation, Candidate, Authorization, repository integration, or Trusted Baseline advancement is authorized or performed by this record.
