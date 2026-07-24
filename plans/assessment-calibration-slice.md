# Assessment Calibration Slice

## Goal

Add an objective but bounded knowledge-calibration signal to the adaptive curriculum
without treating a short question set as certification, replacing learner evidence, or
exposing answer keys to the browser.

## Implemented behavior

1. A versioned calibration bank contains one single-choice question for each competency
   in the provisional Junior Python Backend Engineer role profile.
2. The platform selects two to four questions from the learner's current ordered
   priority gaps rather than presenting a fixed generic quiz.
3. Attempts are signed with a domain-separated HMAC key and expire after 30 minutes.
4. Attempt tokens contain learner, role, state-sequence, expiry, and question identity,
   but never correct options or answer explanations.
5. Submission fails closed when:
   - the token is malformed or modified;
   - the attempt is expired;
   - the learner, role, or state sequence has changed;
   - questions are missing or duplicated; or
   - an unavailable option is submitted.
6. Correctness and explanations are returned only after submission.
7. Objective scores remain separate from learner-attested evidence mastery.
8. For assessed competencies, the planning signal uses a conservative blend:
   - 70% learner-attested evidence mastery; and
   - 30% objective calibration score.
9. Evidence readiness, assessment coverage, and blended planning readiness are exposed
   separately so the UI does not collapse unlike signals into one opaque number.
10. A scored attempt regenerates active build missions from the calibrated priority
    model while preserving pending spaced reviews and evidence history.
11. Assessment history is bounded and stored in the signed learner state.
12. The frontend provides a separate calibration workspace with:
    - explicit policy boundaries;
    - answer-hidden questions;
    - complete-answer enforcement;
    - post-submission feedback; and
    - synchronized plan updates without a page reload.

## Security and privacy boundary

- Correct options remain in the backend assessment catalog.
- Public questions and signed attempt tokens contain no correctness marker.
- The assessment secret is derived from the learner-state secret through a
  domain-separated HMAC operation.
- Request, response, token, history, and attempt sizes remain bounded.
- The browser communicates only through the same-origin Next.js proxy.

## Explicit claim boundary

This calibration is a small planning sample. It is not:

- a validated psychometric instrument;
- an independently proctored assessment;
- proof that a learner can produce working software;
- an employer credential;
- certification of job readiness; or
- a substitute for artifact inspection, project evidence, interviews, or workplace
  performance.

The current question bank is provisional and has not been validated for difficulty,
discrimination, reliability, fairness, or current hiring-market representativeness.

## Stack and deployment policy

This slice is stacked on `automation/adaptive-curriculum-evidence`, which is stacked on
PR #6. Automatic Vercel Git deployments remain disabled. The slice must not deploy or
merge until its base PRs have passed their own merge conditions.
