# Waterfall Demo CSP Loop and Guardian Recovery

This document records a Human Dogfood incident as durable architecture learning.
It complements the regression-protection decision already recorded in
[`watt-regression-protection-and-golden-journey-governance.md`](../watt-regression-protection-and-golden-journey-governance.md):
the Preview passive-resource defect strengthens `GJ-01 Greenfield Production`
rather than creating an incident-specific Golden Journey.

The case is evidence for future Guardian responsibilities and for a stronger
distinction between completed implementation activity and a usable Human outcome.
It does not authorize Guardian implementation or any product, Runtime, or test
change.

## 1. Case summary

The Human asked Watt to produce a simple HTML waterfall page with these visible
outcome requirements:

- use real lifestyle and person photos;
- be previewable in Chrome through the Watt Preview served on `127.0.0.1`;
- present an Instagram- or Xiaohongshu-like visual tone; and
- preserve the requested waterfall layout as the page content grows.

The operative acceptance condition was therefore a browser-visible page with
rendered photographs and the intended visual composition. Producing an HTML file,
or proving that the layout markup existed, was only an intermediate result.

## 2. Observed symptoms

The waterfall structure and much of the intended card layout were produced, but
the photographs repeatedly failed to display in the actual local Preview. The
Human continued to see empty or failed image regions even after multiple repair
attempts.

The attempts changed image sources, discussed external-host allowances, and
adjusted artifact-level handling, yet did not promptly converge on a working
browser result. The system kept making locally plausible changes while the same
user-visible failure survived. Progress existed at the artifact and execution
levels, but the outcome the Human requested remained broken.

This produced a local-fix loop:

```text
broken image in Preview
  -> revise a nearby artifact detail
  -> produce another candidate
  -> observe the same broken image
  -> revise another nearby detail
```

The loop ended only when diagnosis moved from the page content to the effective
Preview environment and its browser-enforced policy.

## 3. Why this case matters

This was not only a front-end defect. It exposed a system-level gap between
execution activity and Human success.

An Executor can continue to edit files, replace URLs, and produce candidates while
the result visible to the Human remains unusable. Each action may be reasonable in
isolation, but continued activity is not evidence of convergence. When successive
attempts preserve the same acceptance failure, the system needs to treat that
continuity as evidence about the strategy, not merely as another request for a
local patch.

The case also shows how an execution route can become a dead end. If the active
hypothesis remains inside the artifact while the blocking condition belongs to the
Preview Runtime, further artifact edits cannot reliably solve the problem. The
system needs to recognize repeated failure, challenge the current explanation, and
escalate diagnosis to the layer that owns the observed behavior.

That is direct motivation for Guardian capabilities. Independent assurance must be
able to ask whether the claimed result works for the Human, whether the evidence is
sufficient, and whether repeated repairs are changing the relevant condition.

## 4. Failure pattern

The observed pattern was:

1. The missing images were initially discussed as an external-image,
   cross-origin, source-host, or hotlinking problem.
2. Repair stayed local to the artifact: image sources were switched, allowlists
   were discussed or added at page level, and fallback behavior was considered.
3. These changes were plausible but did not test the effective browser policy at
   the layer serving the Preview.
4. The real Preview response supplied an HTTP Content Security Policy containing
   `img-src 'self' data:`. That policy was enforced cumulatively with the
   artifact's own policy, so an artifact-level allowance could not relax the
   response header.
5. Because the governing restriction was outside the edited page, repeated local
   changes did not stably converge. Higher-level inspection of the served response
   and browser-visible result was required to locate the controlling layer.

The repository's canonical regression record classifies the root cause as Preview
passive-resource capability being narrower than the admitted artifact. It also
preserves the corresponding invariant: Watt Preview must support artifact-required
passive HTTPS images while retaining active-resource boundaries.

The important pattern is broader than CSP. A system can repeatedly repair the
wrong layer when it does not compare the current hypothesis with unchanged
user-visible evidence.

## 5. Root lesson

> First try to do it right; if wrong, detect the failure; after repeated failure,
> change strategy; eventually converge instead of looping forever.

