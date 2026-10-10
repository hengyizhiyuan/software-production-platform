# Exact readiness gate — generation 46

Application source `49b5bd42c2bb499848740b9ce4a595a8f2049b0d`, tree `014527f987e6db2bda4c3e42d67cd021b806da14`.
Actual newly built image `sha256:9eea19fd586c8b5e801cc3bcadc75cdb9bb83ad6b53c112220aabd2cbcae456d`.
Guardian `76c1e87a1b29d151f4ed949748e3298f2169c5b1`; ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`.

## Completed gates

| Gate | Actual outcome | Boundary |
|---|---|---|
| New frozen-source image build | PASS; 76.27 seconds | Strict archived lock, exact Git inputs; no runtime source overlay |
| Actual installed imports | PASS | Recorded source/Owner identities, not requested identities alone |
| Installed regression suite | 750 PASS / 0 FAIL / 0 ERROR / 0 SKIP; 226.02 seconds | Network disabled; zero model calls, no real Work |
| Fresh PostgreSQL regression | 40 PASS / 0 FAIL / 0 ERROR / 0 SKIP; 373.03 seconds | Migration `20261007_72`, isolated fixtures; no source/test overlay |
| C1 independent Guardian paths | Both actual admission paths passed inside the PostgreSQL suite | Existing independent Guardian contract retained |
| Generation41 historical identity proof | PASS, 23 original sources | Zero model calls, old identities unchanged, retrospective upgrades refused |
| Generation42 terminal replay | PASS, original terminal retained | Zero model calls; does not convert failed Work into success |

The three prior PostgreSQL identity-tamper failures now pass on the exact newly installed application. The original generation45 failed receipt remains unchanged. Development source-overlay tests and the generation45 fixture-only correction are separately reported and are not used as installed generation46 qualification.

## Remaining qualification

The ordinary G0 and independent Holdout are not certified by this readiness gate. The ordinary normal-input chain must still create actual Worker/Git/Verification/Candidate and applicable independent Guardian evidence while preserving pending Human decisions. Holdout stays sealed until that production boundary qualifies. Controlled expressibility and structural refusal tests do not prove semantic model success.

## Persistence

Public receipts: `manifest.json`, with exact SHA256 and original paths. Frozen inputs, image/build, PostgreSQL volume and private replay bases persist under `/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/g0-binding-generation46-qualified-20261010/`. No private Human conversation, Provider response body or credential is included in this report. Dollar cost is UNKNOWN. These readiness tests used zero live model calls.
