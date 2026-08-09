# Nyaya Mitra Master Build Roadmap v2 (Final)
**Team Tensor Titans | HackVerse 2.0 | MIT Bengaluru | Aug 8–10, 2026**

This supersedes the earlier roadmap. What's new: tech stack is now a genuine choice (organizers confirmed you have full freedom), every phase is tagged to exactly which rubric line it earns you points on, and there's more implementation-level detail throughout.

---

## Table of Contents
0. What Changed From v1
1. The Two Rubrics You're Actually Being Scored Against
2. Ground Rules
3. Tech Stack Decision Framework (now flexible)
4. Team Role Assignment
5. Repo & Folder Structure
6. Phase −1 Eval Round 1 (pointer to separate Playbook)
7. Phase 0 Setup
8. Phase 1 Data & Knowledge Layer
9. Phase 2 Core Agent Logic
10. Phase 3 Interfaces
11. Phase 4 Integration & Hardening
12. Phase 5 Polish & Final Demo Prep
13. Mid-Hackathon Checkpoints
14. Data Schemas & Prompt Templates
15. Judging-Day Checklist (both rounds)
16. Risk Register
17. Stretch Goals

---

## 0. What Changed From v1
- **Tech stack is a decision, not a mandate.** Section 3 gives you a real trade-off analysis instead of a single prescribed stack.
- **Every phase is now tagged** with which scoring line it feeds both the Eval Round 1 sheet (Problem Understanding / Innovation & Creativity / Feasibility & Planning / Team Coordination) and the final judging rubric from your deck template (Completeness of Design / Impact / Uniqueness / Presentation / Ethics).
- **New:** a concrete `llm_client.py` fallback pattern, mid-hackathon checkpoints (Hour 18 and Hour 30 gut-checks), and more granular per-agent test steps.

---

## 1. The Two Rubrics You're Actually Being Scored Against

You have two separate judging events, with two different sheets. Know both before you plan a single hour.

| | **Eval Round 1** (idea screening, early) | **Final Judging** (from your deck template) |
|---|---|---|
| Criteria | Problem Understanding, Innovation & Creativity, Feasibility & Planning, Team Coordination | Completeness of Design (30%), Impact towards Theme (30%), Uniqueness/Creativity (25%), Presentation (10%), Ethical Considerations (5%) |
| What it's scoring | Your plan, your research, your team setup **no working code needed** | Your actual built prototype + demo + pitch |
| Prep material | `Eval_Round_1_Playbook.md` (separate doc) | This roadmap's Phases 0–5, your deck, your video script |

**Where to spend marginal hours, given this:** Completeness of Design + Impact = 60% of the final score. That means once Eval Round 1 is cleared, your build hours should skew toward **Phase 2 (agent depth)** and **Phase 3 (dashboard clarity that visibly proves the design is complete)** not toward stack novelty or frontend flourishes for their own sake. Ethics is only 5% of the final score, but it's nearly free the human-sign-off gate and deterministic eligibility logic you're already building satisfy it entirely, so don't over-invest extra time there beyond what Phase 2 already gives you.

---

## 2. Ground Rules

- **Synthetic data only.** Never source or simulate real prisoner names/records. This is both the ethical call and a stronger pitch line say it out loud in both eval rounds.
- **Be explicit about what's live vs. simulated**, especially Status Tracking no public court-record API exists to integrate in 36 hours. Label it clearly rather than hiding it. Judges penalize overclaiming far more than an honestly-scoped mock.
- **The eligibility decision is never made by an LLM** it's a deterministic Python rule. The LLM explains, retrieves, and drafts; it never decides. This is your strongest answer to "how do you prevent hallucination from wrongly affecting someone's custody status."
- **A human lawyer signs off before anything is "filed."** Build this as an actual UI gate, not a slide claim.
- **Confirm with mentors early:** whether there's a mid-hackathon mentor check-in you need to plan around, and whether a Celonis-aligned track exists worth targeting (see Section 17).

---

## 3. Tech Stack Decision Framework (Now Flexible)

You have full rights to change anything from the deck. Treat this as a real engineering decision and documenting *why* you chose what you chose is itself Feasibility & Planning evidence, not just a footnote.

