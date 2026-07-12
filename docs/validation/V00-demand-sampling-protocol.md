# V00 Symmetric Demand-Sampling Protocol

**Status:** Draft evidence-acquisition protocol; pending decision-owner approval.
**Phase:** `V00 - Candidate Role Evidence`
**Decision effect:** None. This document does not supply demand evidence, rank candidates, select a Target, or unlock `V01`.

## Purpose and Boundary

The existing V00 dossier has directional, uneven, and partly mutable public signals. This protocol defines how a future public-demand collection must be performed symmetrically before it can inform a V00 rerun. It does not make practitioner availability, learner-channel reach, cost acceptance, role baseline, assessment validity, or simulation realism automatable.

| ID | Collection label | Included title and stack rule | Exclusions from counted sample |
| --- | --- | --- | --- |
| C1 | Junior Python Backend Engineer | Entry/junior backend developer or engineer responsibility with Python explicitly required or preferred; FastAPI is recorded when present, not required | Non-Python backend, full-stack without clear backend responsibility, senior/lead roles |
| C2 | Junior Data Analyst | Entry/junior data analyst responsibility | Data scientist, data engineer, BI developer without analyst responsibility, senior/lead roles |
| C3 | Junior Software Tester | Entry/junior software QA, tester, or test-engineer responsibility; manual and automation expectations are recorded separately | SDET lead, performance/security specialist, senior/lead roles |
| C4 | SOC Analyst L1 | Entry/junior SOC Analyst, L1, Tier 1, or equivalent monitoring-and-escalation responsibility | Penetration testing, governance, threat-hunting-only, Tier 2/3, senior/lead roles |

For every candidate, a posting must explicitly state entry/junior status, fresh-graduate eligibility, or no more than two years of required experience. A conflicting title and experience requirement is retained as an excluded row; it is not silently treated as junior.

## Fixed Symmetric Frame

Before the first source is inspected, the V00 decision owner records the values in the approval block. They apply identically to every candidate and cannot change mid-collection.

| Control | Required preregistered value | Rule |
| --- | --- | --- |
| Evidence cutoff | UTC date and time | End of the 28-calendar-day collection window |
| Search window | 28 days ending at cutoff | A row outside it is excluded from the counted sample but remains traceable |
| Markets | `EG_LOCAL`, `MENA_REMOTE`, `EN_REMOTE_EGYPT_ELIGIBLE` | Every candidate is sampled in every market; zero results are recorded, never skipped |
| Source channels | At least three named channels, ordered before collection | Each candidate-market cell receives the same channels, query rounds, and observation schedule |
| Query families | One title/alias query per candidate plus common seniority and market filters | Exact query, filter state, and locale are stored |
| Deduplication key | Employer, normalized title, market, and requisition or stable URL where available | Suspected duplicates keep their canonical row ID and reason |
| Demand sufficiency rule | Signed numerator, denominator, threshold, and failure disposition | No count, ratio, or search-result total establishes sufficient demand until approved |

`EG_LOCAL` is Egypt-located on-site, hybrid, or locally employed work. `MENA_REMOTE` is remote work explicitly open to Egypt or MENA residents. `EN_REMOTE_EGYPT_ELIGIBLE` is English-speaking remote work explicitly open to an Egypt resident. These are research segments, not a broadening of a candidate Target; they must be reported separately and never pooled into one demand or baseline claim.

## Source and Freshness Rules

1. Prefer an employer career page or official public listing. A platform page without a stable employer record is a mutable sample only.
2. Record an absolute publication date only when shown. Relative age is an observation, not a date; missing or conflicting dates are `freshness_unverified`.
3. Do not use search-result counts, paid-placement rankings, repost counts, or aggregate occupation data as exact-role vacancy volume.
4. Preserve source URL, access timestamp, source type, displayed date, stability, and a short paraphrase. Do not copy access-controlled content or personal data into Git.
5. Where a capture or archival snapshot is legally and technically permitted, record its controlled reference and hash. Otherwise retain the URL and the correct freshness label; absence of a snapshot is not evidence of freshness.

