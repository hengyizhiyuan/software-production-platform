# M0 baseline: Golden Journeys 1 and 2 on the live composite (2026-10-15)

Live ECS composite runtime: one image for api, coordinator, tool-host and worker, with
Guardian and ECF pinned in `owners.lock`. Drivers:
`benchmarks/golden/runtime/golden_journey.py` and `run_golden.sh`. They use the
public API only, apply controlled authorization and acceptance (Human Governor
decision 4), and answer Watt's questions with "按你的建议来".

## Outcome

| Journey | Runs | Result |
|---|---|---|
| G1 minimal page with a button that alerts "hello Watt" | 8 | Run 8 delivered end to end in 184 s. Runs 1–7 each stopped at a breakpoint listed below. |
| G2 static page with an exact title, an exact paragraph, and exclusions | 1 | Formation exhausted both attempts. Work stopped in PRODUCE before execution. |

The Human observed run 8 in the Watt UI: the Work was completed, and the
delivered page could be previewed and downloaded. The delivered `source/index.html`
contains `<button onclick="alert('hello Watt')">`.

## Breakpoints found and fixed in M0

| # | Breakpoint | Root cause | Fix |
|---|---|---|---|
| 1 | `POST /api/experience/intent` hung for more than 120 s | The streaming adapter's timeout bounded each read, not the whole inference. During the DeepSeek incident the Provider sent only keep-alives. | Watt `41250303`: every streamed inference has a total deadline. |
| 2 | Formation never produced a candidate (10 of 10 calls on 10-07 and 10-15) | The formal compose used reasoning effort "low". C3 qualified with "none". Flash spent all 16384 output tokens on reasoning. | Watt `1bd2b968`: release compose carries the C3 provider profile. |
| 3 | Native ended UNABLE_TO_COMPLETE in 1.5 s with zero tokens | The execution view hashed the Formation Owner's compact and materialized forms of one receipt literally and saw identity drift. | Watt `d24a149c`: identity is compared in compact form; a restored field must hash to its reference. |
| 4 | Guardian BLOCKED every protected obligation (CONTEXT_COVERAGE_GAP) | Same compact vs materialized receipt comparison in `_component_plan_evidence`. | Guardian `828641a`. |
| 5 | Guardian BLOCKED again on a reviewed v3 plan | Watt admits the Candidate seal without an acceptance goal under v3. Guardian required `acceptance_required` for every future-phase binding, in two duplicated places. | Guardian `03caa0e`: one rule, used in both places. |
| 6 | Release reported success but services kept the old images | Leftover image-pin overrides were still applied. `docker compose run` consumed the heredoc that held the remaining remote script. | `release_to_ecs.sh`: uses the base compose only, runs an uploaded script with stdin closed, checks the image ID of every service, and requires the `RELEASE_REMOTE_PASS` marker. |
| – | Host CPU about 70% from 10-15 00:17 | The C3 api image lacked the hot-fix that removes `docker system df` from the Admin sampler. | Both live hot-fixes (Admin sampler and Worker idle poll) are now in source. Host is back to about 12%. |

## Open breakpoints (assigned to milestones)

| Breakpoint | Evidence | Milestone |
|---|---|---|
| Formation is stochastic and can exhaust its budget | G1 run 7: attempt 1 hit CONFLICTING_DISPOSITION; attempt 2 was rejected by the independent Review, which judged that Git-scope and seal routes added to plain content constraints went beyond the source. G2: attempt 1 hit SOURCE_CONTRIBUTION_LOST; attempt 2 hit CONFLICTING_DISPOSITION. G1 runs 4, 6 and 8 passed. | M3 (Formation contract convergence). M2 handles the dead end. |
| An exhausted Formation leaves the Work silently READY in PRODUCE | G1 run 7 and G2: no Attention, no Human-visible reason, the Work does not advance | M2 (no dead ends) |
| A single Watt reply repeats the same paragraph, ends with "当前说明暂时无法安全展示", and mentions scope that was never requested | G1 runs 1 and 5 | M1 (conversation intelligence) |
| The first chat reply takes 99 s (G2) and 46 s (G1) | See the turn timeline below | M1 (P-1, P-2) |
| `delivery-manifest.json` and `verification.json` are about 2 MB each for a 322-byte page | G1 run 8 delivery | M3 |
| Workspace read takes 1.2–1.4 s around candidate formation and publication (0.1–0.4 s otherwise) | G1 runs 6 and 8 | M1 (read-model projection) |

## Performance timeline: G1 run 8 (end to end)

| Stage | At | Segment |
|---|---|---|
| Intent routed (product created) | 2 s | 2 s |
| Work admitted | 30 s | 28 s |
| PRODUCE (design closed) | 43 s | 13 s |
| Formation done, Native RUNNING | 70 s | 27 s |
| Candidate formed, Guardian running | 151 s | 81 s |
| Guardian PASS, authorization requested | 160 s | 9 s |
| Preview ready, controlled authorization | 171 s | 11 s |
| Integration and delivery published | 176 s | 5 s |
| Work COMPLETED | 181 s | 5 s |
| Downloaded (446 KB, 0.64 s) and accepted | 184 s | 3 s |

Native execution took 16.2 s and used about 113 k tokens (2.4 k output) in G1 run 4.

## Performance timeline: G2 first chat turn (server stages)

| Stage | At |
|---|---|
| Turn acknowledged | 0.04 s |
| Reality loaded | 0.21 s |
| Provider first token (assessment, non-streamed) | 1.58 s |
| Semantic payload validated | 74.5 s |
| Assessment persisted | 74.6 s |
| Realization started | 84.3 s |
| First response delta (first visible text) | 99.4 s |
| Completed | 99.7 s |

The Human sees nothing for 99 s. A full non-streamed assessment call runs in
front of the first visible token. The frontend then polls every 2.6 s and
re-reads the whole workspace instead of subscribing to the existing SSE stream.

## M1 starting facts (read-only survey)

- `experience.js` uses only polling: 2600 ms per turn, plus a full workspace
  re-read on each poll. It never uses the existing SSE endpoint.
- `POST /intent` makes one synchronous routing model call in the request thread.
- Every turn of every interaction runs on one global worker thread
  (`ThreadPoolExecutor(max_workers=1)`, `interaction.py:741`).
- The SSE endpoint polls the database every 50 ms. Each response delta takes a
  row lock and writes one row.
- The home page shows 4 products, 5 Works and 5 attention items, but each load
  projects up to 300 Works.
