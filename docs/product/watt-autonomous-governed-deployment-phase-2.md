# Watt Autonomous Governed Deployment — Phase 2 Product Direction

Status: **Phase 2 product direction / architecture capture**

```text
FEATURE_PHASE
    PHASE_2

PRODUCT_DIRECTION
    APPROVED

DETAILED_ARCHITECTURE
    NOT_FROZEN

IMPLEMENTATION
    NOT_AUTHORIZED

CURRENT_RELEASE_DEPENDENCY
    NONE
```

This document records an approved future product direction. It does not
authorize a Deployment Plane, Deployment Adapter, schema, runtime, Executor,
credential, cloud-account, or UX implementation.

## 1. Product intent

Watt should eventually take a governed software Delivery into a
Human-authorized external runtime, observe the resulting Runtime Reality,
diagnose deployment problems, repair recoverable problems, recover safely from
interruption, and verify the result. Human participation should be required
when authority, intent, credentials, external dependencies, meaningful
trade-offs, or high-risk decisions genuinely require it—not merely because a
technical error occurred.

The intended experience is approximately:

```text
Delivery Ready
    -> Deploy
    -> Connect Cloud
    -> Select Target Server
    -> Provide domain / required application configuration
    -> Watt explains the material deployment plan
    -> Human authorizes
    -> Watt deploys
    -> Watt observes
    -> Watt diagnoses or remediates recoverable problems
    -> Watt verifies Runtime Reality
    -> Deployment Complete
```

For a Human who knows little about server administration, Watt should hide
unnecessary SSH, systemd, Nginx, Docker, security-group, TLS, package-manager,
instance-ID, and low-level network mechanics. The Human should provide what
only the Human can provide—such as account authorization, target choice,
domain choice, external API keys, or a meaningful business decision—while
Watt handles technical complexity inside the admitted boundary.

The product goal is not to automate a fixed list of deployment commands. It is
to let the Human delegate the outcome: **make this Delivery safely run there**.

Two principles are central:

> AI handles technical complexity. Human handles authority and meaningful
> trade-offs.

> A deployment error is new Reality for diagnosis and recovery, not
> automatically the end of the deployment task.

## 2. Phase 2 timing and release boundary

Autonomous Governed Deployment is intentionally Phase 2. The current first
release remains focused on software production, governed Delivery, the current
Human Journey, WIC/SDD reconstruction, formal UX/UI implementation, real
production Reality integration, and Human Journey dogfood.

```text
FIRST RELEASE
    software production and governed Delivery / current Human Journey

PHASE 2
    extend governed production through external deployment and Runtime Reality
```

This direction is not a dependency for the current first release, does not
reorder the current roadmap, and must not be used to reopen closed Work,
Executor, WIC, SPG, or Runtime foundations.

## 3. Human authority boundary

Human intervention is normally required only when at least one of these is
true:

- new Human Authority is required;
- Human Intent is ambiguous;
- a meaningful trade-off must be decided;
- a required credential or capability is unavailable;
- an external dependency is controlled outside Watt;
- remediation would affect resources outside the admitted deployment boundary;
- a destructive or high-risk action requires explicit governance.

Technical difficulty alone is not sufficient reason to make the Human become
the technical fallback. The Human is the Authority Governor, not the shell
operator.

Watt must never treat possession of a credential as equivalent to authority.
`Capability != Authority`: a credential may technically permit deletion,
network changes, service stops, or database changes while the Deployment
Contract authorizes only updating one application, restarting its runtime, and
verifying health. The narrower admitted authority wins.

The preferred future access posture is temporary credentials, scoped roles,
least privilege, just-in-time privilege, target-specific permission,
auditable use, and automatic expiry or revocation. Persistent customer root
credentials are not the normal product model.

## 4. Conceptual Deployment Plane

Deployment is a distinct governed capability after software production:

```text
Governed Delivery
      -> Deployment Planning
      -> Deployment Authorization
      -> Deployment Contract
      -> Deployment Plane
      -> Deployment Adapter
      -> External Runtime
      -> Runtime Observation
      -> Deployment Verification
      -> Deployment Reality
```

The software-production Executor owns **how to produce an admitted software
production result**. The future Deployment Plane owns **how an authorized
Delivery becomes Runtime Reality in an external target environment**.

These must not collapse into an Executor that writes code, logs into a
production server, and deploys whatever it wants. Production Authority and
Deployment Authority are distinct.

The upper Watt architecture should reason in terms of Deployment Target,
Delivery identity, Deployment Contract, required capability, authority,
execution, observation, verification, recovery, and rollback. `ssh`,
`kubectl`, `systemctl`, `docker compose`, and vendor-specific command APIs
belong below an Adapter boundary rather than becoming Watt deployment
semantics.

## 5. Provider-neutral adapters and capabilities

The future Deployment Plane should expose stable deployment semantics across
infrastructure. The current first-wave provider direction is:

