# AI Career Learning Platform: Product Strategy & System Design
**A persistent one-to-one AI tutoring, mastery, and role-readiness engine. Not a chatbot, not a course library, not a quiz app, not a school, and not a job-placement guarantee.**

*Operating scope: 2–4 engineers + 1 learning designer, LLMs via API without model training, web-first, and adult career acceleration first. A valid target must resolve role, seniority, geography or labor market, timeline, and any known industry, company, or stack constraints; unresolved dimensions remain explicit rather than being silently guessed. The RoleProfile defines the destination, not a fixed syllabus. Each learner receives a continuously recomputed curriculum based on verified prior knowledge, misconceptions, forgetting, pace, constraints, evidence, interests, and active overlays. Shared blueprints provide quality control, but every served task, project, and work simulation is instantiated uniquely for that learner. The document separates long-term vision, the 12-month strategy (§P), the 90-day validation sprint (§Q), and later school/kid expansion (§N, §P). The school/kid shell remains architectural compatibility during year one unless a separate team is funded.*


---


## A. Executive summary

Online learning is split into two half-products. LLM Socratic tutors (Khanmigo, ChatGPT Study Mode, Claude Learning Mode) provide strong real-time dialogue and conversational understanding checks, but there is no public evidence that they maintain deep, persistent, per-skill mastery models — what you did three weeks ago, what you are about to forget, or which misconception you are still carrying. Classic intelligent tutoring systems (ALEKS, MATHia, Squirrel AI) are the mirror image: decades of engineering behind persistent mastery tracking and adaptive sequencing, but interaction runs through structured problems and pre-authored explanations — limited natural dialogue and limited explanation adaptation.

**The learning product is the union: an LLM Socratic front-end wired to a deterministic mastery, misconception, forgetting, and assessment back-end.**

**The commercial product is a career booster built on top of that union.** A learner selects a target role; the platform resolves it into a versioned role-readiness contract, diagnoses the learner's current state, compiles a learner-specific curriculum, and continuously replans it as evidence changes. It teaches and verifies each required competency, instantiates unique tasks, projects, and work simulations for that learner, and maintains an evidence portfolio until the published readiness threshold is met.

> **A chatbot answers. A tutor diagnoses. A mastery engine remembers. A career engine turns mastery into work readiness.**

The framing that governs everything: **replace passive instruction, not school.** Passive lectures, generic videos, dumb quizzes, repeated explanations, worksheet practice, and one-size-fits-all pacing are automated. Socialization, labs, sports, peer learning, mentorship, safeguarding, and human development remain explicitly human. Teachers are not eliminated; their low-leverage instructional tasks are automated so they can focus on mentor, coach, guide, and accountability work.

The same precision is required for career claims. No honest platform can teach literally *everything* relevant to every employer or guarantee employment. The defensible promise is narrower and stronger:

> **The platform makes the learner ready for a defined role profile, seniority level, market, and competency contract — then applies company-, industry-, or stack-specific overlays where needed.**

A target such as “backend engineer” is therefore not a course or a fixed module sequence. It is a **core role baseline** plus explicit overlays for geography, industry, company, tooling stack, interview style, and seniority. “Ready for any company” becomes “ready for the role's validated common core, with a visible employer-specific delta.”

The RoleProfile is shared; the curriculum is not. Two learners targeting the same role may receive different prerequisite routes, explanations, task sequences, review schedules, projects, simulations, and pacing because they start with different evidence and respond differently. Shared standards preserve comparability; learner-specific instances prevent copy-through learning and keep the path relevant.

Nine commitments define the build:

1. **The LLM is a sensor and actuator, not the learner model.** It evaluates, explains, converses, and proposes tutor moves; a deterministic, auditable layer owns mastery state, updated only from structured evidence.
2. **Scaffold, then withdraw.** If the learner cannot solve it without the AI later, the product did not teach. Every serious mastery claim requires no-hint performance, a reasoning check, delayed retention, and transfer where the domain allows.
3. **Role completion is not content completion.** Career readiness requires demonstrated competence, projects, work simulations, and evidence — not videos watched or modules finished.
4. **Content and role requirements earn trust.** Generated tasks and inferred market requirements pass through explicit trust levels before they may influence assessment or readiness decisions.
5. **Measure learning and readiness, not engagement.** Time-in-app is a diagnostic, never a goal. Job placement is a downstream outcome, not proof by itself that the learning system worked.
6. **The destination is stable; the curriculum is dynamic.** The RoleProfile defines required outcomes. A deterministic curriculum planner continuously recompiles each learner's route from current evidence; there is no fixed syllabus shared by all learners.
7. **Unique work, shared standards.** Tasks, projects, and simulations are unique learner instances generated from validated blueprints and equivalent rubrics. Personalization never bypasses verification.
8. **Core role baseline plus overlays.** Every role contract declares its scope and exclusions. Employer-specific requirements are modeled explicitly instead of hidden behind an impossible “any company” promise.
9. **Prove the engine on one role, then expand.** Wave 1 is one adult/16+ technical role with objective verification, realistic projects, and a clear employment outcome. A certification may support the role contract; it is not the product identity.

On evidence posture: this document does not promise Bloom's two-sigma, guaranteed employment, or universal job readiness. Modern tutoring effects are usually more modest, and hiring depends on market conditions, geography, communication, prior experience, and employer decisions. The product owns what it can verify: mastery, retention, transfer, project performance, simulation performance, and the completeness of the learner's evidence against the role contract.

And one orientation for the first year:

> **For the first 6–12 months, this is not mainly an AI company. It is a learning-and-career-systems company using AI as the interface.**

---


## B. Core thesis

The market gap is structural, not incidental. Dialogue tutors are a great mouth with no memory; adaptive platforms are a great memory with no mouth; career course platforms provide a destination but usually treat completion as evidence of readiness. Every capability the product needs exists somewhere; no shipped product has the full stack tied together as one auditable system.

**The union, stated precisely:** an LLM Socratic front-end — dialogue, explanation re-rendering, step evaluation, hint generation — wired to a deterministic back-end that owns four learning states: **mastery** (per-skill estimates), **misconceptions** (tracked, evidenced, resolved), **forgetting** (decay and spaced-retrieval scheduling), and **assessment** (validated items, no-hint checkpoints, delayed probes, transfer tasks).

A separate **career-readiness layer** maps those learning states to an outcome contract: target role, seniority, geography, required competencies, tools, work behaviors, portfolio evidence, and optional company/industry overlays. The RoleProfile is an outcome graph, not a curriculum. A deterministic CurriculumPlanner compiles a learner-specific route through that graph and recomputes it whenever mastery, misconceptions, forgetting, available time, project evidence, market requirements, or target overlays change. The platform does not infer “ready” from course completion; it computes readiness from verified evidence against the contract.

> **A chatbot answers. A tutor diagnoses. A mastery engine remembers. A career engine converts verified mastery into role readiness.**

The division of labor is a hard architectural rule, not a preference:

> **The LLM is a sensor and actuator, not the learner model — and not the sole judge of career readiness.**

The LLM may evaluate a learner's step, explain a concept five different ways, generate the next Socratic question, extract a candidate competency from market evidence, and *suggest* a tutor or career move. It must not directly own mastery or readiness state. Updates are deterministic, auditable, versioned, and computed from structured evidence: assessment mode, hint usage, project rubrics, simulation outcomes, artifact provenance, and reviewer decisions.

The career promise is bounded by an explicit contract:

> **“Complete for the target role” means every required competency in a published, versioned role-readiness contract — not every technology, employer preference, or future market change.**

Each contract has a common core and overlays. For example, a data analyst core may include SQL, data cleaning, statistics, visualization, requirements clarification, and stakeholder communication; a finance overlay may add domain-specific metrics; a target-company overlay may add a particular BI stack or interview format. Readiness can therefore be explained, challenged, and updated.

The curriculum is produced at runtime for one learner. It is not a static list attached to the role. Plan changes are triggered only by versioned evidence or declared constraint changes, recorded as a new LearnerPlanVersion, and shown as a readable delta: what moved, why it moved, and what evidence caused the change. The LLM may propose content or candidate activities, but it cannot mutate required competencies, readiness thresholds, or the learner's plan directly.

**Assumption-closure rules.** The platform does not fill material gaps with model intuition:

- An underspecified target does not produce a curriculum. Role, level, market, and timeline must be resolved or explicitly marked unknown.
- Unknown company, industry, or stack requirements remain unresolved overlays; they are not folded into the common core.
- Self-reported experience prioritizes diagnosis but never grants mastery or readiness.
- A low-confidence market signal cannot become a mandatory competency.
- A competency without valid assessment evidence remains unverified.
- A task, project, or simulation that cannot be validated or shown to be sufficiently distinct is not served.
- Changing the target role, level, market, constraints, or deadline creates a new RoleProfile selection or LearnerPlanVersion; prior evidence is preserved and remapped, not discarded.
- When evidence conflicts, the system records uncertainty and requests stronger evidence or human review instead of forcing a confident decision.

These rules are product invariants. Prompt wording, conversational history, or model replacement cannot override them.

Where the defensibility lives:

> **The moat is not the LLM. The moat is the validated learner model, versioned role and competency graphs, item bank, item statistics, misconception data, work-simulation rubrics, evidence portfolio, and tutor-move outcome data.**