## Required Ledgers

### Search-attempt ledger

Every candidate × market × source-channel × query-round combination has one row, including zero results and access failures.

| Fields |
| --- |
| `attempt_id`, `candidate_id`, `market_id`, `source_channel`, `query_text`, `filters`, `locale`, `scheduled_at`, `observed_at`, `result_state`, `collector_id`, `review_status`, `deviation_id` |

`result_state` is `completed`, `zero_results`, `access_failed`, or `source_unavailable`. Any visible result count is `not_counted` and is never a demand metric.

### Normalized posting ledger

Every individually inspected public listing, included or excluded, has one row.

| Fields |
| --- |
| `record_id`, `attempt_id`, `candidate_id`, `market_id`, `employer`, `normalized_title`, `source_url`, `role_seniority_evidence`, `stack`, `domain`, `location`, `remote_eligibility`, `displayed_date`, `accessed_at`, `source_stability`, `freshness_state`, `dedupe_state`, `canonical_record_id`, `include_in_counted_sample`, `exclusion_reason`, `reviewer_state` |

`dedupe_state` is `unique`, `duplicate`, or `uncertain`; `reviewer_state` is `unreviewed`, `confirmed`, or `disputed`. `freshness_state` is `verified_in_window`, `out_of_window`, `freshness_unverified`, or `unknown`.

**Count eligibility is strict.** A record may set `include_in_counted_sample` to `true` only when exact role, seniority, and market eligibility are supported; its dedupe state is `unique`; its reviewer state is `confirmed`; and its freshness state is `verified_in_window` from an absolute displayed date inside the preregistered window. `freshness_unverified`, `unknown`, `out_of_window`, duplicate, uncertain, unreviewed, disputed, or access-failed records must set it to `false` and cannot enter the demand-sufficiency numerator.

If the verified eligible records do not satisfy the approved numerator and denominator rule, or the rule has not been approved, the demand condition is `Not met` and V00 remains `Revise`.

### Source and deviation ledger

Record source ownership, stability, coverage limitation, access issue, and every deviation. A deviation invalidates a candidate comparison unless the same corrective method is applied to every candidate-market cell or the V00 outcome remains `Revise`.

## Completion and Interpretation

A public-demand collection is **comparison-complete** only when all attempt cells exist, inspected listings have normalized rows, duplicates are traceable, every candidate had the same search opportunity, and freshness/access defects are explicit. It still does not prove sufficient demand; only count-eligible records may be evaluated against an approved sufficiency rule.

The V00 rerun reports broad market evidence; current vacancy samples by candidate and market; exclusions and duplicates; freshness/stability; baseline signals; and the approved sufficiency rule separately. No candidate receives an overall ranking when the approved rule is missing, a candidate-market cell is absent without symmetric correction, or material duplicates, seniority, or freshness issues remain. The required disposition then is `Revise`.

## Approval Block

Blank fields mean the protocol is not approved for a V00 rerun.

| Required decision | Approved value | Owner | Date / controlled reference |
| --- | --- | --- | --- |
| Evidence cutoff and 28-day window | Pending | Pending | Pending |
| Named source channels and query rounds | Pending | Pending | Pending |
| Demand-sufficiency numerator, denominator, threshold, and `Revise`/`Narrow` outcome | Pending | Pending | Pending |
| Duplicate-resolution and independent-review owner | Pending | Pending | Pending |

## Validation Checklist

Before collection, verify four candidates, three markets, common source channels, and a completed approval block. After collection, verify the attempt matrix, source URLs, absolute dates or freshness labels, explicit exclusions, dedupe links, and no claim stronger than the evidence. Assert that `freshness_unverified`, `unknown`, `out_of_window`, duplicate, uncertain, unreviewed, disputed, and access-failed records have `include_in_counted_sample=false`. Any failure returns V00 to `Revise`; it never falls forward to V01.
