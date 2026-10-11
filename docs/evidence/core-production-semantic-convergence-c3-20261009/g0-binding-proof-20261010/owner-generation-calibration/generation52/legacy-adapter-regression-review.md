# G52 installed regression refusal: legacy Owner contract negotiation

Source: 41635093b03b729d07816a77049409c96ec05ac1.
Image: sha256:bd3814062d20ea15a5fef1b191f56658de3724300402733ba129876509e3b30a.
Installed regression: 870 tests, 866 passed, 4 failed, no errors/skips; 344.58 pytest seconds. The original receipt is retained. No real model, Work or Holdout was run.

All four failures arise in historical compatibility adapters: v6, v7, v9 and deliberately omitted typed observations. Fresh request preparation passed the current-only exclusion-content marker before the actual adapter contract was returned. The existing strict Owner contract validator correctly rejected those incompatible combinations as OBLIGATION_FORMATION_REQUEST_VIEW_CONTRACT_INVALID. Consequently the tests could not reach their historical success or conflicting-disposition terminal boundary.

This is an application negotiation ordering regression, not missing source evidence, a model mapping error, a Review verdict or an artifact failure. The remedy negotiates current exclusion eligibility only after the actual returned Owner contract proves v11/v5/v2 compatibility. Necessary source proof domains are recomputed under that exact marker. Existing historical requests continue to use their stored marker (including absence); the validator stays strict. No historical receipt or terminal is rewritten.

Directed qualification targets the original four failed cases plus current/legacy negotiation, exact replay and independent critic-feedback identity. A new frozen revision and complete installed image qualification are required before real G0. This failed image is not a final delivery qualification.

Directed development qualification completed: 35/35 passed, no errors or skips. Controlled overlay only; not final installed image, real model or Work qualification. Receipt: adapter-negotiation-directed-receipt.json.
