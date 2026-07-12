# V00 External Evidence Request Package

**Status:** Draft request templates; not sent and not evidence of access.
**Phase:** `V00 - Candidate Role Evidence`

This package prepares privacy-safe V00 requests without claiming practitioner, learner-channel, or cost evidence. Before sending, an authorized owner must choose the recipient and approval path. Do not commit names, contact details, raw correspondence, learner lists, or access-controlled artifacts.

## Practitioner Availability and Validation Request

### Draft message

> We are validating the specified V00 candidate Target: `[candidate ID and tuple version: role, seniority, market segment, learner baseline, and overlays]`. Would you provide a short, independent review of that exact role boundary and the realism of a future bounded proof slice? We will not ask you to assess learners or approve a curriculum at this stage. Please state your current role context, relevant experience, familiarity with the stated market segment, any conflict of interest, and whether you can review the V00 material by the requested date. Your information will be kept in controlled storage; the repository will retain only a pseudonymous record.

| Required controlled evidence field | Rule |
| --- | --- |
| `practitioner_evidence_id` | Pseudonymous stable ID |
| Current practice and market familiarity | Summary only; no personal or employer identifier in Git |
| Qualification-rule result | Pending until the V00 qualification rule is approved |
| Candidate Target binding | Candidate ID, tuple version, role, seniority, market segment, candidate-specific learner baseline, and overlays |
| Review scope and date | Exact candidate role boundary and market segment; proof-slice realism only |
| Conflict disclosure status | `none_declared`, `declared`, or `unknown` |
| Controlled reference | Original stored under approved access control |
| V00 use | `availability_only` or `validation_received`; availability never implies approval |

Two distinct records that pass the approved qualification rule are required. One person, or two unqualified responses, cannot satisfy the V00 gate.

### Practitioner Qualification Decision Template

| Required decision | Approved value |
| --- | --- |
| Candidate Target scope and tuple version | Pending |
| Minimum current or recent practice and exact-market familiarity | Pending |
| Minimum review experience and independence/conflict rule | Pending |
| Validity period for availability and validation | Pending |
| Approval owner, date, and controlled reference | Pending |


## Recruitment-Channel Confirmation Request

### Draft message

> We are validating an adult (18+) career-transition learning pilot for `[candidate ID and tuple version: role, seniority, market segment, and candidate-specific learner baseline]`. Can your channel reach 20-50 adults matching that exact baseline and market? Please describe the channel type, relevant eligibility filter, realistic reachable range and period, and participation constraints. Do not send subscriber or learner personal data. We will store the original confirmation in controlled storage and keep only a pseudonymous evidence record in the repository.

| Required controlled evidence field | Rule |
| --- | --- |
| `channel_evidence_id` | Pseudonymous stable ID |
| Owner authority | Summary of authority to represent the channel |
| Adult eligibility and learner-baseline filter | Explicit confirmation |
| Candidate Target binding | Candidate ID, tuple version, role, seniority, market segment, and candidate-specific learner baseline |
| Reachable range, period, and candidate market | Explicit numeric range and bounded period |
| Recruitment constraints | Cost, consent, timetable, or platform constraints |
| Controlled reference | Original stored under approved access control |
| V00 use | `reach_confirmed` only when the evidence supports 20-50 eligible adults |


### Candidate-Baseline Binding Matrix

| Candidate | Baseline that must appear in the request and evidence record |
| --- | --- |
| C1 | Basic Python syntax and Git; no production backend competence or defensible work evidence |
| C2 | Spreadsheet literacy, basic numeracy, and no professional analytics experience |
| C3 | Basic software and web literacy, structured written communication, and introductory scripting exposure |
| C4 | Networking, operating-system, and command-line fundamentals; no professional SOC experience |

Hypothetical audience size, social followers, or an unauthenticated referral is not a real recruitment channel.

## Expected-Cost Acceptance Boundary Request

Relative statements such as “low to moderate” cannot substitute for an approved boundary.

| Required stakeholder decision | Approved value |
| --- | --- |
| Target scope and time horizon | Pending |
| Maximum total V00 validation cost | Pending |
| Maximum pilot cost per active learner and calculation method | Pending |
| Included categories: practitioner review, model, compute, storage, tools, recruitment, support, contingency | Pending |
| Measurement method, cadence, and accountable owner | Pending |
| Overrun disposition: continue, revise, narrow, pause, or stop | Pending |
| Approval authority, date, and controlled reference | Pending |

Until every field is approved and representative estimates are measured against it, the V00 cost condition remains **Not met**.

## Intake and Review Rules

Place only privacy-safe metadata in `docs/validation/inbox/` according to its README. A later run checks the exact candidate Target binding, date, controlled reference, qualification or reach criteria, conflicts, and consistency with the approved V00 protocol. A response lacking the candidate binding, an approved qualification rule, or an approved controlled reference cannot satisfy a V00 gate. Invalid, incomplete, conflicting, or low-confidence submissions remain unverified and must not change the V00 decision automatically.