The first attempt does not need to predict every environmental constraint. It does
need a meaningful outcome check. A failed check must remain visible as a failed
obligation. If another materially similar attempt produces the same failure, the
system should reduce confidence in its current explanation and investigate a
different layer or route.

Convergence therefore requires more than persistence. It requires feedback that
can invalidate a strategy.

## 6. Guardian implications

This case gives the future Guardian role several concrete assurance duties:

### Validate the Human-visible outcome

Guardian evidence should answer whether the exact Preview works in the relevant
browser environment. File creation, command success, and candidate generation do
not establish that external images rendered for the Human.

### Detect repeated failure across attempts

Guardian should retain the acceptance failure across execution attempts and
recognize recurrence. Repeated observations of the same blank-image outcome are a
series, not unrelated incidents. The series should become stronger evidence that
the current repair strategy is ineffective.

### Escalate strategy when execution is stuck

When multiple materially similar repairs leave the same obligation unsatisfied,
the assurance path should require a new hypothesis or a different diagnostic
layer. In this case, escalation meant examining the served Preview response and
effective browser policy rather than continuing to rotate image URLs.

### Challenge Executor assumptions independently

The Executor's explanation should remain a claim until independently supported.
Guardian should be able to challenge assumptions such as “the host rejects the
image,” “the page allowlist is effective,” or “the candidate is ready” by asking
for evidence from the actual delivery and browser boundary.

### Gate broken outcomes

A candidate whose required photographs do not render must not reach the Human as
if it were acceptable merely because production activity completed. Guardian
should preserve the finding, identify missing or contradictory evidence, and keep
the result from receiving an assurance judgement it has not earned.

These duties describe assurance direction. They do not make Guardian the owner of
page implementation, Preview Runtime repair, or Human authorization.

## 7. Watt / SPG implications

Future Watt and SPG evolution should account for four system properties exposed by
this case.

**Continuous-failure awareness.** The system should carry an unsatisfied visible
obligation across attempts and relate new evidence to prior failures. A new attempt
number must not erase the fact that the Human is still seeing the same defect.

**Separate production from success.** “Code changed,” “artifact generated,”
“Attempt completed,” and “Human-visible outcome verified” are distinct facts. The
system should represent them separately so that activity or completion cannot be
mistaken for a usable result.

**Validate at the owning boundary.** Front-end outcomes affected by browser and
environment policy require evidence from the served response and a real browser.
Static artifact inspection cannot establish the effective CSP, redirected resource
behavior, or successful image decoding in Chrome.

**Escalate unproductive routes.** Once evidence shows that an execution route is
not changing the failed outcome, Watt needs a governed path from local repair to
system-level diagnosis. That path should retain prior attempts and findings,
identify the layer that owns the remaining condition, and avoid asking the Human
to repeatedly rediscover the same failure.

## 8. Regression / Golden Journey implications

This case belongs in the existing `GJ-01 Greenfield Production` journey because it
tests whether production reaches a usable Preview. It does not justify a separate
waterfall- or CSP-specific Golden Journey.

Future regression protection should preserve these lessons:

- A page that depends on external passive resources or browser policy needs
  user-visible verification in the actual Preview environment.
- “Artifact generated” is not sufficient evidence of success. The required
  browser-visible resources must load and render.
- Artifact policy and HTTP response policy must be assessed as an effective whole;
  checking only the HTML source can produce a false conclusion.
- Browser evidence should distinguish a platform policy failure from an individual
  unavailable asset instead of treating every blank image as the same cause.
- Repeated failure patterns should become reusable assurance signals. The signal is
  not “this URL failed”; it is “successive local repairs left the same required
  visible outcome unsatisfied.”

The canonical governance record already requires future `GJ-01` qualification to
open the exact Watt Preview in a real browser, prove that required passive external
HTTPS images render through a redirected CDN host, and simultaneously prove that
external active scripts remain blocked. This case explains why that browser-level
evidence is architecturally necessary.

## 9. Status

```text
CASE_RECORDED = YES
IMPLEMENTATION_CHANGE_AUTHORIZED = NO
GUARDIAN_SCENARIO_VALUE = HIGH
FUTURE_REGRESSION_VALUE = HIGH
FUTURE_ARCHITECTURE_SIGNAL = PRESERVED
```
