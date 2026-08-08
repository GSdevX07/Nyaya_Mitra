# HackVerse 2.0 — Eval Round 1 Playbook
**Nyaya Mitra | Team Tensor Titans**

## What this round actually is
Your scoring sheet has four criteria — Problem Understanding, Innovation & Creativity, Feasibility & Planning, Team Coordination — and nothing about a working demo. That means this is almost certainly an **idea/plan screening round**, run before (or in the first hour or two of) the 36-hour build window, to approve teams before they start coding. Treat it as your literal first task — before anyone opens an editor.

**Total: 40 marks across 4 criteria + a Comments field.** Here's how to maximize each line, with a script for each so nobody's improvising in front of a judge.

---

## 1. Problem Understanding — /10
**What's actually being checked:** did you research this, or pick a trendy AI-for-good topic with no depth behind it?

**Your evidence:**
- 73% of India's prison population — 371,440 people — are undertrials, not convicted (NCRB data)
- Two-thirds are from SC/ST/OBC communities; ~30,000 have already spent 3+ years in custody
- BNSS Section 479 (successor to CrPC 436A) already grants release once someone has served half their maximum possible sentence
- Root cause is operational, not legal: jail staff strength is ~63,000 against a sanctioned ~100,000; national occupancy is 112.7% of capacity

**Say this (~30s):**
> "Our theme is AI for Sustainable and Social Impact. We're solving India's undertrial prisoner crisis — 73% of India's prison population, over 371,000 people, are undertrials, not convicted. Under Section 479 of the BNSS, anyone who's served half their maximum sentence is already legally entitled to release. This isn't a legal gap — the right exists — it's an operational one: understaffed jails and untracked case files mean nobody applies it at scale. We researched this from actual NCRB prison statistics and the statute text itself, not a guess."

---

## 2. Innovation & Creativity — /10
**What's actually being checked:** is this a fresh angle, or the tenth "AI chatbot for X" in the room?

**Your evidence — two things nobody else will pitch:**
- A **Records Completeness Agent** that flags missing paperwork *before* a case stalls — most solutions assume the file is complete and only fail at drafting time
- A **Status Tracking Agent** that follows a case *after* filing — because a large share of delay happens after eligibility is established, not before
- A deliberate ethical design choice: the AI never decides eligibility (that's pure deterministic rule logic); it only retrieves, drafts, and explains — with mandatory human sign-off

**Say this (~30s):**
> "Most legal-AI ideas stop at a chatbot that answers legal questions. We built something different — a full case-lifecycle operations platform with eight specialized agents, including two nobody else will pitch: one that catches missing paperwork before a case ever stalls, and one that tracks a case after it's filed, since that's actually where most delay happens. And we made a deliberate call: our AI never decides eligibility — that's a fixed rule, not a guess — it only drafts and explains, with a human lawyer signing off on everything."

---

## 3. Feasibility & Planning — /10
**What's actually being checked:** is there a realistic, scoped plan, or just enthusiasm?

**Your evidence:**
- Hour-by-hour roadmap with phases, owners, and a defined "done" for each step (show the Master Roadmap doc physically)
- Deliberately scoped decisions that make this buildable in 36 hours: synthetic case data (no real prisoner data — also the ethically correct call), a simulated-but-honestly-labeled court-status tracker (no public API exists to integrate for real), and a free, fully local AI stack that never depends on hackathon wifi
- A risk register with named fallbacks (e.g., Streamlit if the React dashboard runs behind)

**Say this (~30s):**
> "We scoped this specifically to be buildable in 36 hours. We're using synthetic case data — not real prisoner records — a simulated but clearly-labeled court-status tracker since no public API exists for that, and a free, fully local AI stack so our demo never depends on wifi or an API quota. We have an hour-by-hour roadmap with owners for every piece and named fallbacks if something runs behind schedule." *(hand over / open the roadmap doc here)*

---

## 4. Team Coordination — /10
**What's actually being checked:** real role clarity, or four people who'll all touch the same file at Hour 30?

**Your evidence:**
| Member | Owns |
|---|---|
| Sathwik G | Backend & agent orchestration |
| N B Tanisha | LLM / RAG layer |
| Vedhanth M | Data layer & ingestion pipeline |
| Nishanth Prakash Reddy | Frontend & demo |

- Shared task board mapped directly to the roadmap
- Check-ins at every phase boundary, not just at the end
- A planned rest-rotation so nobody's presenting exhausted at Hour 36

**Say this (~30s):**
> "Each of us owns a distinct layer end-to-end — Sathwik on backend and orchestration, Tanisha on the LLM and retrieval layer, Vedhanth on data and the ingestion pipeline, and I'm on frontend and the demo. We're working off a shared task board mapped to our roadmap, with check-ins at every phase boundary, and we've planned rest rotation so we're not presenting exhausted at Hour 36."

---

## The Full ~2-Minute Walkthrough
If the judge just says "walk me through it," run the four scripts above back to back, in order — that's already a complete, rubric-aligned answer with no gaps.

## Bring physically
- The Master Roadmap doc (laptop or printed)
- Your architecture diagram slide
- The role-assignment table above, visible

## Anticipated questions + crisp answers
| Judge asks | Answer |
|---|---|
| "Why couldn't a lawyer just do this manually?" | They can, in theory — the problem is scale: thousands of files, a handful of overloaded legal-aid lawyers, no one tracking who's already crossed the threshold. |
| "What data are you actually using?" | Synthetic case records we designed ourselves — deliberately, since real prisoner data shouldn't be touched for a hackathon prototype. |
| "What if the AI drafts something legally wrong?" | It can't decide anything — eligibility is a fixed rule, every draft is grounded in retrieved statute text, and a human lawyer signs off before anything is filed. |
| "What's your tech stack?" | State whatever you've locked in from the Master Roadmap's Section 3 — say it's a deliberate choice, not a default, and name one trade-off you considered. |
| "Why this theme over Business Transformation?" | This is fundamentally an equity/capacity problem for an underserved population, not an efficiency problem for a business. |

## One tactical tip
Echo the rubric's own words back at the judge — *"clarity," "background research," "out-of-the-box," "realistic implementation steps," "role distribution."* A judge scoring off a printed sheet responds well to hearing their own criteria language reflected in your answer. Every script above already does this — stick close to the wording.