Everyone rents similar foundation models. Competitors do not automatically have the longitudinal record of each learner, calibrated tasks, traceable role requirements, or millions of (learner state, tutor move, project/simulation outcome) triples that let pedagogy and career preparation improve empirically. Those assets compound; API access does not.

---


## C. What already exists

### Category 1 — LLM Socratic dialogue tutors
*Khanmigo, ChatGPT Study Mode, Claude Learning Mode, LearnLM-based tools, oral-assessment systems like Georgia Tech's Socratic Mind.*

What they demonstrably do well: **strong real-time Socratic scaffolding and conversational understanding checks.** Khanmigo is the reference pattern — refuse to hand over the answer, ask what the learner tried, guide with progressively targeted hints. Explanation adaptation (tone, analogy, reading level, on-demand re-rendering) is the best in the industry. Khan Academy has publicly described improving its tutor by A/B-testing against next-item correctness and response latency — the right instincts, worth copying.

What should not be claimed for them: deep long-term mastery models. Public evidence points to session-scoped context plus coarse course position, not per-skill mastery estimates with forgetting curves and misconception ledgers. Their understanding checks are conversational and unverified — a fluent learner can parrot through them. Two reported failure modes matter for this design: learners answering "IDK" until the Socratic method collapses (it requires effort it cannot compel), and teachers repurposing the tutor as a quiz generator (users route around pedagogy).

### Category 2 — Classic ITS and adaptive platforms
*MATHia (Bayesian knowledge tracing lineage), ALEKS (knowledge space theory), Squirrel AI (fine-grained knowledge mapping), CENTURY Tech, DreamBox, Knewton Alta; Cognii and Querium for step-level and open-response evaluation.*

These are **stronger at persistent mastery tracking** — that is their entire reason for existing: fine-grained knowledge components, prerequisite structures, mastery-gated progression, precise gap diagnosis, and in the best cases step-level feedback within multi-step problems.

Their limits are the mirror image: interaction is structured problem-solving, not conversation; explanations are pre-authored and cannot re-render for a confused learner; "understanding" is operationalized almost entirely as item performance, with little "explain why." Content authoring cost confines most of them to math and adjacent STEM. And the research literature on these systems documents *gaming the system* — learners clicking through hint sequences to extract answers — which is a preview of this product's own failure modes if hint budgets are not enforced.

### Category 3 — AI-first school and hybrid models
*Alpha School / 2 Hour Learning; assorted microschools and hybrid homeschool programs.*

Alpha compresses academics into roughly two hours of mastery-gated, app-based practice (reported thresholds around 90%+ accuracy before advancing), with afternoons for projects and life skills. Reporting indicates the "AI" is largely adaptive-app instruction rather than LLM tutoring, and — critically — **human guides remain part of the model**, handling motivation, supervision, and accountability.

**Treat Alpha as a directional signal, not proof. Its model validates demand for compressed AI-assisted academics plus human guidance, but its outcome claims should not be treated as causal evidence without independent auditing.** The reported growth numbers come from a selective, expensive private school with obvious selection effects; do not build a business case on unaudited outcomes. The transferable lesson is directional and still valuable: even the most AI-forward school in existence kept humans for the human parts — which validates this document's thesis from the most aggressive possible direction.

### Category 4 — Career-path platforms and bootcamps
*Course-pathway products, bootcamps, certification academies, and job-readiness programs.*

These products are strong at **destination framing**: choose a role, follow a syllabus, complete projects, receive a certificate, and sometimes obtain career coaching. They solve motivation better than generic course libraries because the learner can see a career outcome.

Their common weakness is that the path is usually static and completion is treated as a proxy for readiness. They rarely maintain a fine-grained, longitudinal mastery and forgetting model; project feedback may be shallow or mentor-dependent; employer requirements are not represented as versioned competency contracts; and the learner may finish with a certificate but still have unverified gaps in foundational knowledge, independent execution, debugging, communication, or workplace judgment.

The opportunity is not another bootcamp catalogue. It is to combine the bootcamp's destination, the ITS's mastery model, the Socratic tutor's interaction, and an auditable readiness/evidence layer.


---

## D. The market gap

| Capability | LLM Socratic tutors | Classic ITS / adaptive | Career programs / bootcamps | AI-first schools |
|---|---|---|---|---|
| Dialogic interactivity | **High** — real conversation | Low–medium — structured steps | Medium — mentor/chat dependent | Low — app UX |
| Persistent per-skill learner model | Weak / not publicly evidenced | **Strong** — mastery-gated | Usually weak | Strong at platform level |
| Depth of understanding check | Conversational, unverified | Item-verified, little “explain why” | Project/completion based, uneven | Mastery gates |
| Curriculum / pacing adaptation | Weak | **Strong** | Mostly fixed pathways | Strong |
| Explanation adaptation | **Strong** — re-renders on demand | Weak — canned | Medium | Weak |
| Misconception detection | Ad hoc, per-conversation | Rule-based where present | Rare / mentor dependent | Coarse |
| Forgetting model / spaced retrieval | Rare | Partial | Rare | Partial |
| Anti-dependency design | Poor | Moderate — hints gameable | Variable | Untested claim |
| Versioned role-competency contract | Rare | Out of scope | Usually coarse or implicit | Out of scope |
| Work simulations and portfolio evidence | Rare | Rare | **Present but weakly tied to mastery** | Projects outside academic block |
| Company/industry overlays | Rare | Out of scope | Sometimes informal | Out of scope |
| Auditable readiness decision | No | Academic mastery only | Usually completion/certificate proxy | Academic progression only |
| One-to-one self-learning | Good | Weak — motivation outsourced | Good when learner is motivated | N/A — humans supplied |
| Teacher / mentor / organization mode | Assist tools | **Native school dashboards** | Mentor/career-coach dependent | Whole-school |

Read the columns: **row-complete does not exist.** Dialogue tutors provide interaction; ITS provide mastery; career programs provide direction and projects; AI-first schools provide accountability. The missing product combines all four while keeping each decision auditable:

> **target role → versioned competency contract → baseline diagnosis → adaptive tutoring → verified mastery → realistic projects and work simulations → evidence portfolio → readiness decision → employer-specific overlay.**

That is wide enough to be a company rather than a feature. The product is not “AI explains courses better.” It is a closed-loop system that knows the destination, knows the learner, measures the gap, closes it, and proves what was closed.

---


## E. What AI should replace — and what it should not

**Replace or heavily automate (the instructional layer):** passive lectures; repetitive re-explanation; generic one-size-fits-all courses and videos; worksheet-style practice; basic tutoring and homework help; first-pass feedback; formative assessment and gap diagnosis; adaptive revision planning; and the teacher's low-leverage workload — grading simple practice, generating worksheets, diagnosing routine gaps, tracking routine progress, explaining basics one-to-many.

**Do not attempt to replace (the human layer):** socialization; physical activity; labs and hands-on work; peer learning; friendships and teamwork; emotional care; mentorship; child safeguarding; human accountability; real-world projects; school culture; and credentialing/institutional trust.

Two boundary clarifications that keep the claim honest. *Formative* assessment belongs to the platform; *high-stakes summative* assessment stays with institutions — proctoring, validity, and trust are not things a startup mints. And first-pass feedback belongs to the platform; consequential judgment on consequential work stays human.

**The thesis, in one sentence:**

> AI should not replace school as a human social environment. It should replace the passive, generic, low-feedback instructional layer — and turn online learning into a persistent one-to-one tutoring experience.

On teachers, precisely: the product automates repeated explanations, simple grading, worksheet generation, gap diagnosis, adaptive revision, and basic tutoring. Humans remain essential as **mentors, coaches, guides, supervisors, motivators, and accountability layers** — for values, intervention, emotional support, real-world discussion, and high-stakes judgment. "Teacher as mentor/coach/guide" is the job description that remains after the repetitive work is automated, and it is the only framing under which teachers, parents, and institutions will ever trust the product.

**Career preparation the platform can automate:** target-role normalization; baseline skill-gap diagnosis; dynamic curriculum compilation and replanning; technical practice; learner-specific task and project instantiation; work simulations; code, analysis, or artifact feedback; portfolio evidence mapping; interview rehearsal; and company/stack delta analysis.

**Career preparation it must not pretend to control:** employer hiring decisions; labor-market demand; visas and geography; compensation; workplace politics; culture fit; background checks; access to networks; or the exact internal stack and expectations of every company. The platform may improve readiness and expose gaps; it does not guarantee a job.

The career claim therefore uses a **readiness contract**, not marketing language. Every RoleProfile publishes its role, level, geography, competency coverage, exclusions, evidence requirements, uncertainty, and market review date. A learner can be “ready against RoleProfile v3.2” while still needing a named company overlay — a truthful, actionable conclusion instead of “you are ready for anything.”


---

## F. Product principles

Fourteen principles, each enforceable in design review — a principle that cannot veto a feature is a slogan.

