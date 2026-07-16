# ExecPlan: F03 Portable Container Runtime and Non-Production Preview Baseline

**Phase:** `F03 - Portable Container Runtime and Non-Production Preview Baseline`
**Class:** Technical foundation
**Status:** Not started
**Decision owner:** Primary agent
**Validation lane:** `V00` remains `WAITING_EXTERNAL` / `Revise`; `V01` is locked.

## Objective

Prove that the existing role-neutral FastAPI and Next.js health runtime can be
packaged as portable OCI services and exercised in one ephemeral preview without
claiming staging, production, product, or role maturity. The public boundary is
the web service; the API remains a private server-to-server dependency. F03
preserves the approved container-on-managed-PaaS boundary while treating the
provider, region, exact Next.js mode, and production topology as provisional.

## Verified Entry Conditions

| Condition | Evidence | Result |
| --- | --- | --- |
| F00-F02 pass | Accepted plans, controller state, inventory, and exact GitHub Actions runs through controller revision `8963101805d6f29f4701c91764b5563f07ff07c8` / run `29511515229` | Met |
| Containers on a managed PaaS remain approved while provider and exact Next.js mode remain provisional | `specs/tech-stack.md` | Met |
| Scope is limited to the existing role-neutral health transaction | Current runtime inventory and architecture review | Met |
| A replaceable container preview is technically plausible | Vercel Services, container, binding, and pricing documentation inspected on 2026-07-16 | Met |
| No V00 evidence is required or inferred | Parallel-lane rules and roadmap review | Met |

The phase definition is accepted separately from implementation. This ExecPlan,
the roadmap entry, and controller records do not start F03, create a container,
select a production provider, or satisfy an F03 exit condition. A later
invocation must recheck these entry conditions before F03-01.

## Why This Phase Is Next

V00 has no new controlled-inbox evidence and remains externally blocked. V01
and every role-specific phase remain locked. F02 passed, and no later foundation
phase was defined. The governing completion loop therefore requires a narrow
roadmap amendment before further technical work.

The smallest reusable gap is portable runtime packaging. The repository has no
Dockerfile, container smoke, deployment manifest, Vercel configuration, or
verified local Vercel link. Direct deployment would also fail the current web
contract: `AI_PLATFORM_API_BASE_URL` intentionally accepts only explicit
loopback origins. Packaging the API first proves the approved container boundary
without prematurely choosing web routing or weakening that guard.

PostgreSQL, authentication, jobs, product state, and public API routing were
considered and rejected for this phase. They are gated later or would enlarge
the role-neutral health-only boundary.

## Current Provider Evidence and Decision

The user reports that the repository is connected to Vercel. Current official
documentation now says that:

- [Vercel Services](https://vercel.com/docs/services) can build a polyglot
  Next.js/FastAPI monorepo as independently built services, but Services remains
  Beta;
- [container deployment](https://vercel.com/kb/guide/docker) supports
  `Dockerfile.vercel`, OCI container-image Functions, multi-service container
  entrypoints, `$PORT`, scale-to-zero, and bounded `SIGTERM` handling;
- [service bindings](https://vercel.com/docs/services/bindings) provide a
  deployment-aware private server-to-server URL, but reachability is not
  application authentication; and
- [Fluid compute pricing](https://vercel.com/docs/functions/usage-and-pricing)
  measures active CPU, provisioned memory, invocations, and regional usage.

These capabilities can reconcile Vercel with the approved portable-container
boundary for a preview experiment; they do not approve Vercel for production.
The provider adapter must remain replaceable. Automatic non-container FastAPI
detection is not F03 evidence because it would not prove the approved container
contract. The repository currently has no Vercel CLI, `.vercel` link, or
`vercel.json`, so remote preview access remains unverified until F03-03.

## Scope and Slices

Only one slice may be implemented and gate-reviewed per invocation.

1. `F03-01 - FastAPI portable OCI artifact`: add a locked, digest-pinned,
   non-root image for the existing health-only API; use a bounded service-root
   build context; honor `$PORT`; exercise live, ready, and OpenAPI responses;
   prove startup, graceful termination, cleanup, and confidential diagnostics;
   add one provider-neutral container smoke command that runs identically on
   every host with an available Docker-compatible daemon and in Ubuntu CI; and
   record build time, image bytes, startup, shutdown, memory, package inventory,
   and vulnerability evidence. Do not add Vercel configuration or intentionally
   invoke deployment. A pre-existing Git integration may auto-create an
   unverified preview when the required commit is pushed; that side effect is
   not F03 evidence and cannot advance F03-03.
2. `F03-02 - Web container and private binding topology`: add a portable,
   non-root production web image and a distinct server-only deployment-binding
   configuration path while leaving the local loopback parser unchanged; fail
   closed on missing, malformed, or ambiguous configuration; run the two images
   on an isolated container network; expose only web; and prove available,
   unavailable, invalid-response, routing, correlation, confidentiality,
   termination, and browser-output behavior. Add the reviewed Services topology
   only after these local contracts pass.
3. `F03-03 - Exact-revision preview gate`: verify the connected project and
   Services availability; create an ephemeral preview from the exact pushed
   revision; prove public web-to-private-API health behavior, absence of public
   API ingress, confidential diagnostics, fixed failure behavior, cleanup, and
   rollback; record region, image/build bytes, cold and warm timings, resource
   and request observations, estimated provider cost, Beta limitations, and the
   replacement path; then execute the complete F03 exit gate.

## Design Boundaries

- Both runtime artifacts are OCI-portable. Provider-specific configuration may
  adapt deployment, but application images and health contracts cannot depend
  on a Vercel-only domain, SDK, or runtime API.
- Base images and build tools are pinned deliberately. Runtime layers contain
  no development dependencies, tests, caches, VCS metadata, credentials, or the
  tracked repository archive.
- Runtime processes are non-root, bind only the injected port, handle termination
  within a measured bound, and do not rely on a writable or durable local
  filesystem.
- The API remains private. F03 adds no public API rewrite, browser-direct API
  call, CORS policy, custom domain, DNS change, or unauthenticated product route.
- F03-02 uses a separate server-only binding input. With no binding input, local
  development retains the exact loopback default. Binding and local override
  present together fail closed. A binding must be canonical, credential-free,
  and free of query, fragment, ambiguity, logging, or browser exposure.
- A private binding is a reachability grant, not authentication. F03 makes no
  authorization or isolation claim and exposes only the existing technical
  health transaction.
- Vercel Services and container support remain mutable Beta surfaces. Any drift,
  unavailable account capability, or non-container fallback returns to the F03
  gate; it does not weaken the constitution.
- Scale-to-zero, ephemeral filesystems, and Function limits cannot become
  assumptions for future persistence, jobs, or background work.
- F00-F02 contracts remain authoritative. Container and preview logs retain the
  fixed safe vocabulary and never emit raw URLs, headers, bodies, environment
  values, exceptions, trace context, or credentials.

## Dependency and Supply-Chain Decision Rule

Before F03-01 adds an image or scanner, record the base-image, builder, package
installation, vulnerability-check, and signal-handling options. The decision
must include exact ownership, pinning, transitive contents, build/runtime size,
known-vulnerability disposition, update path, and portability. A third-party
CI action or provider SDK is not approved merely for convenience.

Application dependencies and lockfiles remain unchanged unless the slice proves
that a runtime package is necessary. A container build must consume the existing
locked dependency graph and fail on drift. No registry credentials or provider
tokens enter Git, build arguments, layers, or logs.

## Failure Handling

- Lock drift, unpinned runtime inputs, root execution, excess build context,
  failed health validation, leaked configuration, or unclean termination fails
  the relevant slice.
- Missing, malformed, conflicting, or browser-exposed binding configuration
  fails closed with fixed non-secret output.
- A public API route, unexpected CORS requirement, non-container fallback, or
  provider-only application coupling returns `Revise` or `Narrow`.
- Preview build, routing, binding, region, quota, or account-capability failures
  remain F03 evidence. They do not alter V00, unlock V01, or justify production.
- Cancellation and timeout paths must remove owned containers/processes and
  leave tested ports available.

## Test Strategy

F03-01 requires static policy tests plus one repository-owned container harness
that builds, launches, probes live/ready/OpenAPI, exercises invalid configuration,
captures bounded resources, sends graceful termination, verifies exit and port
closure, and removes owned artifacts. The same command must work on supported
hosts with an available Docker-compatible daemon and on the Ubuntu CI runner. If
the local host has no daemon, report that limitation and rely on exact CI plus
independent reproduction; never claim an unrun local image build.

F03-02 adds web-image, isolated-network, server-binding, ambiguity, failure-state,
browser confidentiality, cross-process correlation, resource, and cleanup tests.
F03-03 adds exact-preview checks without storing credentials or raw provider
logs in Git. Every affected locked sync, contract, format, lint, strict type,
coverage, unit, build, line-ending, F02 confidentiality, and runtime-smoke gate
remains mandatory. Exact pushed GitHub Actions and independent verification are
required before accepting each slice.

## Performance and Resource Observations

Record API and web image bytes, compressed transfer if available, build time,
container startup and shutdown, resident memory, process count, preview cold and
warm health/page latency, service requests, active CPU, provisioned memory,
invocations, region, and estimated preview cost. These are observations, not
V17A budgets, SLOs, capacity claims, or production acceptance thresholds.

## Data, Privacy, and Compatibility

F03 uses only configuration-only health data and synthetic canaries. It adds no
database, migration, learner record, role record, durable file, credential,
production secret, retained provider log, or external telemetry backend. Public
health schemas and the browser confidentiality boundary remain compatible.

## Non-Goals

- Staging or production promotion, custom domains, DNS, traffic migration,
  uptime, availability, SLO, incident-response, or production-readiness claims.
- Public API ingress, CORS, browser-direct API calls, or general service discovery.
- Authentication, authorization, identity, tenancy, database, ORM, migrations,
  persistence, object storage, events, outbox, replay, jobs, queues, or LLM access.
- Product analytics, persistent telemetry, exporter/backend selection,
  monitoring, alerting, sampling, retention, or V17A operational budgets.
- Learner, role, competency, curriculum, assessment, mastery, evidence,
  simulation, readiness, or any V00/V01 behavior or claim.
- Real learner data, production credentials, permanent vendor selection,
  production cost ceilings, beta-capacity claims, or V16A/V16B evidence.

## Acceptance Criteria

F03 passes only after all three slices pass their exact pushed CI and independent
reviews; both images are locked, non-root, portable, bounded, and confidential;
the two-service container smoke passes; web alone is public and reaches API only
through its private server binding; malformed or ambiguous configuration fails
closed; the exact revision has a successful preview with recorded region,
resource, timing, cost, Beta, and rollback evidence; no persistent or sensitive
data is introduced; and no validation or production-hardening gate is bypassed.

Passing F03 does not pass V00, unlock V01, authorize V02, satisfy V16A/V16B or
V17A, approve Vercel for production, or establish product readiness.

## Rollback Strategy

Each slice remains independently revertible. Container images are immutable
build outputs, not committed binaries. Preview rollback selects the previous
immutable deployment or reverts the configuration commit; it never requires a
data migration. Removing F03 restores the accepted F02 development runtime.

## Gate Decision Rules

- `Continue`: every applicable slice or complete phase condition passes on the
  exact pushed revision.
- `Revise`: a reproducibility, container, binding, routing, confidentiality,
  cleanup, resource, preview, or documentation condition fails but is repairable.
- `Narrow`: only the portable API artifact can be proved without selecting or
  coupling a production topology.
- `Stop`: useful preview deployment requires public unauthenticated API access,
  secrets in Git, non-container runtime, persistent state, role-specific work,
  or a validation-gate bypass.

## Exact Next Action

On a later invocation, revalidate F03 entry conditions and implement only
`F03-01 - FastAPI portable OCI artifact`. Do not add web/Vercel topology,
publish an image, or intentionally invoke deployment in that invocation. Any
preview automatically created by a pre-existing Git integration remains
unverified, is not F03 evidence, and cannot advance F03-03.
