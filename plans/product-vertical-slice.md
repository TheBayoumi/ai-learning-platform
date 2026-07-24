# First Deployed Product Vertical Slice

## Goal

Replace the technical status page with one complete learner journey for the
provisional Junior Python Backend Engineer track:

1. load a versioned role and competency profile;
2. collect bounded learner context and self-ratings;
3. diagnose weighted competency gaps;
4. generate a learner-unique sequence of practical missions;
5. show readiness, priority gaps, current work, and acceptance criteria;
6. accept completed work and update mastery; and
7. resume the signed learning state from the same browser.

## Runtime topology

- `apps/api`: FastAPI deployed as a separate Vercel Python project;
- `apps/web`: Next.js deployed on the existing Vercel project;
- browser requests use same-origin `/api/platform/*` routes;
- the Next.js server validates and proxies allowlisted requests to FastAPI;
- the API base URL remains server-only;
- learner state is canonical JSON protected by HMAC-SHA256 and stored in browser
  local storage as an opaque signed token.

## Implemented product behavior

- provisional versioned role profile with ten competencies;
- 0–4 self-rating diagnosis and weighted readiness projection;
- deterministic learner-unique activity selection and identifiers;
- bounded weekly-capacity plan length;
- explicit deliverables and acceptance criteria;
- progress completion, mastery increments, plan sequencing, and resume;
- tamper rejection and stable safe error envelopes;
- responsive, accessible onboarding and dashboard UI.

## Explicitly not complete

- user accounts, OIDC, authorization, tenancy, or deletion lifecycle;
- database-backed cross-device persistence and event history;
- LLM tutoring, Socratic dialogue, misconception inference, or generated feedback;
- artifact uploads, automated evidence inspection, assessments, simulations, or
  employer-facing portfolio verification;
- payment, subscription, notifications, analytics backend, or administrator tools;
- additional roles or evidence that the provisional role profile is market-validated.

This slice is a real deployed product workflow, not the full long-term platform.
It must not be presented as complete career readiness or as a replacement for the
remaining strategy and validation work.
