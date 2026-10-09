# P0 — One authorized exact inventory diagnostic

## Actual evidence and scope

Historical C3 Work `048189aa-0613-5307-b6f4-c430e7977f93`, Reality `332a3a38-8719-580c-a1a2-c331ae14a5ae`, inventory `7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf` was reconstructed from the already redacted canonical Owner export, SHA256 `9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c`. It is not Work408 data. Human explicitly authorized this one external-send diagnosis. The first rejected execute command never ran; actual directory/container absence was checked before the single execution.

The diagnostic ran outside any Work application, in retained application `d8ea0642f0c360794e69c366e8f15fa369eeed0b`, actual image `sha256:51c0b8be88969720cb3a3cfc4e047edc7f229aa22348a95a89cbb4bf83a18e39`. Only provider credentials, read-only basis and diagnostic code, plus a new evidence directory were mounted. No business DB, Work mutation, admission, Candidate or Assurance action occurred. See [actual diagnostic](historical-provider-diagnostic-1/provider-diagnostic.json) and [actual container](historical-provider-diagnostic-1/container-identity.json).

## Confirmed current result, historical UNKNOWN

On **2026-10-09 15:06:57–15:07:53 UTC**, the request was queued and sent. HTTP **200** was observed at 15:07:01.190498 UTC, followed by a first response event. The terminal response was `incomplete`, with reason `max_output_tokens`, normalized `INCOMPLETE_RESPONSE`, request ID `d504da81-846e-45a1-8411-1f5b6edb2c08`. This was a sent request with an incomplete Provider response, not a proved HTTP rejection, timeout or local pre-request failure. No candidate output contract was reached. One logical model entry and zero transport recovery stages were observed; the old typed error did not retain an exact numeric replay counter.

The unchanged profile was DeepSeek / `deepseek-flash` / `low`, timeout 120s, maximum output 16384. Wall time **56.328976289s**. No output-token budget, timeout, request meaning, validation or retry count was increased. The old typed error reports `usage_unknown=false`, but discards its parsed numeric usage before raising. Numeric token consumption is therefore **UNKNOWN**, not 0 and not an inferred limit value.

This does **not** establish that the historical second G0 failure had the same cause. Historical HTTP status, terminal reason, request ID and numerical usage remain UNKNOWN. The separate synthetic connectivity probe's HTTP 200 and 156 observed tokens only prove that its small benign request was processable; they do not replace this inventory test.

## Bounded corrective boundary

A minimal failure-observation correction now retains actual terminal `ModelUsage` and actual transport counter on the existing typed error, safely projected by the existing Provider/Verification receipt mechanism. Missing or invalid values remain `None`/UNKNOWN. Existing HTTP failure metadata is preserved without response prose; no retry, permission, schema or model output is fabricated. Controlled SSE regressions qualify the future observation correction separately from this old-image diagnostic.

The observed output-limit failure itself has **no proven C3 implementation fix under the unchanged request and budget**. Candidate representation overhead, model behavior and Provider capacity have not been causally separated. Do not label them a specific software defect or randomly create another Work. The next necessary step is an evidence-backed capacity/representation review or an actual Provider condition change compatible with the approved constraints. There is currently no basis for another normal G0 attempt.

## Recovery and claim boundary

Public receipts are committed with this continuation. ECS persistence is `/data/watt/c3-semantic-convergence-20261009/continuation-20261010/historical-provider-diagnostic-1/evidence/`; private credential/log files remain under the same run's `private/` and are never Git content. The directory name is an identifier; the actual timestamps above identify the observation date.

**P0 remains BLOCKED for successful real G0; historical cause UNKNOWN.** R1 and R2 are independently qualified corrections, not an assertion that Work408 or Provider formation succeeded. Holdout remains sealed and this amendment is not unseal permission.
