# C3 — bounded live-model verification decision

Status: **NOT AUTHORIZED / NOT EXECUTED in this round**. Prepared after exact-image qualification, not a new Work authorization.

## Qualified basis

- Watt source `e0df8196cb51480f542af13b40cfa77fca6b6a6e`, tree `d479d61f5fcac075a5af3a274f60cbe3f6e9f53f`.
- Actual isolated image `sha256:7a4ac00e3599bda2dbcebe46b15dd0b45f3be86552021023ebd288eb732f7b35`; 191 related regressions and 4 dedicated PostgreSQL tests PASS, with no source overlay.
- Guardian `d01bac1ad153e1eadefafe87d2ea4f5d65896ab6`; ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`. Neither changes for this verification.

## Exact input boundary

Read only the same already retained and sanitized C3 Work `048189aa-0613-5307-b6f4-c430e7977f93` inventory (26 sources, 12 existing capabilities). Reality `332a3a38-8719-580c-a1a2-c331ae14a5ae`; inventory `7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf`; canonical snapshot SHA256 `9b013274f1a6daafc776297a302c52c8247cd2fd5ec9c5b99a83279fd2ee8e2c`. Target source revision remains `465038ded6cf4ba335a11577de76acb1dea55b76`, target `index.html`.

Use the unchanged full immutable inventory and existing capability contracts with the new private wire. Formation request fingerprint `4b995573e01820631e063d0108388140be8576c3ac385a38da88d8ee87ea62d4`; table `cddd1ffc3429695d19411d42c5d6b741534460496705dbb0a430ff138df9e429`; schema `5668e226eb8d38c0f4bf9004ea8fc7aa363e9d388f64927783252f562d78ad40`. The offline reconstructed HTTP entity is 54,365 bytes; SHA256 `9e9e5ab4753c4e20115e721b2c933cd9db20a1c36a7744dd7e037073eea3041d`. Headers and actual transport framing are not included.

No Work 408 data, sealed Holdout, additional conversation, database access or business environment access. The request uses the existing DeepSeek endpoint and previously authorized test credential, kept in its existing protected file. No credential is shown or rotated.

## Calls, budget and stop

1. At most **one Formation** logical request.
2. Only if it passes the existing deterministic source, version, scope, component and current contract checks, at most **one independent semantic review** of that exact expanded candidate against the same immutable inventory.

Unchanged profile: `https://api.deepseek.com`, `deepseek-flash`, reasoning `low`, `max_output_tokens=16384`, timeout 120 seconds **per request**. At most 2 logical requests, with 32,768 configured output allowance across their observed responses. This does not identify the visible JSON/reasoning split or actual consumed tokens. Keep the existing adapter's one fresh-connection transport recovery before any first response event; at most 4 HTTP transmissions in the worst case. If every transmission was processed, their configured allowances would total 65,536; processing and billed usage of an unobserved transmission remain UNKNOWN. Report actual transmissions and UNKNOWN usage for unobserved outcomes. No semantic retry, Self-Refine request, budget reset, model route change or new Work.

Stop on the first provider/transport terminal, unsafe/unretained output, invalid wire/contract, unresolved binding, failed independent review or missing evidence. Do not retry to obtain a favorable result. A valid plan creates no Engineering Truth, Verification PASS, Guardian Assurance, Runtime Commit, sealed Candidate or Human decision.

## Evidence benefit and limits

The check can determine whether this exact revised representation completes within the existing profile on the same retained basis and whether actual reasoning/output/total usage is available. It can qualify an isolated model-derived fulfillment plan only when the unchanged independent review also accepts it. It cannot reconstruct the original historical failure, prove arbitrary-input generalization, replace the real G0 or sealed Holdout, or close C3.

Persist safe hashes, identities, stage events, actual usage/UNKNOWN, failure predicates and bounded call counts publicly. Any permitted safe candidate/review text stays in the existing protected evidence directory, excluded from Git/public reports. Do not store hidden reasoning, raw HTTP/private Provider bodies or sensitive prompts.

This round expressly requires a new Human decision before this check. Earlier broad authorization is not substituted for that instruction.