### Path A IBM Open Stack (recommended default)
Ollama running Granite locally, BeeAI framework for orchestration, Docling for document parsing, Data Prep Kit for the cleaning pipeline, ChromaDB for RAG, with one agent (Drafting) also wired to real watsonx.ai as a bonus live-cloud path.

- **Pros:** entirely free, works fully offline (your demo never depends on venue wifi), keeps your existing deck/video narrative ("Built on IBM") consistent so you don't have to redo slides, and IBM is a named collaborator on this hackathon using their real tooling is a credible signal to IBM-affiliated judges specifically.
- **Cons:** more moving parts to set up (multiple libraries), Ollama model pulls/inference can be slow on weaker laptops, BeeAI has a learning curve if nobody's used it before.

### Path B Fastest Generic Stack
Groq's free API (very fast Llama/Gemma inference) or Gemini free tier for the LLM calls, a hand-rolled Python state machine instead of a dedicated agent framework (genuinely faster to build than learning a new framework under time pressure, for a pipeline this linear), plain `pytesseract`/`PyPDF2` instead of Docling.

- **Pros:** less new-tool learning curve, potentially faster raw inference, fewer setup failure points.
- **Cons:** breaks your existing pitch-deck narrative (you'd need to update the "Built on IBM" slide), forfeits alignment with IBM as a named hackathon collaborator.

### Recommendation
**Default to Path A.** Only fall back to Path B if you hit a real blocker by Hour 3 (e.g., Ollama won't run on available hardware, or nobody can get a watsonx account working). Structure your code so that swap is cheap see the fallback pattern below.

### The one file that makes stack-swapping painless
```python
# backend/app/llm_client.py single choke point for every LLM call in the app
def generate(prompt: str, system: str = "") -> str:
    try:
        return _call_watsonx(prompt, system)          # Path A primary
    except (TimeoutError, QuotaExceededError, ConnectionError):
        return _call_ollama_granite(prompt, system)     # Path A local fallback
    # To pivot to Path B entirely: replace both functions' bodies with _call_groq(...)
    # No other file in the codebase should ever call an LLM API directly.
```
Every agent calls `generate()`, never a provider SDK directly. This is what makes "we have full rights to change the stack" a 10-minute change instead of a re-architecture if you need it mid-hackathon.

---

## 4. Team Role Assignment
*(Rubric tag: Team Coordination)*

| Member | Primary owns | Secondary |
|---|---|---|
| **Sathwik G** | Backend orchestration the agent pipeline, orchestrator, FastAPI wiring | Integration testing (Phase 4) |
| **N B Tanisha** | LLM layer prompts, RAG retrieval, `llm_client.py` | Multilingual Explainer Agent |
| **Vedhanth M** | Data layer synthetic dataset, statute corpus, ingestion pipeline | Notification + Status Tracking Agents |
| **Nishanth Prakash Reddy** | Frontend lawyer dashboard, family view, agent-activity log | Demo rehearsal lead, README |

Everyone reviews everyone else's code at each phase boundary below don't let integration happen only at Hour 30.

---

## 5. Repo & Folder Structure

```
nyaya-mitra/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── llm_client.py            # the single choke point from Section 3
│   │   ├── agents/
│   │   │   ├── eligibility_agent.py
│   │   │   ├── completeness_agent.py
│   │   │   ├── prioritization_agent.py
│   │   │   ├── notification_agent.py
│   │   │   ├── retrieval_agent.py
│   │   │   ├── drafting_agent.py
│   │   │   ├── explainer_agent.py
│   │   │   ├── status_agent.py
│   │   │   └── orchestrator.py
│   │   ├── rag/
│   │   │   ├── build_index.py
│   │   │   └── vector_store.py
│   │   ├── data_prep/
│   │   │   └── ingest_pipeline.py
│   │   ├── models/                  # Pydantic schemas
│   │   ├── api/                     # route handlers
│   │   └── tests/                   # one smoke test per agent see Phase 2
│   └── requirements.txt
├── frontend/
├── data/
│   ├── synthetic_cases/
│   ├── statutes/
│   └── processed/
├── docs/
│   └── architecture-diagram.png
├── .env.example                     # keys as blank placeholders, never real ones
└── README.md                        # setup + "what's live vs. mocked" section
```

---

## 6. Phase −1 Eval Round 1
*(Rubric tag: all four Round 1 criteria)*

Do this **before** Phase 0. Full script and talking points are in the separate `Eval_Round_1_Playbook.md` read it as a team, assign the four speaking parts, and rehearse the ~2-minute walkthrough once out loud before you're in front of a judge.

---

## 7. Phase 0 Setup (Hour 0–2)
*(Rubric tag: Feasibility & Planning)*

| Step | What | Why | Done when |
|---|---|---|---|
| 0.1 | Create GitHub repo, push the skeleton above, protect `main`, agree branch naming (`feat/agent-name`) | Prevents Hour-30 merge chaos | Repo exists, everyone's pushed once |
| 0.2 | Each member: Python 3.11 venv, install core deps per your Section 3 stack choice | Avoids "works on my machine" later | `pip freeze` matches across machines |
| 0.3 | If Path A: install Ollama, `ollama pull granite4:8b` (or a smaller quantized tag on weaker laptops), on at least 2 laptops | This is your demo-day insurance test before you need it | Local prompt returns text |
| 0.4 | If using watsonx.ai: sign up for the Lite plan (free, card for identity verification only), get API key/project ID/region, store in `.env` (never commit) | Unlocks the real-cloud-usage path | Test call returns a completion |
| 0.5 | Build `llm_client.py` skeleton (Section 3) even before agents exist | Locks in the fallback pattern from day one instead of retrofitting it | File exists, both provider functions stubbed |
| 0.6 | Shared task board with every step in this doc as a card | Keeps 4 people from duplicating work | Board exists, Phase 0–1 cards assigned |

---

## 8. Phase 1 Data & Knowledge Layer (Hour 2–9)
**Owner: Vedhanth M, supported by N B Tanisha for embeddings**
*(Rubric tags: Completeness of Design, Ethical Considerations)*

| Step | What | Why | Done when |
|---|---|---|---|
| 1.1 | Design the synthetic case schema (Section 14) and generate 15–20 records: 5 hand-crafted "hero cases" engineered to hit each agent's decision branch cleanly (clean-eligible, eligible-but-missing-docs, not-yet-eligible, urgent/elderly, multi-FIR edge case), plus 10–15 varied ones for queue realism | The demo needs the queue to *look* real, not 3 items but only the 5 hero cases must be perfect | 15–20 JSON records validate against schema |
| 1.2 | Turn 5–6 records into PDF/image files styled like scanned jail registers, a couple with deliberately missing fields | Makes ingestion a real demoable step, not a claim | Files exist in `data/synthetic_cases/` |
| 1.3 | Collect actual public-domain text of BNSS Section 479 and the offense-wise sentencing provisions for your ~5 offense types, plus 2–3 real/paraphrased precedent summaries | RAG needs something real to retrieve don't fabricate statute text | Source files in `data/statutes/` |
| 1.4 | Build the ingestion pipeline: raw PDF/image → parse/OCR → clean/structure → JSON matching your schema | This *is* the "completeness of design" evidence for your data layer | Running it on a sample file produces correct structured JSON |
| 1.5 | Chunk + embed the statute corpus into Chroma | Powers the Retrieval Agent | `build_index.py` runs once, index is queryable |
| 1.6 | Manually sanity-test retrieval: 5 test queries, confirm the right clause comes back **before** building agents on top of it | Debugging bad retrieval is much harder once agents wrap it | 5/5 correct |

---

## 9. Phase 2 Core Agent Logic (Hour 9–22)
**Owner: Sathwik G (orchestration) + N B Tanisha (LLM/RAG agents)**
*(Rubric tags: Completeness of Design, Uniqueness, Ethical Considerations this phase carries the most weight of any single phase)*

Build and standalone-test each agent before wiring it in. **Test discipline:** every agent gets a 2-minute script that feeds it one hero case and prints the output, run and confirmed correct *before* it's added to the orchestrator this is what saves you from an Hour-25 debugging spiral where you can't tell which of 8 agents broke.

| # | Agent | Type | Input → Output | Design rationale |
|---|---|---|---|---|
| 2.1 | Eligibility Agent | Deterministic Python, no LLM | case → `eligible: bool`, `days_overdue: int` | Legal-threshold math must be exact lead with this as your rigor/ethics point |
| 2.2 | Records Completeness Agent | Rule-based diff + optional LLM phrasing | case → missing docs list + human-readable message | Deterministic core; LLM only phrases the sentence a human reads |
| 2.3 | Prioritization Agent | Rule-based weighted score | all cases → sorted queue | `score = days_overdue + urgency_weights(age>60, health_flag, low_offense_severity)` explainable, no black box |
| 2.4 | Notification Agent | Simulated | eligible case → logged alert (console/log/mock inbox) | Explicitly simulated; architecture supports a real gateway later |
| 2.5 | Retrieval Agent (RAG) | Real LLM + vector store call | offense section → top-k statute/precedent chunks | The actual grounding step no hallucinated law |
| 2.6 | Drafting Agent | Real generation via `llm_client.generate()` | case + retrieved chunks → draft bail application | Your best demo "wow" moment show the real generated document |
| 2.7 | Multilingual Explainer Agent | Real generation | case + eligibility → plain-language explanation, 1–2 Indian languages (confirm current language support in whichever model you land on) | Humanizes the pitch the direct-beneficiary side |
| 2.8 | Status Tracking Agent | Simulated state machine | filed case → advances `filed → hearing_scheduled → order_passed → released`, on a timer or a manual "simulate next event" button; loops to Notification Agent if stalled | No public API exists name this explicitly as your defined production integration point |
| 2.9 | Orchestrator | Sequential pipeline (BeeAI, or a hand-rolled Python state machine if faster given your Section 3 choice) | chains 2.1–2.8, with a **mandatory human-approval gate** between Drafting output and "filed" state | This is what makes it a pipeline, not 8 disconnected scripts |

---

## 10. Phase 3 Interfaces (Hour 18–30, parallel with tail of Phase 2)
**Owner: Nishanth Prakash Reddy, backend hooks from Sathwik G**
*(Rubric tags: Completeness of Design, Presentation)*

| Step | What | Why | Done when |
|---|---|---|---|
| 3.1 | FastAPI endpoints: `GET /cases`, `GET /cases/{id}`, `POST /cases/{id}/approve`, `GET /cases/{id}/status` | The backend↔frontend contract | Verified via Swagger/`curl` before frontend touches them |
| 3.2 | Lawyer Dashboard: prioritized queue, case detail with an "Approve & File" button, side-by-side raw record vs. structured extraction | Primary judge-facing screen; visually proves the ingestion step worked | A judge can click through a full case end-to-end |
| 3.3 | Family/prisoner-facing view: multilingual plain-language explanation, mobile-width | Distinct, humanizing demo beat | One clean, phone-sized screen |
| 3.4 | **Agent activity log panel** live feed of each agent firing with timestamps as a case runs | Visually *proves* "agentic," not just claims it | Feed updates as a demo case runs |

---

## 11. Phase 4 Integration & Hardening (Hour 30–33)
**Owner: whole team**
*(Rubric tags: Completeness of Design)*

| Step | What | Why |
|---|---|---|
| 4.1 | Run all 5 hero cases end-to-end, confirm each hits its intended branch | Catches integration bugs before they're unfixable |
| 4.2 | Confirm `llm_client.py` fallback actually triggers on a forced failure (kill wifi, test it) | A demo should never visibly break |
| 4.3 | Pre-compute/cache outputs for your exact demo-day cases, while keeping the live pipeline working for a judge who wants to try their own input | Insurance against live network flakiness |
| 4.4 | Basic error/empty states in the UI | Cheap to fix, costly to skip |

---

## 12. Phase 5 Polish & Final Demo Prep (Hour 33–36)
*(Rubric tags: Presentation)*

| Step | What | Why |
|---|---|---|
| 5.1 | Visual polish pass matching your deck's palette | Reads as intentional, not rushed |
| 5.2 | Update the architecture diagram to match what you actually built | Judges cross-check diagram against live demo |
| 5.3 | Rehearse the live demo against your existing 3-minute video script map each beat to an on-screen click | Don't let that prep go unused |
| 5.4 | Write the README: setup, architecture, and an explicit **"what's live vs. simulated"** section | Transparency is a strength here, not a weakness |
| 5.5 | Final repo cleanup: remove secrets, add a license, tag a release | Basic hygiene judges do check |

---

## 13. Mid-Hackathon Checkpoints

**Hour 18 gut-check (whole team, 10 min):** Are all 8 agents individually tested and passing their smoke test? If not, cut Phase 3 scope now (Streamlit fallback, skip the family view) rather than discovering the shortfall at Hour 30.

**Hour 30 gut-check (whole team, 10 min):** Does the full pipeline run end-to-end on all 5 hero cases without manual intervention? If not, this is your last safe point to fall back to pre-computed/cached outputs for the demo rather than a live run.

Rest/rotation note: with 4 people over 36 hours, don't all stay up the full stretch. Rotate 2 people take a 3–4 hour break during Hour 20–28 (the most error-prone stretch) while the other 2 hold lower-cognitive tasks. A team that's alert at Hour 36 beats a team that built 10% more but is incoherent on stage.

---

## 14. Data Schemas & Prompt Templates

### Synthetic case record schema
```json
{
  "case_id": "UTP-0007",
  "name": "synthetic - not a real person",
  "offense_sections": ["IPC 379"],
  "arrest_date": "2024-11-02",
  "custody_days": 410,
  "max_sentence_days_for_offense": 730,
  "prior_bail_orders": [],
  "required_docs": ["remand_order", "charge_sheet", "prior_bail_order_if_any"],
  "present_docs": ["remand_order", "charge_sheet"],
  "urgency_flags": {"age": 63, "health_flag": true, "repeat_offender": false},
  "jail_location": "District Jail, synthetic",
  "preferred_language": "hi"
}
```

### Drafting Agent prompt template
```
System: You are drafting a bail application for a legal-aid lawyer's review.
Use ONLY the retrieved statute/precedent text provided do not add legal
claims not present in it. Flag clearly if a required fact is missing rather
than inferring it.

Case facts: {structured_case_json}
Retrieved statute/precedent: {top_k_chunks}

Task: Draft a bail application in [required legal format], citing the
specific retrieved section.
```

### Multilingual Explainer prompt template
```
System: Explain the following legal status in simple, non-legal
{target_language}, suitable for reading aloud to a family member with no
legal background. No jargon. Under 150 words.

Facts: {eligibility_result}, {days_overdue}, {next_step}
```

Keep every prompt in a single `prompts.py` (or `.txt` files), never hardcoded inline lets you tune wording under time pressure without touching agent logic.

---

## 15. Judging-Day Checklist

**For Eval Round 1:** see `Eval_Round_1_Playbook.md` in full.

**For Final Judging:**
- [ ] Laptop fully charged + backup device
- [ ] Full demo tested **offline** (wifi off, local-fallback-only path) at least once
- [ ] GitHub repo link ready, README complete with the "live vs. simulated" section
- [ ] Video uploaded, link accessible
- [ ] All 4 members can give the 1-line elevator pitch unprompted
- [ ] Rehearsed answers ready for: "why not an off-the-shelf legal chatbot," "what if OCR misreads a document," "what stops the AI from wrongly flagging eligibility," "what's mocked vs. real"

---

## 16. Risk Register

| Risk | Mitigation |
|---|---|
| Chosen LLM provider quota/wifi fails mid-build or mid-demo | `llm_client.py` fallback pattern (Section 3), tested explicitly in Phase 4.2 |
| Ingestion pipeline misreads a synthetic scan | Use clean, well-formatted files for your 5 hero cases; keep messier ones for a "flagged for manual review" talking point rather than a live demo |
| Frontend behind schedule by Hour 28 | Fall back to Streamlit a working ugly UI beats a broken beautiful one |
| A judge challenges legal accuracy | You're only grounded in the one statute you've indexed via RAG be ready to show exactly which section and the citation live |
| Team fatigue by Hour 30+ | Rotation plan in Section 13 |

---

## 17. Stretch Goals (only if ahead of schedule)

- **Celonis tie-in:** feed the Status Tracking Agent's lifecycle events (detected → prioritized → filed → hearing → released, with timestamps) into a simple process-mining-style visualization a strong visual if a Celonis-aligned prize track exists. Confirm with a mentor before committing time to it.
- A second Indian language for the Explainer Agent.
- A closing analytics view: "X undertrials flagged, Y days average overdue, Z% missing at least one document."

---

**Read the Eval Round 1 Playbook first. Then start Phase 0. Go.**