- Alibaba Cloud;
- Tencent Cloud;
- Huawei Cloud;
- Baidu AI Cloud;
- Volcengine;
- JD Cloud.

This is an early Watt target-user and ecosystem relevance selection, not an
exhaustive cloud-support roadmap and not a claim about market share.

The candidate implementation sequence is:

1. define the provider-neutral Deployment Contract and capability boundary;
2. build Alibaba Cloud as the first Reference Implementation;
3. build Tencent Cloud as an independent second implementation;
4. use the second provider to test that the abstraction is genuinely
   provider-neutral rather than Alibaba-specific;
5. add further providers incrementally.

Adapters should expose capabilities rather than being forced into one giant
universal method set. Candidate capabilities include:

```text
TARGET_DISCOVERY          TARGET_INSPECTION
ENVIRONMENT_BOOTSTRAP     DEPLOY
HEALTH_OBSERVE            RUNTIME_INSPECT
SECRET_BINDING            NETWORK_CONFIGURATION
DOMAIN_CONFIGURATION      ROLLBACK
ZERO_DOWNTIME             CANARY
TRAFFIC_SHIFT             DIAGNOSTIC_EXECUTION
CONTROLLED_REMEDIATION
```

Different targets may support different sets. Steering and Deployment
Planning should eventually determine whether a target can satisfy the
Deployment Contract before execution begins. No final interface or domain
enum is frozen here.

For supported clouds, Watt should generally prefer the provider control plane
and its official remote-management or agent capability over a SaaS process
using public SSH and a root account. SSH may remain a bounded compatibility
fallback for generic or unsupported infrastructure. This document makes no
vendor-specific service claim without source evidence.

## 6. Deployment authority and privilege levels

The following is an illustrative future layered model, not a frozen
authorization schema:

```text
L0 — Observation
    logs, process/container status, ports, resource state,
    reachability, health, and cloud resource facts

L1 — Routine Remediation
    restart or replace Watt-managed application state,
    update admitted application configuration, fetch Delivery,
    clean Watt-managed temporary data

L2 — Elevated Environment Repair
    install an approved package, repair runtime, change admitted proxy
    configuration, change admitted firewall/security-group configuration,
    perform bounded environment bootstrap

L3 — High-risk / Cross-boundary
    touch unrelated applications, perform destructive database operations,
    change unrelated enterprise DNS or security posture, delete non-Watt
    resources
```

If a permission failure prevents diagnosis, Watt should not immediately
project `DEPLOYMENT_FAILED` or tell the Human to log in over SSH. A candidate
state such as `DIAGNOSIS_BLOCKED_BY_AUTHORITY` should distinguish:

```text
AUTHORITY_AVAILABLE_BUT_NOT_GRANTED
    versus
CAPABILITY_UNAVAILABLE
```

The future flow is to use already-authorized evidence, identify the minimum
additional capability, distinguish availability from authorization, request
the smallest scoped Human grant when required, and resume from the blocked
diagnostic point after authorization.

For example, instead of unrestricted root access, Watt may eventually request
temporary permission for one ECS target to read admitted Nginx configuration,
validate it, and read the relevant service journal for one deployment, with a
short expiry.

`BREAK_GLASS` is a future exceptional mechanism, not normal behavior. It
would require explicit Human approval, a short TTL, restricted target and
reason, detailed audit/evidence, side-effect capture, post-event evidence, and
automatic revocation. “AI is stuck, therefore gain root” is not a valid
architecture.

## 7. Deployment diagnosis, recovery, and verification

The intended autonomous loop is:

```text
Deployment Goal
    -> Prepare
    -> Deploy
    -> Observe
    -> Verify
    -> SUCCESS --------------------> COMPLETE
          |
          `-> anomaly
                -> Collect Evidence
                -> Diagnose
                -> Form hypothesis
                -> Collect missing evidence
                -> Confirm / reject hypothesis
                -> Find remediation
                -> Authority / safety check
                -> Remediate
                -> Observe again
                -> Verify again
                `--------------------> loop
```

The preferred diagnostic model is:

```text
Observed Evidence
    -> Diagnostic Hypothesis
    -> Required Additional Evidence
    -> Collect Evidence
    -> Hypothesis Supported / Rejected
    -> Remediation Candidate
    -> Authority + Safety Check
    -> Execution
    -> Post-condition Verification
```

AI owns diagnostic reasoning; deterministic systems and tools own observable
facts and bounded side effects. A command returning exit code zero is not
deployment success. Verified Deployment Reality should require, as applicable:

- expected Delivery identity active;
- runtime process or container healthy;
- backend health passing;
- frontend health passing where applicable;
- required frontend/backend integration passing;
- expected endpoint reachable;
- environment state matching the Deployment Contract.

