# Semantic contribution compilation — non-Holdout qualification protocol

2026-10-14 (Asia/Shanghai). Fixed before any model call. C3 remains PARTIAL.

## Subject

Application source `f9519044cd6ac1c18e4c5894d56258156d5f47dd`, tree
`16643e80baa40166126c8d71e9ba3f7640445a3b`, on `claude/c3-formation-ai-native-convergence`.
Contract marker `formation-semantic-contribution-compilation-v1`. Image built offline from
the exact source archive with the existing C3 Dockerfile and frozen Guardian/ECF inputs.

## Samples and budget

Only the two existing non-Holdout development inventories:
`ordinary34` (19 sources, `b023bae8…`) and `ordinary41` (23 sources).
Each trial is a complete fresh bounded Formation: both candidates are real model calls,
plus any Review the unchanged gates permit (≤4 logical calls). No retained first response.

Three trials per inventory, six in total, fixed in advance. Estimated ≤ 1.2M tokens;
hard stop at 2.0M actual tokens. No retry of a failed trial, no tuning between trials,
no code change during the batch. Holdout inputs are not read.

Model: deepseek-flash, reasoning none, max_output_tokens 16384, timeout 120s, existing
transport behaviour. Isolated container: no database, no Docker socket, read-only inputs,
non-root user, no source overlay.

## Pass criteria (fixed)

1. **False admission = 0 (hard).** Any admitted projection is independently re-validated
   offline against the unchanged `validate_projection_candidate` and the persisted
   independent Review; any admitted plan containing a duplicate component/consumer,
   coverage loss, invalid source correspondence or a negative Review is a failure of
   the whole qualification.
2. **Owner compilation never attaches a non-punctuation character** in any trial
   (checked over every `geometry_compilation.attachments` entry against source text).
3. **Recovery/identity**: every terminal replay issues zero new calls; budgets never
   exceed two Formation candidates and four logical calls.
4. **Capability signal (reported, not a closure gate):** count of trials reaching
   independent Review, and admitted. Baseline for comparison: all prior recorded
   non-Holdout trials of the current role-construction path reached Review at most
   once (trial15) and were never admitted.

Generalisation is not claimed from six trials; independent Holdout requalification
remains the separate `.c3-holdout-reviewer` responsibility.
