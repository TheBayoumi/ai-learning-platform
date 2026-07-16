# Autonomous Loop Checkpoint

## Current phase and gate

Foundation phases F00-F02 are `PASSED / Continue`. F02's controller revision
`8963101805d6f29f4701c91764b5563f07ff07c8` passed exact GitHub Actions run
`29511515229`. F03 is now defined but `NOT_STARTED`; its first eligible slice is
`F03-01 - FastAPI portable OCI artifact` on a later invocation.

The validation lane remains `V00 - Candidate Role Evidence`,
`WAITING_EXTERNAL / Revise`; V01 remains locked. No human review is pending.

## Lane recomputation

The controlled V00 inbox still contains only its README and retains the empty
evidence fingerprint. V00 still lacks qualifying symmetric demand evidence, two
qualified practitioner confirmations, a confirmed channel owner able to reach
20-50 eligible adults, and acceptable measured expected-cost evidence. Those
inputs cannot be self-certified, so no V00 rerun or later validation phase is
eligible.

The foundation lane had no approved phase after F02. Parallel architecture and
roadmap reviews therefore selected a narrow, reversible roadmap amendment:
`F03 - Portable Container Runtime and Non-Production Preview Baseline`.

## F03 amendment

F03 preserves the approved containers-on-managed-PaaS boundary and separates
three independently gated slices:

1. F03-01 builds and smokes only a locked, non-root FastAPI OCI artifact.
2. F03-02 adds the web artifact and a private server-only API binding while
   preserving the existing loopback parser unchanged.
3. F03-03 verifies one exact-revision ephemeral Vercel preview.

Official Vercel documentation inspected on 2026-07-16 describes OCI container
services, private bindings, and multi-service previews, but those surfaces are
Beta. They are a replaceable preview candidate, not a production selection. The
API must remain private, and F03 adds no public API, CORS, persistence,
credentials, product state, role state, or V00 evidence.

## Runtime and data boundary

This invocation changes only roadmap, plan, and controller records. It adds no
Dockerfile, deployment manifest, Vercel configuration, source code, dependency,
lockfile, workflow, migration, persistent data, or secret; it does not
intentionally invoke a deployment. The reported pre-existing Vercel Git
integration may still auto-create an unverified preview on push. That provider
side effect is not F03 evidence and cannot advance F03-03.
The accepted F00-F02 runtime remains unchanged.

## Risks

Vercel Services/container support is Beta, the reported repository connection
has no verified local `.vercel` link or CLI, and a Docker-compatible local daemon
has not been established. The tracked 66.3 MB archive remains an unrelated
checkout-cost risk. F02's prior Ubuntu-only raw-marker source remains unknown,
although the safe classifier and subsequent exact runs passed.

## Exact next action

Publish this definition-only amendment and require the exact pushed API, web,
and runtime-smoke GitHub Actions jobs to pass. Then stop. On a later invocation,
revalidate F03 entry conditions and implement only F03-01; do not add the web or
Vercel topology or intentionally invoke deployment. Any integration-triggered
preview remains unverified and is not F03 evidence.
