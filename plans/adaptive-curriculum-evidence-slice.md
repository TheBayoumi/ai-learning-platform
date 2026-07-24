# Adaptive Curriculum and Evidence Slice

## Goal

Extend the first learner journey from a fixed generated activity list into a bounded
adaptive curriculum that reacts to learner-attested evidence, review timing, weekly
capacity, and explicit competency focus.

## Implemented behavior

1. Each activity now exposes its generation, type, rationale, and availability date.
2. Completion captures:
   - acceptance criteria the learner states were met;
   - a bounded evidence reference;
   - confidence reproducing the work independently; and
   - a reflective account of the result and remaining gaps.
3. The API records a bounded evidence history inside the signed learner state.
4. Mastery changes are explicitly labelled provisional because the evidence is
   learner-attested rather than independently assessed.
5. Every evidence cycle schedules a spaced retrieval review using a deterministic
   confidence-dependent interval.
6. Due review activities take priority over ordinary build activities.
7. The learner can rebuild the active curriculum around:
   - updated weekly learning capacity; and
   - up to four explicit competency focus areas.
8. Replanning preserves evidence history and pending reviews while generating a new,
   learner-unique build cycle with a new plan revision and activity identities.
9. Version-1 signed states remain structurally readable through defaults for all new
   version-2 fields; any subsequent mutation emits schema version 2.
10. Evidence history, completed identifiers, request sizes, and signed state size remain
    bounded.

## Runtime and deployment policy

This slice is stacked on `automation/product-vertical-slice` while PR #6 awaits its
Vercel deployment gate.

Both Vercel project configurations set:

```json
{
  "git": {
    "deploymentEnabled": false
  }
}
```

Automatic Git deployments are disabled to prevent development commits from consuming
the Hobby-plan quota. Deployment remains an explicit exact-head workflow action after
PR #6 is accepted and the quota is available.

## Explicit claim boundary

This slice does not independently inspect repositories, documents, uploaded artifacts,
or runtime behavior. Criterion completion, evidence references, confidence, and
reflections are learner attestations. The resulting mastery and readiness values are
provisional planning signals, not external assessment, employment certification, or
proof of career readiness.

The slice still does not implement:

- authenticated user accounts or authorization;
- database-backed, cross-device persistence;
- artifact ingestion or automated evidence validation;
- AI tutoring, generated feedback, misconception diagnosis, or dynamic role research;
- market validation of the provisional role profile; or
- payment, notification, administrator, or employer-facing workflows.
