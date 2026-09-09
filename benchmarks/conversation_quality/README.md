# Conversation Quality Benchmark

This benchmark is a reusable Human–Watt conversation-quality corpus. It covers
36 representative interactions across Chinese and English conversation modes.
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

## v3.2 continuity measurements and fixed-input comparison

The probe now retains every received text delta's elapsed time and character
count, the first complete sentence's time/text, the largest gap between
non-whitespace text deltas, and the last text delta to successful completion.
Sentence completion uses punctuation, including Chinese punctuation: it does
**not** establish that a sentence is useful, relevant, or already answers the
question. Review the actual sentence and complete answer. Shorter answers are
not inherently better. The delta-gap measurement excludes initial waiting and
the final semantic tail; a single text delta has no measurable inter-delta gap.

`natural_response_closed_to_completion_seconds` separately measures the interval
from the provider's observed response-string closure to completion. HTTP reports
measure client receipt of final persisted completion; replay reports measure
provider candidate validation. Do not combine those completion boundaries.
Resets are recorded explicitly and never create first-text or first-sentence
timings. Initial streamed text remains historical evidence after a reset; tails
against replaced content are unknown. Failed turns retain first-text/first-sentence
observations and delta sizes/timings, but have no successful completion/tail.
The full rejected response/envelope is not archived by this probe. Provider call attempts and per-call configured
model/effort, prompt hash and size accompany successful pipeline provenance.

`--scenario-set v32-zh` extends the original Chinese A–E conversation with budget
and deadline limits, a rejected recommendation and deferred question, a changed
operator scope, and a detailed-answer request. `--corpus-case ID` instead runs
one corpus case's Human messages in sequence, using `expected_intents` where
present. The six `evaluation_group=v32_multiturn` cases are suitable for a wider
quality check; the case's `review_guidance` still requires human judgment.

```text
python benchmarks/conversation_quality/pipeline_probe.py --run-real-provider --scenario-set v32-zh --repeat 2 --label v32-sequential --output .spg/validation-evidence/v32-sequential.json
python benchmarks/conversation_quality/pipeline_probe.py --run-real-provider --corpus-case priority-solo-deadline-multiturn-zh --label priority-review --output .spg/validation-evidence/priority-review.json
```

Each repetition uses a new Interaction in the initially empty isolated database.
`--cases 1,3,4` marks those turns as selected but executes the complete prefix
through turn 4 to preserve conversational context. Report every call, including
context-building turns; no failed turn is silently retried. Separate probe
invocations still require separate fresh databases.

Each case stores the complete input `basis` and its `basis_sha256`. These are
benchmark inputs from the isolated synthetic conversation, not extra product
memory. Use one saved report to replay the **same** input under each source,
model or effort condition, removing drift caused by earlier generated replies:

```text
python benchmarks/conversation_quality/replay_probe.py --run-real-provider --input .spg/validation-evidence/v32-sequential.json --cases 1,3,4 --source-repetition 1 --repeat 2 --label fixed-default --output .spg/validation-evidence/fixed-default.json
python benchmarks/conversation_quality/replay_probe.py --run-real-provider --input .spg/validation-evidence/v32-sequential.json --cases 1,3,4 --source-repetition 1 --repeat 2 --semantic-effort low --conversation-effort low --label fixed-low --output .spg/validation-evidence/fixed-low.json
```

Replay requires explicit Provider authorization but no database. It validates
recorded hashes and creates an independent domain input for every call; generated
answers never become another replay's history. It retains complete validated
candidate semantics and replies; failed attempts retain their error, first-sentence
and timing observations, not a complete rejected envelope. It does not admit
results or execute production. Cases run serially in repetition order. Use both
effort options together to preserve eligibility for the single-call path; changing
only one effort can switch to the staged path. Record actual call counts, compare
source/prompt/input hashes, and repeat in alternating condition order before
attributing a difference to one change. These small samples do not establish p95.

The [v3.2 sample artifact](../../docs/evidence/human-collaboration-experience-v32-samples.json)
preserves the original immutable replay inputs even when ignored raw reports are
unavailable. Extract an input report without calling a Provider:

```python
import json
from pathlib import Path

artifact = json.loads(Path("docs/evidence/human-collaboration-experience-v32-samples.json").read_text())
Path("/tmp/watt-v32-replay-input.json").write_text(
    json.dumps({"cases": artifact["immutable_replay_inputs"]}, ensure_ascii=False)
)
```

Pass that file as `--input` with `--cases 1,3,4,5` after authorizing a real run.
The extracted report's file hash differs from the original full report; each
canonical basis hash remains identical. Final A–E HTTP results use their own
generated history and must not be confused with these original fixed bases.
