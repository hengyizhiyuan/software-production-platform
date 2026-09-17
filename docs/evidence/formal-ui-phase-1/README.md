# Formal UX/UI Phase 1 — Industrial Cyan fidelity and Human Retest evidence

Date: 2026-09-17

Status: `CLOSED / PASS`

Human Product Acceptance: `PASS`

This evidence records the revised Formal UX/UI Phase 1 scope and the
reference-driven Industrial Cyan reconstruction. The Human Governor completed
the final retest, accepted the current functional result, and reported no
additional phase-blocking finding. The broader E2E closure is recorded in
[First Human-validated Watt End-to-End Software Production Loop](../first-human-validated-end-to-end-production-loop.md).

## Source and runtime identity

- Start/current committed revision: `20ce750c8afac912468bba56b8ee9ebfbf0fe8c5`
- Trusted Baseline tree: `9660dcca0a71647f04325b19a61bd0eeaa40216f`
- Clean Human Retest runtime: `watt-formal-ui-fidelity-retest`
- Runtime state: `ACTIVE_AT_TRUSTED_BASELINE`
- Human Retest URL: `http://127.0.0.1:8049/app`
- Seeded comparison Work: `7e592f43-4714-4bd4-babe-1ea31ae5cf4d`
- Migration current/head: `20260915_41`

The runtime has a dedicated Compose project, network, PostgreSQL volume, and
Runtime volume. Its formal UI source is the read-only current working-tree
overlay mounted at `/acceptance-source`; Phase 1 changes remain intentionally
uncommitted pending Human retest.

## Revised appearance scope

The current production Workspace Skin is only:

- `INDUSTRIAL_CYAN`

The selector exposes no unfinished choice. The other five stable identities
and exact assets remain preserved as `FUTURE_EXTERNAL_ASSET_DOGFOOD` for a
future External Design / Asset Ingestion capability. This scope correction
does not reject the two-scope appearance architecture. Ordinary pages still
use only `GLOBAL_LIGHT` / `GLOBAL_DARK`.

## Authoritative target and comparable evidence

- [Authoritative reference](../../assets/ui-skins/01-industrial-cyan.png)
- [Before fidelity pass](industrial-cyan-before-fidelity-pass.jpg)
- [Final fidelity-pass comparison](industrial-cyan-final-fidelity-pass.jpg)
- [Clean Human Retest runtime](industrial-cyan-human-retest-ready.jpg)

The before and final fidelity-pass captures use the same explicit 1450 × 1086
CSS viewport request, seeded Work, Work status, Current Interaction history,
and surface order. The in-app browser emitted 1435 × 971 and 1450 × 981 raster
bounds respectively because the old page required scrollbars while the rebuilt
composition fit the viewport; this platform difference is recorded rather than
misrepresented as a pixel metric. The clean-runtime capture demonstrates the
isolated acceptance state.

```text
VISUAL_FIDELITY_TARGET
    APPROX_90_PERCENT_HUMAN_PERCEIVED

VISUAL_FIDELITY_RESULT
    HUMAN_ACCEPTED
```

No fabricated numerical score is claimed. Human acceptance is the authority
for the qualitative fidelity result.

## Major differences found

The first implementation retained the old page composition and mainly changed
tokens. Compared with the approved reference, it lacked the narrow industrial
navigation rail, engineered topbar and Work header, compact control-room
proportions, framed four-surface geometry, continuous Conversation History
rail, dense instrumentation hierarchy, integrated Human controls, and a
reference-like lower interaction/composer zone.

## Major corrections made

- rebuilt the active Work shell into a narrow rail plus central Workspace and
  full-height provenance rail;
- reconstructed the topbar, Work header, 2 × 2 Workspace geometry, chamfered
  framing, cyan/amber status hierarchy, dense fact rows, and material texture;
- embedded observed result facts in Production and Human Authority/Attention
  controls in Actions instead of repeating disconnected cards below the grid;
- compacted Current Interaction and Composer into the lower operational zone;
- made current messages visible in the Conversation History rail while
  retaining Current Interaction;
- retained Human-controlled surface Focus, stable semantic order, responsive
  stacking, WIC behavior, Work identity, and product/domain state;
- limited the runtime registry and Human selector to Industrial Cyan while
  preserving all six canonical reference identities.

## Known remaining differences

- the reference uses purpose-designed iconography and bespoke metallic artwork;
  the current implementation uses bounded CSS geometry and system glyphs;
- actual Watt Work facts differ from the illustrative Customer Support content
  in the visual reference;
- the current semantic detail disclosure remains available below the stable
  four surfaces rather than being removed for pixel imitation;
- exact typography differs because no licensed/reference font asset was
  supplied;
- browser-native select and scrollbar rendering can vary by platform.

These differences are attributable to real product semantics, missing source
assets, browser/platform rendering, or deliberate bounded simplification.

## DeepSeek runtime recovery

The previous credential failure was caused by the Human Retest app container
not receiving the configured local `SPG_DEEPSEEK_API_KEY` or the intended WIC /
Conversation provider adapter settings. The local-only runtime overlay now
injects the existing ignored credential and configures:

- provider: `deepseek`;
- model: `deepseek-flash`;
- credential: available, never printed or committed.

One bounded probe on the earlier isolated `watt-formal-ui-phase1` runtime
completed with Interaction status `COMPLETED`. The final 8049 Human Retest
runtime uses the same configuration but contains no automated Interaction or
Provider facts.

## Clean Human Retest data guard

The 8049 runtime contains exactly:

- Goals: 1
- Works: 1 (`AWAITING_APPROVAL`)
- Interactions: 0
- native execution queue entries: 0
- execution attempts: 0
- provider execution reports: 0
- runtime commits: 0

No production execution, Provider probe, approval, Runtime Commit, or Trusted
Baseline mutation was created for the final Human Retest environment beyond
normal initial bootstrap and the representative Goal/Work draft.

## Focused verification

- JavaScript syntax checks: PASS
- focused Node appearance/response tests: PASS
- focused Python UI contracts: PASS
- DeepSeek real Interaction probe: PASS
- `/health` and `/app`: HTTP 200
- app and PostgreSQL containers: healthy
- Alembic current/head: `20260915_41`
- `uv lock --check`: PASS
- `git diff --check`: PASS

The earlier focused verification above remains historical pre-acceptance
evidence. Closure subsequently ran the complete Linux/PostgreSQL Python suite,
Node/Web suite, OPEN_WIC, Alembic, compile/import, lock, and diff guards; the
exact counts are preserved in the canonical E2E closure record linked above.