1. **Replace passive instruction, not school.** Any feature that drifts toward replacing the human layer (§E) is out of scope by definition.
2. **The LLM is a sensor and actuator, not the learner model.** Mastery and readiness updates are deterministic, auditable, and evidence-based. No exceptions, including “temporary” ones.
3. **Scaffold, then withdraw.** If the learner cannot solve it without the AI later, the product did not teach. Scaffolding fades on schedule, not on request.
4. **Verified mastery or it did not happen.** A mastery claim requires no-hint performance, an explanation/reasoning check, delayed retention, and a transfer or near-transfer task where the domain allows.
5. **Content completion is not career readiness.** Readiness requires verified competencies, independent work, realistic simulations, and portfolio evidence mapped to a role contract.
6. **No static curriculum.** A role graph defines outcomes; a learner-specific plan defines the current route. The route is continuously recomputed from evidence and constraints.
7. **No shared learner work.** Every task, project, and simulation served to a learner is a unique instance. Shared blueprints and rubrics preserve validity; identical assignments are not the learning model.
8. **The goal is not engagement with the app. The goal is sustained attention on productive struggle and progress toward a declared role.** Engagement metrics are diagnostics, never objectives.
9. **Assessment validity is part of the product, not an optional research feature.** Mastery and readiness numbers nobody should trust are worse than no numbers.
10. **Content and role requirements earn trust.** No generated item touches assessment, and no inferred market requirement becomes mandatory, until it passes the appropriate validation pipeline (§L).
11. **Core role baseline plus explicit overlays.** Employer-, industry-, geography-, and stack-specific deltas are modeled separately. The product never hides company variation behind an “any company” promise.
12. **One engine, policy-configured shells and role graphs.** Shell differences live in policy; role differences live in versioned graphs; learner differences live in versioned plans and unique instances — never forked codebases.
13. **Latency is pedagogy.** Dead air is a phone-check invitation; p95 turn latency is a learning KPI with an owner.
14. **Humans stay in the loop.** Accountability, contested grading, soft-skill judgment, market validation, escalation, and high-stakes decisions route to people — a mentor, reviewer, parent, teacher, subject expert, or hiring-domain expert.

---


## G. Learning and motivation model

The engagement question, answered properly: do not optimize engagement.

> **The goal is not engagement with the app. The goal is sustained attention on productive struggle.**

**Explicitly rejected:** streak addiction, XP, loot mechanics, time-in-app targets, message-count targets. These maximize app-opens, and app-opens are not learning; worse, they teach learners that the reward is the token, not the competence.

**Replaced with:** productive struggle in a calibrated difficulty band; visible mastery progress; bounded sessions with clear finish lines; exam/project goal anchoring; spaced review; confidence calibration; end-on-a-win recovery; and human accountability when needed.

**0. Career anchoring — the learner sees a route to work, not a pile of lessons.** Onboarding starts with a target role, seniority, geography, constraints, prior experience, and timeline. The platform turns that into a visible role map: required competencies, current evidence, gaps, prerequisite structure, evidence requirements, and employer-specific deltas. Every learning session explains why today's node matters to the target role. The progress surface shows **readiness coverage and evidence quality**, not percentage of videos completed.

**1. Dynamic curriculum compilation — the route changes when the learner changes.** The role graph is a versioned destination, not a shared syllabus. The CurriculumPlanner builds an initial LearnerPlan from verified baseline evidence, prerequisites, available time, target date, learning velocity, accessibility constraints, preferred contexts, and active overlays. It recomputes the plan after meaningful events: mastery verification, misconception evidence, forgetting, failed or exceptional performance, project/simulation results, a changed target, or a new RoleProfile version. Every replan is deterministic for the same inputs, versioned, auditable, and presented as a delta. The learner may request a different pace or context, but cannot skip mandatory competencies without accepted evidence.

**2. Difficulty calibration — the primary anti-distraction mechanism.** Boredom and frustration are the two exits into the phone. Target a **roughly 80–90% success band** for practice — a product heuristic, not a universal law; the oft-cited "85% rule" derives from machine-learning and animal-learning models, not a proven human constant. Calibrate by activity type: new acquisition tolerates lower success (60–75%) *when scaffolding is strong*; spaced-retrieval reviews sit high (~90%) because their job is strengthening, not struggling; no-hint assessments are allowed to feel hard. The knowledge graph's operational job is serving the *next right problem* to keep each learner in-band.

**3. Bounded sessions with visible finish lines.** "Study for an hour" invites drift; "master these five nodes" doesn't. Sessions run 25–50 minutes (adult shell) or 15–20 (kid shell), opened with an explicit goal and a visible distance-to-done. Progress visualization is a **mastery map** — nodes lighting up, decayed nodes dimming — never arbitrary currency.

**4. Hand the pen back — no passivity beyond ~90 seconds.** Reading and watching are where minds wander. After any explanation fragment the tutor's default move is to make the learner generate: "you write the next step," "predict what happens if…," "explain that back in one sentence." Generation beats consumption, and it doubles as continuous assessment.

**5. Retrieval, spacing, interleaving.** The scheduler injects due reviews into every session (target ~30% of volume), interleaves once three or more skills are in play, and spaces by per-skill stability estimates. Expect learners to *dislike* this — desirable difficulties feel worse while working better — which is exactly why satisfaction ratings must never tune the difficulty policy.

**6. Latency.** Sub-2-second perceived response on turn-level moves. Engineering approach in §I; the point here is that latency belongs in the learning model, not the infrastructure backlog.