Deployment must eventually use the same continuity discipline as the Native
Executor. If a restart or replacement is interrupted after a possible side
effect, the outcome is `UNKNOWN`; Watt must reconcile Runtime Reality before
continuing and must not blindly replay the action. Reconciliation should
determine which version, process/container, configuration, migration, and
network state actually exist, then derive the residual obligation.

This document records the deployment direction only; it does not claim that
the existing Executor recovery implementation already implements Deployment
Recovery.

Representative routine problems Watt should aspire to diagnose or repair
include unavailable runtime software, an old Watt-managed container occupying
a port, service-start failure, admissible configuration or proxy errors,
ordinary TLS problems, missing cloud security rules, health-check failure,
approved migrations not applied, network allow-list problems, interrupted
deployment, side effects before a process crash, and temporary provider
errors. Human Authority is more likely to be required for unrelated services,
unknown/non-Watt-owned runtimes, destructive database actions, paid-resource
purchase, unrelated corporate DNS, suspected compromise, invalid credentials,
conflicting workloads, or a remediation that changes Product Intent.

## 8. Relationship to Work, Delivery, and the Human Journey

Work remains Motive-bound and is not redefined as a server or deployment
object. Delivery identifies the software result to be deployed; Deployment
Reality records what the external target actually became. A later deployment
issue or modification may form a new Work under the existing Work identity
semantics.

Real deployment is expected to become one source of a future four-surface
Reality projection:

```text
Reality
    active Delivery, runtime health, endpoint and environment facts

Agenda
    remaining deployment obligations, pending verification, next recovery step

Production
    deploying, observing, diagnosing, remediating, verifying, rollback/recovery

Actions
    only decisions and authority requiring Human attention
```

This preserves the existing product principle that Current Work Reality is
the stage and conversation is the interaction channel. No four-surface UI
redesign is authorized by this memo.

Deployment should remain conversationally operable. Future answers to “why is
this slow?”, “why is the site unavailable?”, “which version is running?”, and
“can we roll back?” should use actual Deployment and Runtime Reality rather
than generic DevOps advice. This is a future information relationship, not a
UX implementation.

## 9. External constraints and secrets

Deployment adapters may eventually understand target constraints such as
public reachability, region rules, DNS and certificates, compliance
prerequisites, and cloud network configuration. Mainland-China public Web
deployment and ICP-related constraints are examples for future investigation,
not a compliance specification here. Watt should detect known blockers before
blindly attempting deployment and explain them in Human terms.

Secrets are not ordinary Conversation text or diagnostic-log content. This
document does not freeze a secret-management, vault, PAM product, IAM, or JIT
policy architecture. It only preserves the requirement for scoped,
time-bounded, auditable capability and authority.

## 10. Explicit non-goals and drift smells

This Phase 2 capture does not decide:

- persistence schema, lifecycle enums, APIs, adapter signatures, SDK choice,
  credential vault, PAM product, JIT policy engine, rollback protocol, secret
  storage, Kubernetes, multi-region architecture, quotas, enterprise network
  topology, or UI screens;
- whether any named provider or capability is part of the first release;
- exact relationships to ECF, Steering, Guided Design, or future Workspace
  surfaces beyond the boundaries stated above.

The following are architecture-drift smells to reject in later design:

```text
Deployment == SSH script
cloud credential == unlimited authority
command returned 0 == deployment success
deployment anomaly == ask Human to debug
permission denied == deployment failed
AI stuck == gain root
network interruption == blindly replay last action
Executor == Deployment Plane
provider-specific API == Watt deployment semantics
```

## 11. Relationship to current architecture and next decision

This direction builds on the existing Work, Delivery, Runtime, Trusted
Baseline, Native Executor, Capacity Scheduling, Human Authority, and governed
Reality boundaries. It does not reopen them, introduce a Project concept,
make a Delivery deployable by default, or imply external cloud access.

The next authorized design stage should define a provider-neutral Deployment
Contract and capability boundary, with Alibaba Cloud as a possible reference
implementation and Tencent Cloud as the independent abstraction test. That
stage must be separately admitted and must preserve the current first-release
sequence.

## 12. Status

```text
AUTONOMOUS_GOVERNED_DEPLOYMENT
    PHASE_2_PRODUCT_DIRECTION_APPROVED

DEPLOYMENT_PLANE
    CONCEPT_CAPTURED

DEPLOYMENT_ADAPTER_MODEL
    CONCEPT_CAPTURED

AUTONOMOUS_DIAGNOSIS_AND_RECOVERY
    REQUIRED_PRODUCT_DIRECTION

PAM_JIT_AUTHORITY
    REQUIRED_ARCHITECTURE_CONCERN

FIRST_WAVE_PROVIDERS
    ALIBABA
    TENCENT
    HUAWEI
    BAIDU
    VOLCENGINE
    JD_CLOUD

DETAILED_ARCHITECTURE
    DEFERRED

IMPLEMENTATION
    NOT_AUTHORIZED

CURRENT_FIRST_RELEASE
    UNCHANGED
```
