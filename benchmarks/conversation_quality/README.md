# Conversation Quality Benchmark

This benchmark is a reusable Human–Watt conversation-quality corpus. It covers
30 representative interactions across Chinese and English conversation modes.
It is not an authoritative product dataset and does not score hidden model
reasoning.

The deterministic contract suite validates corpus coverage and architectural
behavior. A bounded real-Provider subset covers the six mandatory high-value
scenarios: vague goal, known-context reuse, direct question, explicit detail,
correction/disagreement, and recommendation.

Quality is reviewed across directness, naturalness, concision, context fidelity,
non-repetition, proactivity, relevance, decision utility, appropriate detail,
internal-metadata leakage, and conversation continuity. Structural assertions
protect hard boundaries; representative samples remain available for Human
review because subjective quality cannot be reduced to one boolean.

## Pipeline latency probe

`pipeline_probe.py` runs the five architecture-review scenarios through real
loopback HTTP/SSE. Eligible default pre-Work uses one Provider Turn per Human
message; `--separate-pre-work` retains the two-call comparison path. It requires
`--run-real-provider` plus `SPG_TEST_DATABASE_URL` pointing at a fresh, migrated
`spg_pipeline_*` database. It refuses existing interactions or Work, does not
truncate data, and verifies that no Work or Runtime rows are created. The test
connection and Provider authentication are infrastructure inputs, never prompt
content. Use `PYTHONPATH` to select an exact preserved source snapshot.

Example after preparing the isolated database and Provider environment:

```text
python benchmarks/conversation_quality/pipeline_probe.py --run-real-provider --label coalesced-default-effort --output .spg/validation-evidence/collaboration-pipeline-optimized-result.json
```

The report retains per-case request receipt, client acknowledgement, first SSE
event, first non-whitespace response, terminal delivery, provider stage duration,
configured effort, frame, intent, selected schema, and final wording. New source
also includes server milestone telemetry. It writes partial failure evidence
without retrying. Compare identical inputs/model and record the source hash;
prior generated responses will naturally differ in a multi-turn comparison.

A five-case run is an observed sample, not a p95 estimate or proof of subjective
quality. Lower reasoning effort and code changes must be reported as combined
conditions rather than assigning all improvement to one factor. Blank/inherited
reasoning configuration does not establish the provider's actual effective
reasoning budget. Review the retained language manually, including whether one
question mark contains several different requests.

## v3.1 Chinese product and latency comparison

Use `--scenario-set v31-zh` for the exact sequential A–E inputs: product idea,
Watt promotion context including three channels, backend correction, document
location, and next-design recommendation. The original English scenarios remain
available as `--scenario-set v3-en` (the default).

```text
python benchmarks/conversation_quality/pipeline_probe.py --run-real-provider --scenario-set v31-zh --label v31-after --output .spg/validation-evidence/collaboration-pipeline-v31-after.json
```

The benchmark observes SDK entry, thread/turn setup, first raw delta, closure of
the top-level natural-response string, terminal receipt, teardown, wire
validation, basis preparation and assessment return. The current service also
records exact-basis candidate validation, assessment commit, final persistence
start and completion after the final message/Turn commit. The SDK/network window
includes remote queuing and generation; it is not a measure of model compute.
Terminal receipt is the conservative semantic-envelope completion boundary when
the SDK provides no final agent-message item event. Failed observations do not
establish successful validation. Client SSE receipt differs from server yield.

For the initial v3.1 baseline probe, the SDK did not expose the expected final
agent-message item event. Its retained `provider_terminal_seconds` supplies the
same conservative full-envelope receipt boundary; raw wire size is unavailable.
The subsequent probe adds that explicit fallback without changing provider input.
Both script hashes are retained. Do not report the missing raw size as zero.

Review complete Chinese replies and their frames for naturalness, useful
hypotheses, one independent clarification, concrete recommendations with rationale,
context fidelity, correction handling and direct answers. A short questionnaire
is not a high-quality recommendation. Compare matched model/effort settings and
preserve unsuccessful experiments rather than selecting only fast samples.

Final v3.1 output evidence also records whether unchanged prior meanings and a
prior Design Intent Frame were explicitly reused. Reuse is validated and expanded
before domain admission; it does not suppress current facts or corrected frames.
The report compares a frozen v3 baseline, the first v3.1 trial (retained despite
mixed performance), and the final bounded refinement. Final source fingerprints
are checked against the delivered code, separately from benchmark script hashes.
