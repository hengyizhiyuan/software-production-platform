# Ordinary G0 source binding root cause review

Status: historical failure preserved; repair and final qualification in progress. This is not C3 closure.

## Exact observation

- Watt: `7820ec05ca20b2421f99c82eaf906cf539eb05f6`, tree `56cbb29b639d38ab1bb0ef668693b4119ff4e817`.
- Actual image: `sha256:18a0e4454195c043aa2a5354a8be53a4c35bdf54e529dfd479b95275ff6c85b4`.
- Guardian: `76c1e87a1b29d151f4ed949748e3298f2169c5b1`; ECF: `5aa4f8833c359c15bd059eda5972aa3915bcc18c`.
- Work `411ea9e0-3bf7-58e2-aa9d-5eabf8d59bab`; Reality `d0f91d5a-a260-58ec-a55c-a3672013dd49`.
- Inventory `4ff42fb04918efff1679c15d83fe786838093a23d6cc86b0a7762362b2c10d80` (19 sources / 12 capabilities; the new legitimate Work has its own inventory, not the older 26-source diagnostic).
- Actual terminal: `OBLIGATION_COMPONENT_REVIEW_IDENTITY_DRIFT`; no PWU, Native Attempt, Worker output, Candidate Seal, Runtime Commit or Human authorization.
- Immutable raw export SHA256 `15152aa2a034ed024e7337abc1964f195ba32b447e59c5e72e7a0bb778fd8616`.

## Per-source responsibility and observed failures

Ordinals below refer only to this exact inventory; no ordinal or wording is encoded in application logic.

| Source | Legitimate responsibility | Observed failure | Classification |
|---|---|---|---|
| 3 | Current artifact outcome | F1 added Candidate Seal, not entailed by this contribution | Model mapping error; independent Review correctly rejected |
| 8 | Continuous effect prohibitions plus authorized file-change scope | F1 selected Artifact Content for those restrictions | Model mapping error; independent Review correctly rejected |
| 10 | Current requested implementation/content; exact corresponding Fact and actual content consumer evidence | F1/F2 chose Git Diff; F2 Review reason described Artifact Content while approving submitted Git route | Model mapping error plus Review false release of a semantic mapping; never an admitted PASS |
| 11 | Current paragraph/content outcome; its exact corresponding Fact and content verification | Same unchanged wrong Git consumer | Same |
| 12 | Current implementation requirement with qualified file scope; content and actual scope Gate must both remain covered | Same unchanged wrong Git consumer | Same |
| 13 | Candidate boundary through Candidate Owner Seal Gate with original source proof | F1 chose Git Diff | Model mapping error; independent Review correctly rejected |
| 6 | Git Diff scope with exact component identity | F2 Review copied a different 64-character component ID | Output identity violation; Owner correctly refused. Model internal cause UNKNOWN |

First-to-second feedback bytes and parent receipt identity match. Incorrect mapping remained unchanged after feedback; this is not feedback identity drift. Correcting the copied ID alone cannot legitimately qualify F2 because sources 10–12 remain misrouted. Structural rejection, semantic mismatch and independent Review error are separately retained.

An independently constructed, separate structural analysis demonstrated that the existing contracts can represent all sources (22 bindings, `REPRESENTABLE_REVIEW_PENDING_ONLY`). It did not mutate either historical Candidate, perform independent semantic Review, obtain actual content/Scope/Gate evidence or produce PASS. Linked `f` proof and provenance `u` are different: provenance cannot transform a Git consumer into content verification. Full semantic sufficiency and subsequent actual Owner evidence remain required.

## Narrow repair boundary

1. Review each actual submitted component before bulk Owner tables, with original identity slots, full declared Fact operands and actual consumer proof boundary. Response identities are singleton slots; verdict predicates remain independently decided.
2. Bound feedback exposes the rejected actual consumer and unchanged component/source identity, rather than implying a cosmetic rationale/provenance change repairs a wrong consumer. Original Wire/inventory/attempt/receipt lineage is retained.
3. Existing static plan repair handles a natural-language Scope through original Work target contract, exact source quote, deterministic method/value/qualifier checks and a second independent plan review, using the existing two-candidate budget. Original Fact and Scope are not rewritten. Actual Git blob and deterministic content parser still decide content PASS/FAIL.
4. Existing Guardian independently consumes matching Fact/Work/source/target evidence; no Guardian authority or contract weakening is introduced.

No alias table, changed semantic truth, new Owner, elevated permissions, increased budget or Holdout tuning is involved. New view requests are version-bound; historical v1 requests and terminal receipts remain reproducible.

## Actual cost and evidence grade

Four completed Formation/Review calls: input 161418, output 15170, cached 7552, reasoning 0, total 176588 Tokens. Separate DESIGN use is not counted as Formation cost. JSON-only token count and monetary cost UNKNOWN. No observed capacity/transport failure in these four calls.

- Historical actual Owner records and Provider usage: persisted observation, not inference.
- Independent lawful-domain probe: deterministic representability only.
- Review reason vs submitted consumer disagreement: private retained exact outputs, safe public identity/predicate hashes in the independent audit.
- Internal model cause of identity copying and first Gitea startup latency: UNKNOWN.

## Recovery locations

Public evidence is committed on `codex/c3-open-semantic-obligation-convergence` under this directory. Original evidence, private quotes/Candidates and readonly audit controls remain at:

`/data/watt/c3-semantic-convergence-20261009/binding-g0-generation37-qualification-20261010`

Private raw export: `private/owner-export-20261010T194136-8b961eaf7988431281176b4054dd0f5d/20261010T194138815824Z-18d2a5cedc744855a990505cca372e54-canonical-work.json`.

Independent private audit: `private/independent-source-binding-audit-20261011/`. Public audit SHA256 `b35055fbd3773c14a99b1c07169a54dd302df76b2b43cae45742393286b7e216`.

No historical Work, Candidate, Human Decision, production source or production service was changed. Future successful evidence cannot retroactively make this Work PASS.