**7. Disengagement detection → recovery, not nagging.** Signals: response-latency spikes, rapid-fire guessing, "IDK" loops, error streaks ≥3, answer-spamming, tab/app switching. The response is to **change the move**: easier sub-question → modality or analogy switch → worked example then near-transfer retry → oral "tell me what we know so far" → confidence reset (surface what's already mastered) → **end the session on a win** — one easy retrieval item — rather than mid-failure, so the session's last memory isn't defeat.

**8. Accountability is a feature.** Single-digit MOOC completion is the null hypothesis for self-paced software. Adults get a target-role plan anchored by an exam date, application window, promotion goal, or project deadline (a reason the first wedge uses a role with a concrete hiring or certification milestone — the deadline ships with the learner goal), a weekly human-readable plan including "here's what slipped," and optional cohorts or mentor review. For kids (phase 2), accountability is structural: parent/teacher dashboards, session gating, escalation. The AI-first schools kept humans for exactly this; treat that as a directional warning against purely software accountability.


---

## H. Anti-dependency model: scaffold, then withdraw

The finding this section exists to defeat: field experimentation with LLM tutors has reported large performance gains *while the AI is present* that regress once it is removed. Help that doesn't survive its own absence is a demo, not an education.

> **If the learner cannot solve it without the AI later, the product did not teach.**

Two products look identical in a demo and are opposites in outcome:

- **Unscaffolded AI answer access:** learner asks, AI answers, learner pastes. Performance now, dependency later — the thinking was outsourced.
- **Scaffolded AI tutoring:** the system forces reasoning and generation now, and independent performance later, on a schedule.

**Every serious mastery claim requires all of:**

1. **No-hint performance** — checkpoints where the tutor is silent; mastery only counts if passed here.
2. **Explanation or reasoning check** — "convince me" probes; fluent guessing dies here.
3. **Delayed retention** — re-verification at 7 and 30 days; mastery decays in the model until re-verified.
4. **Transfer or near-transfer** where the domain allows — isomorphic surface changes (near) and same-structure-new-domain items (far) that were never tutored.

**Withdrawal mechanics, all first-class product features:** scheduled AI-withdrawal blocks (solo mode) with the with/without performance gap shown to the learner; hint budgets that shrink as mastery estimates rise — fading is scheduled, not optional; explain-back sampling on ~1 in 3 correct answers; project-based application where the tutor may coach process but not content; oral defense / viva mode probing causal structure; and confidence calibration — learners rate confidence before feedback, the system scores calibration and shows them where they're overconfident, which is itself a metacognitive curriculum.

The commercial reading: anti-dependency is not just ethics, it is the product's proof. "Our learners pass without us in the room" is the only efficacy claim that survives due diligence from a school district — or a skeptical adult.

**Career-readiness withdrawal is stricter than academic withdrawal.** The learner must perform realistic work without answer-level AI assistance: debug an unfamiliar failure, design a solution under constraints, analyze incomplete data, make trade-offs, explain a decision, respond to review feedback, and recover from an injected mistake. The system may provide the tools that exist in the real workplace, but it must distinguish between permitted professional tooling and hidden tutoring assistance. Readiness evidence records the assistance policy used for each simulation.

A portfolio project alone is insufficient because it can be copied, over-scaffolded, or generated. Each important artifact is paired with provenance, checkpoints, an oral or written defense, modification requests, and at least one unseen follow-up task. The question is not “did the learner submit a polished project?” but “can the learner independently reproduce, explain, modify, debug, and defend the underlying work?”


---

## I. System architecture

**One engine, policy-configured shells.** The engine is age-agnostic pedagogy; the shells (adult self-learner first; kid/school in phase 2) differ only via a policy table: session length, tutor persona, safety level, reward scheme, assessment strictness, accountability hooks, free-text constraints. Never fork.

**Core learning-engine components:** knowledge graph; fine-grained skill nodes (with concept nodes where a subject needs them); prerequisite graph; learner mastery model; misconception model; forgetting/decay model; spaced-retrieval scheduler; item bank; **item validation pipeline (§L)**; Socratic tutor policy (state machine); hint ladder; step evaluator; **no-hint assessment engine; delayed retention probes; transfer task engine**; disengagement detector; motivation/accountability layer; analytics and evaluation harness; safety and privacy layer.

**Career-readiness layer:** versioned RoleProfile and CompetencyGraph; baseline GapAnalyzer; deterministic CurriculumPlanner; versioned learner-specific LearningPlan; TaskInstance, ProjectInstance, and WorkSimulationInstance generators backed by validated blueprints; artifact/provenance capture; EvidencePortfolio; deterministic ReadinessEvaluator; CompanyOverlay and IndustryOverlay; and a market-refresh pipeline that records where each requirement came from, who reviewed it, and when it expires.

```
┌──────────────────────────── Shells ────────────────────────────┐
│ Adult career UI (v1) Kid/School UI (future) │
└────────────────┬──────────────────────────────┬────────────────┘
 │ PolicyConfig
┌────────────────▼──────────────────────────────▼────────────────┐
│ CAREER-READINESS LAYER │
│ Target Role → RoleProfile/CompetencyGraph → GapAnalyzer │
│ → CurriculumPlanner → LearnerPlanVersion │
│ → Unique Task/Project/Simulation Instances → EvidencePortfolio │
│ → ReadinessEvaluator → Company/Industry Overlay │
└───────────────────────────────┬──────────────────────────────────┘
 │ role priorities + evidence
┌───────────────────────────────▼──────────────────────────────────┐
│ CORE LEARNING ENGINE │
│ Planner/Scheduler → verified task mix → Tutor Policy/LLM │
│ ▲ │ structured verdicts │
│ │ ▼ │
│ Mastery + Decay ← deterministic updater ← Step Evaluator │
│ Misconception Model Item Bank/Validation Review Scheduler │
│ No-hint Assessment Retention Probes Transfer Tasks │
│ Engagement Monitor Safety/Privacy Analytics/Eval/Audit │
└──────────────────────────────────────────────────────────────────┘
```

**The accepted control loop:**

> LLM observes / evaluates / explains → **structured JSON verdict** → **deterministic mastery updater** → **planner/scheduler** selects the next move → LLM generates the next tutoring interaction.

**The accepted career-control loop:**

> Source-backed RoleProfile → deterministic gap analysis → learner-specific curriculum compilation → unique tasks, projects, and simulations → verified evidence → deterministic readiness update → explicit remaining gaps and overlay requirements.

**The rejected control loop:**

> LLM decides what the learner knows → LLM decides mastery → LLM decides the next topic → LLM decides whether the learner is ready.

Why the rejected loop fails **as a production architecture**: it may appear to work in demos, but it does not meet the requirements of a production mastery system — auditability, reproducibility, debugging, and assessment validity. Specifically: **hallucinated learner state** (a confident narrative about the learner with no evidentiary basis); **unstable decisions** (same transcript, different verdicts across runs and model versions); **poor auditability** (a parent, teacher, or regulator asks "why did you mark this mastered?" and the honest answer is "the model felt like it"); **impossible debugging** (no reproducible state to bisect when tutoring goes wrong); and **weak assessment validity** (mastery claims that cannot survive psychometric scrutiny, which kills institutional sales permanently). The deterministic layer costs some end-to-end "magic" and buys the entire trust story.

**Supporting decisions:** model routing — small fast model for turn-level moves, large model for diagnosis, generation, and misconception analysis; hint ladders pre-generated when an item is served; token streaming; event-sourced attempts as the source of truth, with every evaluator verdict carrying full version metadata (§J) so that mastery states and analytics are derived — and rebuildable — when prompts, rubrics, verifiers, or models change.

**Curriculum control boundary.** The LLM can generate candidate explanations, examples, tasks, and project parameters, but it cannot edit RoleProfile requirements, mark competencies optional, alter readiness thresholds, or mutate the active plan. CurriculumPlanner accepts only versioned state and policy inputs and emits a LearnerPlanVersion plus a reasoned delta. The same inputs and versions must reproduce the same plan. This prevents conversational context or model updates from silently changing what the learner is expected to master.

**Uniqueness boundary.** Quality is shared at the blueprint level; learner work is unique at the instance level. Task, project, and simulation instances are parameterized by learner state, prior attempts, chosen domain, target stack, difficulty target, constraints, and a recorded seed. Before release, the instance must pass mechanical validation and duplicate/similarity checks against that learner's history and active cohort. Unique does not mean arbitrary: every instance must preserve the blueprint's competency coverage, difficulty envelope, rubric, and assistance policy.

**Role-profile governance:** job descriptions are noisy and biased, so the system must not build a mandatory curriculum from scraping alone. Role requirements combine authoritative frameworks or official objectives where available, multiple current market sources, practitioner review, learner outcome evidence, and explicit versioning. Every competency stores provenance, confidence, geography/industry scope, effective date, and review expiry.

**Revisit as the system grows:** role/competency graph authoring tooling, dynamic-plan optimization, blueprint coverage, instance-diversity measurement, multi-domain ontology consistency, per-turn routing policies, and graduating from BKT-lite toward calibrated psychometrics once item-response volume supports it.


---

## J. Data model

**Entities (storage-agnostic; Postgres + an event stream is fine initially):**

- **Account** — id, email, auth, billing, role `owner`, optional org_id. The account owner is *always* an adult (parent, teacher, or the adult learner) — one structure that unifies B2C adults, parents, homeschool, and classrooms.
- **LearnerProfile** — account_id, display_name, age_band (`adult | 13–15 | 8–12 | <8`), role (`self | child | student`), consent_flags, goals[], shell_policy_id.
- **PolicyConfig** — session_length, tutor_persona, safety_level, reward_scheme, assessment_strictness, accountability_hooks, free_text_constraints.
- **RoleProfile** — normalized role title, seniority, geography, industry, version, valid_from/to, source_refs[], reviewer_status, scope, exclusions, and readiness threshold. “Software engineer” without these qualifiers is rejected as underspecified.
- **CompetencyNode** — role capability such as “debug asynchronous failures” or “communicate a technical trade-off”; type (`knowledge | skill | tool | project | communication | work_behavior`), evidence requirements, prerequisite skill/concept refs, and assessment policy.
- **RoleCompetencyMapping** — role_profile_id × competency_id: required_level, weight, mandatory flag, accepted evidence types, freshness requirement, and source provenance.
- **CompanyOverlay / IndustryOverlay** — deltas from the common role baseline: stack, domain knowledge, interview patterns, regulatory context, and company-specific constraints. Overlays cannot silently redefine the core role.
- **CurriculumPolicyVersion** — immutable planning rules: prerequisite handling, evidence thresholds, review allocation, difficulty targets, replanning triggers, accessibility constraints, and tie-breaking rules.
- **LearnerPlanVersion** — learner_id × RoleProfile version × CurriculumPolicyVersion: ordered competency priorities, selected learning activities, estimated effort, deadlines, active overlays, adaptation reason, parent_plan_version, and declared constraints. It is an immutable snapshot; replanning creates a new version.
- **TaskBlueprint** — validated competency coverage, parameter schema, difficulty envelope, verifier, hint strategy, rubric, and allowed assistance.
- **TaskInstance** — unique learner-bound instantiation of a TaskBlueprint with learner_id, seed, parameter set, context, similarity fingerprint, source plan version, validation record, and expiry.
- **ProjectBlueprint / WorkSimulationBlueprint** — validated scenario family, competency coverage, parameter schema, constraint ranges, assistance policy, rubric, expected artifact types, hidden event families, and validity window.
- **ProjectInstance / WorkSimulationInstance** — unique learner-bound scenario with seed, selected domain/stack, dataset or inputs, stakeholder context, constraints, hidden changes/tests, similarity fingerprint, plan version, validation record, and assistance policy.
- **Artifact** — learner-produced code, analysis, design, document, presentation, or other work product with provenance, checkpoints, assistance disclosure, and immutable version history.
- **ReadinessEvidence** — learner_id × competency_id: source (`assessment | project | simulation | reviewer | workplace`), score, assistance level, verifier/reviewer, timestamp, freshness, and dispute status.
- **ReadinessState** — learner_id × role_profile_id: coverage, mandatory gaps, evidence quality, simulation status, portfolio coverage, overlay deltas, confidence interval, and status (`not_ready | developing | conditionally_ready | ready_against_profile`).
- **MarketSignal** — source-backed candidate requirement with geography/industry scope, confidence, observed frequency, first/last seen, reviewer decision, and expiry. MarketSignal never changes a RoleProfile or LearnerPlan until promoted through governance (§L).
- **SkillNode / ConceptNode** — subject, title, prerequisites[] (edge types: `prerequisite`, `component_of`, `transfer_related`), difficulty_params, common_misconceptions[], renderings[{audience, reading_level, domain_flavor, content_ref}]. Concept nodes carry explanatory structure where a subject separates "understanding X" from "performing X."
- **Item** — skill_ids[], misconception_tags[], blueprint_or_family_id, **trust_level** (`generated_untrusted | verified_practice | beta | calibrated | assessment`), source (`authored | generated`), verification_record, content_ref. Served practice and assessment use learner-specific ItemInstances rather than reusing the same surface form.
- **ItemInstance / ItemStats** — learner-bound variant with seed, parameters, similarity fingerprint, source family, exposure record, outcome, and validation; aggregate family statistics track p_correct, discrimination, hint usage, flags, and drift. This preserves unique delivery while retaining calibration.
- **MasteryState** — learner_id × skill_id: p_mastery, stability/decay params, last_practiced_at, hint_rate, **no_hint_verified: bool**, last_delayed_probe, transfer_verified where applicable.
- **MisconceptionState** — learner_id × misconception_id: evidence_count, last_seen, status (`active | resolving | resolved`), example_attempt_refs.
- **Attempt** — learner_id, item_id, context (`learn | review | assess_nohint | probe_delayed | transfer`), hints_used, latency_ms, outcome, stated_confidence, dispute_status (`none | disputed | resolved`).
- **AttemptStep** — attempt_id, idx, content, verdict, misconception_tags[], evaluator_confidence. First-class, because step evidence is what makes diagnosis auditable.
- **TutorTurn** — session_id, seq, role, move_type (`elicit | hint_1..4 | analogy | subproblem | worked_example | explain | probe_why | assess`), model_used, latency_ms, content_ref.
- **Session** — learner_id, goal, start/end, planned vs completed, engagement_summary.
- **AssessmentResult** — mode (`no_hint | delayed | transfer | oral`), score, item_results[], calibration {stated_confidence, correctness}.
- **ReviewSchedule** — learner_id × skill_id: next_review_at, interval, stability inputs — first-class so the spacing policy is inspectable and tunable, not buried in job-queue state.
- **EngagementSignal** — type (`slow_response | rapid_guess | idk_loop | error_streak | answer_spam | app_switch`), ts, recovery_move_taken, recovered.
- **VisibilityGrant** — viewer_id, learner_id, scope (`mastery_summary | session_activity | transcripts`), granted_by, expires. Defaults: parents/teachers see mastery summaries and activity; **transcript access is an explicit, logged grant** — learners need a space to be confused without an audience.
- **AuditLog** — every mastery/readiness write, plan recompile, visibility grant, policy change, requirement change, trust-level promotion, and task/project/simulation instantiation. This table is what "auditable" means operationally.

**Reproducibility and versioning.** Every evaluator verdict stores model name, model version, prompt version, rubric version, temperature/settings, verifier version, and schema version. Mastery states must be rebuildable from event logs when evaluator prompts, rubrics, verifiers, or models change. This is a handful of columns on AttemptStep and TutorTurn plus a replay job — not an MLOps chapter — and it buys four things that matter: it separates real learner improvement from evaluator drift; it enables regression testing whenever a prompt or model changes; it supports auditability for parents, teachers, institutions, and internal QA; and it keeps the deterministic learner model a durable, recomputable asset rather than a snapshot of whatever the evaluator believed that week.

**Career and curriculum reproducibility.** Every readiness decision stores RoleProfile version, CurriculumPolicyVersion, LearnerPlanVersion, competency/rubric versions, task/project/simulation blueprint and instance IDs, assistance policy, evidence IDs, and active overlays. Replaying the same state against the same versions must reproduce the same plan and readiness state. When learner evidence or the market contract changes, the system creates a new plan or profile version and reports the delta; it never silently rewrites history.

**Storage policy — three tiers:**

*Persist:* mastery state; misconception state; distilled attempt outcomes; assessment results; item-family and instance statistics; the knowledge graph; review schedules; evaluation metrics; role/competency graph versions; curriculum policy and learner plan versions; blueprint and unique-instance metadata; artifact provenance; readiness evidence and readiness states. These are the moat and the learner's property (export and delete supported).

*Store temporarily, then distill and delete:* raw tutoring transcripts (30–90 days for product debugging, shorter for minors, then reduced to derived signals); raw engagement telemetry (aggregate, then drop); debug traces.

*Never store unless explicitly required and safely handled:* unredacted PII in prompts or logs (redact at ingestion); **sensitive inferred attributes** — if a model incidentally infers something about mental health, disability, or family situation, that inference is not persisted, full stop; keystroke-level surveillance; unnecessary child transcripts. When the kid shell ships, this section graduates into a compliance program (COPPA, FERPA for US schools, GDPR-K) with its own owner and budget — planned in §P, not bolted on later.


---

## K. LLM tutoring loop

The per-turn orchestration, concretely:

1. **Load learner state** — mastery and misconception state for the session's target region; due reviews; decayed nodes.
2. **Select due reviews and target skill** — scheduler reads the active LearnerPlanVersion: reviews first (~30% of session volume), then frontier nodes whose prerequisites are verified and whose priority follows the role contract, current gaps, deadline, and recent evidence. Remediation detours occur when an active misconception blocks progress.
3. **Instantiate and serve a verified task** — choose a trusted blueprint or calibrated item family, then create a unique learner-bound instance using current mastery, prior attempts, context preferences, target stack, difficulty target, and a recorded seed. Reject duplicates or near-duplicates; run solver/test/answer-key and schema validation before serving. Pre-generate the hint ladder for that instance.
4. **Ask the learner to attempt.** Optionally capture stated confidence pre-feedback.
5. **Capture step-by-step reasoning** — multi-step items record each step as an AttemptStep.
6. **Evaluate each step** — the evaluator LLM (cross-checked by the solver where the domain allows) emits structured JSON:

```json
{
 "final_correct": false,
 "steps": [
 {"idx": 1, "verdict": "correct"},
 {"idx": 2, "verdict": "error",
 "misconception_tags": ["inverse_operation_confusion"],
 "evidence": "subtracted before isolating the term"}
 ],
 "recommended_move": "hint_2",
 "evaluator_confidence": 0.86
}
```

7. **Detect misconception** — tags accumulate as evidence in MisconceptionState; repeated evidence changes what gets scheduled, not just what gets said.
8. **Choose the tutor move via the policy state machine** — the LLM's `recommended_move` is advisory; the state machine decides.
9. **Deliver the move** — nudge question → targeted hint referencing the specific error → simpler subproblem → analogy/modality switch → worked example (followed immediately by a near-transfer retry) → direct explanation + retrieval check.
10. **Ask the learner to continue** — the pen goes back after every move.
11. **Update mastery deterministically** — evidence weighting: no-hint assessment > unaided practice > hinted practice (discounted by hints_used). The LLM never writes p_mastery. If a learner challenges a verdict, the attempt is marked `disputed` and excluded from mastery updates until reviewed or re-evaluated — evaluators are sometimes wrong, and disputed evidence must not contaminate the learner model.
12. **Decide** — advance (estimate above threshold **and** no_hint_verified), review (scheduler owns it), remediate (prerequisite or misconception drill), or assess (checkpoint due).
13. **Schedule delayed retention** — the ReviewSchedule books the 7-day probe at the moment of apparent mastery, not as an afterthought.
14. **Periodically run no-hint and transfer checks** — solo blocks and transfer items injected on schedule, with results feeding §M metrics.

**Role-to-readiness lifecycle — the tutoring loop runs inside a larger career loop:**

1. **Specify the target.** Capture role, seniority, geography, industry, target timeline, preferred company/stack if known, constraints, and prior experience. Reject underspecified goals such as “teach me AI” until converted into a bounded target.
2. **Resolve the role contract.** Select a versioned RoleProfile and applicable overlays; show the learner what is included, excluded, and uncertain.
3. **Diagnose the baseline.** Use adaptive assessment, artifact review, and self-declared experience to build a gap map. Self-report can prioritize testing but never grants mastery.
4. **Compile the learner-specific curriculum.** CurriculumPlanner creates a LearnerPlanVersion covering knowledge, tool fluency, communication, work behaviors, projects, and simulations. Testing out requires accepted evidence; no shared fixed sequence is assumed.
5. **Learn, verify, and replan.** Run tutoring, spaced review, no-hint checkpoints, and delayed probes. Material evidence changes trigger a new plan version with an explicit delta.
6. **Apply through a unique project.** Instantiate a learner-specific project from a validated blueprint. Vary the scenario, data, constraints, domain, stack, stakeholder requirements, and hidden change requests while preserving competency coverage and rubric equivalence. Capture checkpoints, provenance, modification requests, and defense.
7. **Perform a unique work simulation.** Instantiate an unseen, time-bounded, role-realistic scenario for that learner under a declared assistance policy. Inject learner-specific ambiguity, failures, changing requirements, or review feedback while preserving the simulation's calibrated difficulty and evidence contract.
8. **Update readiness deterministically.** ReadinessState changes only from accepted evidence against required competencies. A beautiful portfolio cannot compensate for an unverified mandatory gap.
9. **Issue a readiness report.** State `ready_against_profile`, `conditionally_ready`, or `developing`; list evidence, confidence, stale evidence, mandatory gaps, and company-overlay deltas. Never output a generic “job ready” badge.
10. **Prepare for a target employer or opportunity.** Apply a CompanyOverlay for stack, domain, interview, and role-specific deltas; generate a short closing plan.
11. **Maintain readiness.** Re-open decayed competencies or newly introduced market requirements and explain exactly why the learner's curriculum changed.

**Anti-annoyance rules — the part most Socratic tutors get wrong:**

- **No endless Socratic questioning.** After **two failed elicitation attempts** on the same stuck point, switch strategy and descend the ladder. Questioning is a means, not a personality; endless "what do *you* think?" is how the IDK loop is manufactured.
- **Never give the complete answer before at least one genuine learner attempt** — except in explicit explanation mode at ladder-bottom, which must be followed immediately by a near-transfer retry so the explanation gets used, not just received.
- **Correct answers still need occasional "convince me" checks** — ~1 in 3; correct-but-can't-explain caps the mastery update and flags for review.
- **Prerequisite bailout.** If step errors implicate a prerequisite, stop hinting the current item and remediate the prerequisite explicitly ("this is actually about X — let's spend three minutes there"). Hinting past a missing foundation is how hint dependency is born.
- **If disengagement appears, change the move rather than nagging** — recovery ladder (§G), skipping rungs toward worked example / confidence reset as signals escalate.
- **Explanation is a legitimate move,** entered when two elicitations fail, a prerequisite gap is found, or the learner explicitly asks and the hint budget allows. Socratic purity that ignores a struggling learner is pedagogy cosplay.

**Latency engineering:** turn moves on the fast model; diagnosis, generation, and misconception analysis on the large model; streaming everywhere; renderings cached; target <2s first token on turns, with p95 tracked as a diagnostic metric owned by a person.


---

## L. Content and item-validation pipeline

Generated tasks, explanations, and assessment items are not created equal, and treating them as if they were is how mastery numbers become fiction. Every item carries a **trust level**:

> **generated_untrusted → verified_practice_item → beta_item → calibrated_item → assessment_item**

**Promotion rules:**

- `generated_untrusted` — fresh from the model. Never shown to learners.
- `verified_practice_item` — passed mechanical verification: symbolic solver for math, test cases for code, answer-key and constraint checks elsewhere; schema-valid, renderable, tagged to skills and misconceptions. Eligible for **practice only**.
- `beta_item` — live in practice with exposure caps; accumulating response data; learner-flaggable.
- `calibrated_item` — enough responses to estimate difficulty and discrimination; statistics stable; explanations reviewed where flags or drift appeared.
- `assessment_item` — the top tier: stable difficulty, acceptable discrimination, clean worked explanation, human review where warranted. **Only items at this level may appear in no-hint checkpoints, delayed probes, or transfer assessments.**

**Standing rules:** generated items may not be used for assessment until they have passed verification *and* accumulated sufficient learner-response data — no exceptions for launch pressure. Practice items may be generated earlier when mechanical validation passes, which is what makes content volume affordable. ItemStats are computed continuously — exposure, p_correct, discrimination, hint-usage profile, flag counts, drift — and drive both promotion and demotion: the worst tail of items is culled on a schedule, and an assessment item whose statistics drift gets demoted automatically.

**Assessment leakage protection.** Assessment items require exposure controls and variant families. If an assessment item is shown too often, appears in explanations, leaks into practice, or becomes over-familiar to learners, it is demoted from assessment status. Practice can use generated variants; assessment needs protected anchor items. Concretely: assessment items are not reused casually in practice; delayed probes and no-hint checkpoints draw only from protected or calibrated pools; ItemStats tracks per-item exposure and contamination signals (familiarity-driven p_correct drift, appearances inside served explanations or hints); and demotion is automatic when leakage or drift is detected. Without exposure control, "verified mastery" quietly becomes "memorized the test" — and the product's core claim dies with it.

**Learner-specific task, project, and simulation instances.** Blueprints are shared because validity must be shared; surface work is unique because learning evidence must belong to the learner. Every instance is compiled from the active LearnerPlanVersion and includes a recorded seed, parameter set, learner-specific context, target competency set, target difficulty, assistance policy, verifier, and similarity fingerprint.

- **Tasks** vary values, data, context, representation, required explanation, and error conditions while preserving the same competency and difficulty envelope.
- **Projects** vary scenario, domain, dataset, stakeholder, constraints, stack choices, non-functional requirements, hidden change requests, and required trade-offs.
- **Work simulations** vary failures, incomplete information, review feedback, time pressure, and requirement changes while preserving rubric equivalence.
- **Assessments** use protected calibrated families that generate unique surface instances with equivalent latent difficulty; the same surface form is not reused across learners.
- **Uniqueness checks** reject exact duplicates and semantic near-duplicates against the learner's history and the active cohort. Instance diversity, collision rate, and difficulty drift are monitored.
- **Instance validation** runs after generation. Inheriting a trusted blueprint is necessary but insufficient; each instance must pass schema, solver/test, constraint, rubric-coverage, safety, and leakage checks before use.

Personalization must not become unbounded generation. The system is free to vary context and constraints, but it may not change the competency being measured, weaken the rubric, expose protected solutions, or alter the target difficulty without a versioned planner decision.

**Role and competency trust pipeline.** Career requirements need the same discipline as assessment items:

> **market_signal_untrusted → source_backed_requirement → expert_reviewed_competency → published_role_requirement → outcome_validated_requirement**

- `market_signal_untrusted` — extracted from a single posting, model output, trend report, or anecdote. It cannot change a learner's RoleProfile or required plan.
- `source_backed_requirement` — supported by multiple current sources or an authoritative standard, scoped by role, level, geography, and industry.
- `expert_reviewed_competency` — decomposed into assessable behavior with prerequisites, evidence types, and a rubric; reviewed by a practitioner or subject expert.
- `published_role_requirement` — included in a versioned RoleProfile with provenance, review date, and change rationale.
- `outcome_validated_requirement` — supported by project/simulation performance, reviewer agreement, hiring-manager feedback, or post-hire evidence where available.

A requirement may be demoted when market frequency drops, sources conflict, or the review date expires. The platform reports changed requirements as a RoleProfile version delta; it never silently moves the finish line. Company-specific requirements belong in overlays unless they are common enough to graduate into the role baseline.

A RoleProfile update does not prescribe a new fixed curriculum. It triggers deterministic replanning for affected learners. The system identifies newly required, removed, strengthened, weakened, or stale competencies; compares them with each learner's current evidence; and creates only the necessary plan delta.

**Project and simulation trust.** A project or simulation blueprint earns trust through authored scenario family → expert-reviewed rubric → pilot instances → calibrated blueprint → readiness-grade blueprint. Each learner receives a unique validated instance. Assistance policy, generation parameters, similarity fingerprint, and artifact provenance are mandatory metadata, because an AI-generated or copied submission without independent defense is not readiness evidence.

**Authoring strategy that respects the bottleneck:** the role and competency graph comes from authoritative frameworks, current market evidence, and practitioner review; certifications contribute only where they map cleanly. Experts author and validate blueprints, rubrics, protected anchor families, and invariants. Volume and learner uniqueness come from verified instance generation. Calibration comes from aggregate blueprint/family statistics, while human review concentrates on readiness-grade assessments, simulations, disputed verdicts, and drift.

**Why this much ceremony:** assessment validity is part of the product, not an optional research feature. Every advancement decision, efficacy claim, parent report, and eventual institutional sale rests on the item bank being real. An engine that promotes learners on unvalidated items isn't measuring mastery — it's generating confident noise.


---

## M. Evaluation metrics

Three strictly separated tiers. The prime directive stands: **measure learning, not engagement** — and Goodhart's law is undefeated in edtech, so diagnostics never masquerade as goals.

**Primary learning metrics** (own the roadmap; appear in efficacy claims):

| Metric | Operational definition |
|---|---|
| Mastery gain | Δ on held-out anchor items, pre vs. post, per skill |
| No-hint assessment performance | Pass rate on tutor-silent checkpoints |
| Delayed retention | 7- and 30-day probe scores vs. immediate post-mastery |
| Transfer performance | Accuracy on never-tutored near/far transfer items |
| Misconception reduction | Active-misconception count and recurrence over time |
| Hint dependency reduction | (hinted − no-hint accuracy) gap, trending down per learner |
| Time to verified mastery | Hours from first exposure to no-hint + delayed verification |
| Confidence calibration | Brier score: stated confidence vs. correctness |
| AI-withdrawal performance | Solo-block performance vs. tutored performance, gap trending toward zero |
| Productive struggle ratio | Items solved after ≥1 wrong step or genuine think-time, vs. instantly-correct and abandoned |
| Curriculum adaptation value | Improvement from replanning versus the prior plan on mastery speed, retention, or simulation performance; changes without measurable benefit are rolled back |
| Instance uniqueness and equivalence | Duplicate/near-duplicate collision rate, competency coverage, and difficulty drift across learner-specific task/project/simulation instances |

**Career-readiness metrics** (co-primary for the adult career product; computed against a named RoleProfile version):

| Metric | Operational definition |
|---|---|
| Role competency coverage | Weighted and mandatory competency coverage backed by accepted, non-stale evidence |
| Unaided work-simulation pass rate | Performance on unseen, role-realistic tasks under a declared low-assistance policy |
| Portfolio evidence coverage | Required competencies supported by defensible artifacts, modifications, and oral/written defense |
| Project rubric performance | Expert-calibrated rubric scores across correctness, quality, trade-offs, testing, documentation, and communication |
| Readiness calibration | Agreement between deterministic readiness state and blinded expert/practitioner judgment |
| Overlay delta | Remaining time/competencies between common role readiness and a named company/industry overlay |
| Time to ready-against-profile | Time from baseline diagnosis to all mandatory evidence gates for a specific RoleProfile version |
| Evidence freshness | Share of readiness evidence still inside its validity window after skill/market decay |

**External outcome metrics** — interview conversion, offers, placement, compensation, promotion, and 30/90-day workplace performance — matter commercially but are lagging and heavily confounded by geography, market conditions, networks, prior experience, communication, and employer bias. Report them with cohort definitions and uncertainty; never use placement alone as proof that the learning model caused readiness.

**Diagnostic metrics** (feed design and operations; never cited as success): drop-off points in sessions and across the graph; response latency (p50/p95 first-token); disengagement signal rates by type; recovery rate after recovery moves; session completion vs. plan; **tutor-move failure rate** — moves followed by continued failure or disengagement, from the eval harness and live data.

**Anti-metrics** (never goals, never in efficacy claims, never in investor decks as learning evidence): time in app as success; message count; XP; raw completion without mastery verification; streaks; satisfaction alone — desirable difficulties *should* depress satisfaction slightly while improving retention, and when satisfaction and retention disagree, believe retention; and **number of generated items without validation** — a content counter is not a capability; and **“job-ready” badges without a named RoleProfile, evidence contract, and uncertainty** — marketing is not measurement.

**The evaluation harness is a launch blocker:** golden tutoring transcripts with expert-labeled correct moves; an evaluator-accuracy suite (step-grading agreement with human graders); regression tests on the tutor-move policy; item statistics computed continuously. Teams that win in this category are the ones that can tell whether a change helped.


---

## N. Go-to-market waves

First, the warning that shapes everything: **B2C career acceleration, B2B workforce training, and B2B school sales are different go-to-market motions — different buyers, cycles, compliance, and support models — and a small team must not pursue them simultaneously.** Sequencing is the strategy.

| Segment | Pain | WTP | Sales cycle | Regulation | Feedback speed | Outcome measurability |
|---|---|---|---|---|---|---|
| **Adult/16+ target-role learners** | **High** | **High** | Instant | Low | **Fast** | **Strong for technical roles** |
| Certification-only learners | High | Medium–high | Instant | Low | Fast | Strong exam signal, weak job-readiness signal |
| Employer/workforce upskilling | High | High | Medium–long | Medium | Medium | Strong if work tasks are observable |
| Tutoring/bootcamp partners | Medium–high | Medium (B2B2C) | Medium | Medium | Medium | Good with shared rubrics |
| Homeschool families | High | Medium–high | Short | Medium | Medium | Strong academic, not career outcome |
| Private schools | Medium | Medium | Long | Medium–high | Slow | Academic outcomes |
| Public schools / institutions | Medium | Low–medium | **Very long** | **High** | **Slow** | Academic outcomes |

**Wave 1 — One adult technical role system, not a generic course catalogue.** The learner chooses a bounded role such as junior data analyst, associate cloud engineer, junior cybersecurity analyst, or QA automation engineer. Pick **one** role using five criteria: objective or semi-objective verification; a coherent common core; realistic simulations feasible in software; visible demand across more than one employer; and a role scope bounded enough to model and verify with high quality.

A certification can anchor part of the knowledge graph and provide a deadline, but the role system must go beyond the exam: projects, debugging, tool fluency, communication, work simulations, portfolio evidence, and company-overlay deltas. The positioning is “become ready against this role contract,” not “pass this test.”

Why this wedge: lower child-safety burden; fast learner feedback; direct willingness to pay; a clear career outcome; easier assessment validity; and lower reputational risk while iterating. The first learner contract should explicitly define role, level, geography, included tool stack, evidence requirements, and exclusions.

**Wave 2 — Adjacent roles and B2B2C career partners.** Expand from the first role to one adjacent role that reuses most of the graph, proving that role-graph, blueprint, and curriculum-policy authoring are compositional rather than a bespoke services business. Pilot with selected bootcamps, career coaches, universities' continuing-education units, or workforce programs where humans provide accountability and disputed-evidence review. Add employer/industry overlays only where a partner supplies credible requirements and reviewers.

**Wave 3 — Employer/workforce upskilling.** Sell gap diagnosis, adaptive reskilling, and work-simulation evidence for internal mobility or onboarding. This requires privacy boundaries between learner coaching and employer reporting: employers receive agreed competency evidence, not unrestricted transcripts or inferred personal attributes.

**Wave 4 — Homeschool, tutoring centers, then schools.** The underlying mastery engine remains applicable to younger learners, but the kid/school shell is a separate safety, compliance, pedagogy, and go-to-market program. Enter only after the engine is proven and the company can fund a dedicated workstream. Private schools precede public institutions; public-school deployment requires compliance, standards alignment, references, and independent evaluation.

**One team, one motion at a time.** The architecture can support multiple shells and role profiles; the company cannot operationally launch all of them at once.

---


## O. Risks and mitigations

| Risk | How it shows up | Mitigation |
|---|---|---|
| Hallucinated explanations | Confident wrong math; invented facts | Curated/retrieved explanation content; solver/test verification for tasks and grading; evaluator-accuracy suite; human review for reused generated items |
| Hallucinated learner state | "The model thinks she's ready" | Prevented by design: deterministic mastery updater; LLM verdicts are evidence, not decisions; AuditLog on every write |
| Wrong evaluator verdict | Learner gives valid reasoning but the system marks it wrong, or accepts invalid reasoning as correct | Learner challenge button; human/sample review queue; evaluator confidence threshold; disagreement checks between solver, LLM evaluator, and rubric; disputed attempts excluded from mastery updates until resolved |
| Over-helping | Learners "succeed" only with hints | Hard hint ladder with budgets; never-answer-first rule; hint dependency as a primary metric |
| Learner dependency | Gains vanish when AI is absent | Scaffold-then-withdraw (§H): no-hint gates, withdrawal blocks, scheduled fading |
| Gaming the system | Hint-farming, answer-spam, rapid guessing | Detection discounts mastery evidence; item variants; zero reward for completion without verification |
| Invalid assessment | Mastery numbers nobody should trust | Trust-level pipeline (§L); anchor items; discrimination stats; automatic demotion on drift |
| Motivation collapse | Silent churn after week 2 | Recovery ladder; end-on-a-win; deadline anchoring; weekly plan; optional cohort/mentor |
| Shallow gamification creep | XP/streaks sneak in "for retention" | Mastery-map visuals only; principle 5 enforced in design review; watch Wave-2 pressure especially |
| Privacy breach | Transcript leak; PII in logs | Redaction at ingestion; short transcript retention; distill-then-delete; export/delete rights; AuditLog |
| Unsafe conversations (minors) | Off-topic or harmful chat | Phase-2 kid shell: constrained free text for youngest, topic fences, moderation, human escalation, logged transcript-access grants |
| Bias in adaptation | Systematic under-challenging of groups | Audit mastery-gain and difficulty-served distributions across cohorts; rendering review for stereotyping |
| Weak curriculum alignment | "Doesn't match our standards" | Wave 1 sidesteps it (blueprints *are* the curriculum); standards mapping built in Wave 2–3 |
| Measuring engagement instead of learning | Dashboards full of DAU | §M tier separation; learning metrics own the roadmap |
| Building two products too early | Team split across shells and motions | Adult shell only until engine metrics clear gates; policy config, not forks; one GTM motion at a time |
| Slow latency | Learners tab away mid-turn | Model routing, hint pre-generation, streaming; p95 owned as a KPI |
| Content quality decay | Ambiguous or broken items accumulate | ItemStats culling; learner flagging; review concentrated on assessment tier |
| Institutional distrust | "Black box teaching my kid" | Transparency dashboards; auditable mastery decisions; human escalation; teacher-as-coach positioning; independent evaluation before school claims |

| False job-readiness promise | Learner completes assigned content but cannot perform in a real role | Readiness tied to a named RoleProfile version, mandatory evidence gates, independent simulations, uncertainty, and explicit exclusions; never guarantee employment |
| Role-contract drift | Curriculum becomes stale while tools and expectations change | Versioned market-refresh pipeline; provenance and expiry on every requirement; periodic expert review; delta reports instead of silent changes |
| Company variance | A learner is ready for the common role but missing a target employer's stack or process | Core baseline plus CompanyOverlay/IndustryOverlay; readiness report lists the exact delta and closing plan |
| Portfolio authenticity failure | Polished projects are copied or heavily generated | Checkpointed provenance, assistance disclosure, hidden follow-up tasks, modification requests, and oral/written defense |
| Soft-skill blind spot | Technical tasks pass but communication, prioritization, and judgment fail | Competency graph includes communication/work behaviors; realistic stakeholder and review simulations; human review for consequential judgments |
| Hiring-outcome confounding | Placement rates rise or fall for reasons unrelated to learning quality | Separate verified-readiness metrics from external hiring outcomes; cohort controls, uncertainty, and no causal claim without suitable evaluation |
| Overfitting to one role or stack | Learners memorize one toolchain but cannot transfer | Core concepts plus tool-specific overlays; unseen transfer tasks; second-role authoring test in year one |
| Static-curriculum drift | Learners with different baselines receive the same sequence, or the plan becomes stale after new evidence | RoleProfile remains the destination; deterministic CurriculumPlanner creates versioned learner plans and replans only from logged evidence or constraint changes |
| Personalization without validity | Unique tasks become easier, ambiguous, or misaligned with the competency | Generate from trusted blueprints; enforce difficulty/coverage invariants; validate every instance; monitor family-level drift |
| Task or project collision | Learners receive identical or near-identical work and can copy evidence | Learner-bound seeds, semantic fingerprints, cohort-level duplicate checks, hidden changes, provenance, and defense |


---

## P. 12-month product strategy

Four horizons, kept deliberately distinct:

**Long-term vision (3–5 years).** A learner selects a target role or educational outcome, and the platform maintains a durable, learner-owned model of what that person knows, what evidence they can produce, what the destination requires, and what gap remains. For adults, it becomes a career accelerator: diagnosis, adaptive learning, verified mastery, realistic work practice, evidence portfolio, employer overlays, and continuous upskilling. For younger learners and schools, the same mastery engine is exposed through a safer, curriculum-aligned shell. The instructional layer is automated; the human layer is strengthened by the time it frees.

**The 12-month reality check.** With 2–4 engineers and one learning designer, the first year cannot simultaneously build a high-integrity career product and a production school/kid program. The architecture preserves both; delivery focuses on the adult career shell. School/kid work in year one is limited to requirements, privacy primitives, and architectural compatibility unless a separate funded team exists.

For the first 6–12 months, this is not mainly an AI company. It is a learning-and-career-systems company using AI as the interface. The year is spent on the execution bottlenecks: role and knowledge-graph authoring; validated item and simulation creation; misconception taxonomy; assessment calibration; artifact provenance; tutor and readiness evaluation; content quality; latency; market-contract governance; and learner trust.

**Quarter by quarter:**

- **Q1 — 90-day validation sprint (§Q).** One target role, adult shell, coarse RoleProfile plus a deeply validated competency slice, full tutoring/mastery loop, and at least one realistic work simulation. Output: evidence that the engine can close and verify a role-relevant gap — not a public career promise.
- **Q2 — First complete role system.** Expand from the proof slice toward the role's full common core; launch a paid beta with a published readiness contract, dynamic learner-specific curricula, a protected assessment pool, two to four unique checkpointed project instances per learner, multiple unique simulation instances, an evidence portfolio, and honest readiness reports. A certification is integrated only where it maps cleanly to the role.
- **Q3 — Career-readiness calibration.** Readiness calibration against blinded practitioner review; portfolio provenance and defense; company/industry overlay v1; accountability layer (cohort and optional mentor); authoring/governance tooling; efficacy and readiness memo v1. Begin one adjacent role only if graph reuse is demonstrably high.
- **Q4 — Repeatability and partner pilot.** Launch the adjacent role or stop to build authoring tooling if it remains bespoke. Pilot with a selected career/bootcamp/workforce partner; test privacy-safe evidence sharing and reviewer workflows. Conduct school/kid discovery and compliance scoping, but do not split the core team into a second product launch.

**Future school/kid expansion.** It requires a compliance program with an owner; age-specific pedagogy and safety; constrained free-text and topic fencing; human escalation; curriculum/standards alignment; parent/teacher workflows; and independent evaluation. The career product validates the engine, but does not automatically validate minor safety or school adoption.

**What would change this plan:** learners master nodes but fail work simulations (the graph or transfer design is wrong); experts disagree with readiness decisions (rubrics/readiness evaluator become the priority); first-role completion is strong but authoring an adjacent role remains nearly as expensive (stop, build graph/simulation tooling); retention fails despite verified progress (add human accountability); or market requirements change faster than governance can review them (narrow the role/market scope).

---


## Q. 90-day validation sprint

**What this is:** an evidence-generation sprint to prove the role-relevant learning loop. **What this is not:** the full platform, a complete career academy, or a job-placement promise. The complete role system, multiple career paths, calibrated simulations at scale, company overlays, school shell, and compliance program are longer programs.

**The sprint exists to answer ten questions:**

1. Can the platform convert a bounded target role into a **traceable, versioned competency contract** that practitioners consider credible?
2. Can it diagnose a learner's **role-relevant gaps** more accurately than self-report or a linear placement quiz?
3. Does tutoring produce better **no-hint performance** on the selected competency slice?
4. Does **hint dependency decrease** within learners over the sprint?
5. Can the system **detect common misconceptions** against a hand-built taxonomy?
6. Do learners **retain after 7 days**?
7. Does the **deterministic learner model behave sensibly** — no absurd mastery jumps, decay that matches observed forgetting?
8. Can generated, verified content be trusted for practice, and is latency acceptable in real tutoring conversations?
9. Can learners complete at least one **unseen, role-realistic work simulation without answer-level tutoring**?
10. Do the system's readiness/evidence conclusions agree sufficiently with blinded practitioner review — and do learners return without shallow gamification?

**Scope — coarse role map, deep competency slice:** one target technical role, adult shell, web only. Normalize the role by level, geography, market, timeline, and known stack or industry constraints; unknown overlays remain explicitly unresolved. Decompose the role into a coarse RoleProfile and CompetencyGraph, but deeply validate a coherent 40–80-node slice that supports one realistic work outcome. The slice must include conceptual knowledge, tool use, debugging/problem solving, and communication or decision explanation — not only exam questions. Each learner receives a distinct LearnerPlanVersion and unique task, project, and simulation instances even when targeting the same role and competency slice.

The Phase 1 item target can still reach 1,500–3,000 practice items, but the 90-day proof loop uses several hundred verified practice items, a protected reviewed checkpoint pool, and one or two pilot work simulations. The RoleProfile and competency graph may incorporate a certification blueprint where useful, but the certification is evidence input, not the destination. The §K tutoring loop runs end to end; ReadinessState is computed only for the validated slice and must be labeled `partial_profile_evidence`, never “job ready.”

**Weeks 1–2 — Role contract and foundations.** Select the target role; define role, level, geography, included stack, exclusions, and source-backed coarse competency map; choose a 40–80-node proof slice with one clear work outcome; create 400–600 seed items; design one validated simulation blueprint and its rubric, capable of producing unique learner instances; build 20–30 golden tutoring transcripts and evaluator test cases. *Gate: two or more practitioners approve the RoleProfile scope and proof slice; evaluator step-grading reaches ≥90% agreement on the controlled test set.*

**Weeks 3–4 — Tutoring loop v0.** Planner, verified task provider, tutor-move state machine, evaluator JSON, solver/test verification, hint budgets, streaming UI, latency baseline, and event/version logging. *Gate: end-to-end tutoring on at least 30 proof-slice nodes; p95 first token <2.5s; replay produces identical mastery updates from identical evidence/version inputs.*

**Weeks 5–6 — Learner model, gap map, and curriculum planner.** Baseline diagnostic; deterministic mastery updates with hint-discounted evidence; decay and ReviewSchedule; learner-specific plan compilation and replanning; bounded sessions with role/readiness map. *Gate: dogfooders complete multi-session arcs; no absurd mastery behavior; gap map reviewed against expert judgment on sample learners.*

**Weeks 7–8 — Assessment and evidence.** No-hint checkpoints; 7-day probes; explain-back; confidence calibration; top misconceptions; artifact provenance; protected calibrated variant families; unique project/simulation instance generation; runner and rubrics. *Gate: verified mastery computable per node and ReadinessEvidence computable for the proof slice; disputed grading excluded from state updates.*

**Weeks 9–10 — Closed beta.** Recruit 20–50 learners actively targeting the role or a closely aligned certification/job transition. Read transcripts and failure traces daily; fix tutor-policy failures; run a unique unseen work-simulation instance for each learner; collect practitioner-blinded ratings for a sample; ship two disengagement recovery moves and a weekly role-gap plan. *Gate: ≥50% week-2 return without addictive gamification; hint dependency trend visible; work-simulation failures produce actionable gap diagnoses rather than generic feedback.*

**Weeks 11–12 — Evidence and decision.** Latency pass; cull weak items; compare deterministic readiness/evidence conclusions with practitioner review; publish the honest sprint memo covering all ten questions, uncertainty, and failure cases; test pricing around the role outcome, not content access. *Gate: go/no-go on building the complete Q2 role system — expand, fix, narrow, or kill with evidence.*

**The 90-day deliverable is not an app or a “job-ready” badge. It is an instrumented claim:** *for this named role profile and validated competency slice, the system can diagnose gaps, teach them, verify independent retention, and predict performance on a realistic work task with stated uncertainty.*

---


## R. Positioning statement

> **Choose a role. The platform maps the destination, diagnoses the gap, teaches what is missing, verifies independent performance, and proves readiness with work evidence.**

**A chatbot answers. A tutor diagnoses. A mastery engine remembers. A career engine converts mastery into role readiness.**

This platform is a persistent one-to-one AI tutor, mastery engine, and career accelerator: an LLM Socratic front-end wired to deterministic mastery, misconception, forgetting, assessment, curriculum-planning, and readiness back-ends. The learner selects a bounded target role; the platform resolves a versioned RoleProfile, diagnoses prior knowledge, compiles and continuously updates a learner-specific curriculum, teaches every required competency in scope, schedules retention, and instantiates unique tasks, projects, and work simulations. It maintains an evidence portfolio until the learner satisfies the published readiness contract.

It replaces the passive, generic, low-feedback instructional layer of online learning and traditional teaching — and deliberately does not replace school as a human social environment or teachers and mentors as coaches, guides, reviewers, and accountability partners. It scaffolds, then withdraws: if the learner cannot perform without answer-level AI assistance later, the product did not teach.

The promise is ambitious but bounded. It does not claim to teach every possible technology, prepare someone for every employer without adaptation, or guarantee hiring. It makes the learner **ready against a named role, level, market, and competency contract**, then identifies the exact company-, industry-, or stack-specific delta. The role contract is shared; the curriculum and learner work are continuously personalized, versioned, and unique. It measures learning and role performance, not content consumption; treats assessment, simulations, and artifact provenance as the product; and earns expansion from one technical role to adjacent careers, workforce partners, and eventually school-age learning shells — one independently verified readiness claim at a time.

The moat is not the LLM. The moat is what the system knows about the learner, what the target role demonstrably requires, how rigorously both are modeled, and the proof that the learner can still perform when the tutor leaves the room.
