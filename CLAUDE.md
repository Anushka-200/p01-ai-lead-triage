# Engineering Standard (shared across all portfolio projects)

> Paste this whole file at the top of each repo's `CLAUDE.md`, then append the project-specific section from the brief.

## Who I am and why this repo exists
I'm an AI engineer building a public portfolio to win freelance work (Upwork) with US clients. Every repo must (1) teach me the concepts in depth, (2) look and behave like production work, and (3) prove impact with numbers. I must be able to defend every design decision on a client call.

## How to work with me
- **Teach while building.** Before writing a new module, explain in 5–10 lines what it does, the main alternatives, and why we're choosing this one. After the module, ask me 3 questions to check I understood.
- **Plan before code.** For any change bigger than ~50 lines, propose the plan first and wait for my OK.
- **Small steps.** One phase at a time, tests passing, then commit with a clear message.
- **No magic.** Prefer plain, readable Python over clever abstractions. Comment the *why*, not the *what*.
- If a requirement is ambiguous, ask me instead of guessing.

## Working style (every project)
1. **Plan first:** a plan broken into small substeps, each with my estimated hours, plus what the same work would take on a client job (the hours to quote).
2. **Explanations: brief, to the point, in plain words.** Start with an everyday analogy, then the technical term. Don't stack jargon.
3. **Before every step you ask me to do:** say in one or two lines *what* it is and *why* we're doing it.
4. **Track each substep:** ask for my start time, log actual vs estimate, and apply the 150% overrun check below.

## Default stack (change only with an ADR explaining why)
- Python 3.12, `uv` for deps, `ruff` + `mypy` (basic), `pytest`
- FastAPI + Pydantic v2 for APIs; Streamlit for internal UIs unless the brief says Next.js
- PostgreSQL (+ pgvector) via Docker Compose; Redis when queues/caching are needed
- LLM calls through **LiteLLM** so models can be swapped/routed; default to a small, cheap model tier; structured outputs via Pydantic
- Tracing with **Langfuse** (cloud free tier or self-hosted)
- Config via env vars (`pydantic-settings`), `.env.example` committed, `.env` never committed

## Non-negotiables in every project
1. **Decision records** — `docs/adr/NNN-title.md` (context, options, decision, consequences). 3–5 per project.
2. **Evaluation first** — a labeled dataset in `evals/` and a script that prints metrics. No optimization claims without before/after numbers.
3. **Reliability** — timeouts, retries with exponential backoff + jitter, idempotency keys where actions repeat, validation of LLM output with repair-then-retry, graceful degradation, clear error messages.
4. **Observability** — every LLM call traced (Langfuse) with model, tokens, cost, latency; structured JSON logs.
5. **Cost & performance** — record baseline cost per unit (per email / per answer / per call / per 1k records) and p50/p95 latency. Try at least 3 optimizations (model routing, caching, batching, prompt trimming, smaller model, parallelism) and log each in `docs/benchmarks.md`.
6. **Security basics** — secrets from env only, input validation, least-privilege DB user, no user-controlled code/SQL execution without guards.
7. **Tests** — unit tests for logic, integration test for the main flow, and a scenario/eval test.
8. **Packaging** — `docker compose up` runs it; `Makefile` with `make setup`, `make test`, `make eval`, `make bench`, `make demo`.
9. **Docs** — README (impact line, demo GIF/video link, Mermaid architecture, benchmark table, quick start, design decisions, limitations), `docs/architecture.mmd`, `docs/DEMO_SCRIPT.md`, `LEARNING_LOG.md`.
10. **CI** — GitHub Actions running lint + tests (+ eval on a small subset if cheap).
11. **Estimation log** — `ESTIMATES.md` (see below). I'm learning to quote client jobs accurately; treat this as seriously as tests.

## Estimation workflow (every project)
Almost every concept here is new to me, so default familiarity is **New (2.0× multiplier)** unless I say otherwise.
- **After PLAN.md is approved, before Phase 2:** create `ESTIMATES.md` with a table: # | Task | Category | Familiarity | O | M | P | PERT | × mult | Planned h | Learning h | Build h | Actual total h | Ratio | Why it was off.
  - Split every phase into tasks of ≤ 4 h. Categories: setup, learning, llm-logic, retrieval, agent, integration, data, ml, infra, testing-evals, optimization, debugging, docs-video.
  - Include hidden work as explicit tasks: setup/access, reading docs, edge-case testing, docs + demo video.
  - Ask ME for O/M/P on each task first (I need the practice); then give your own view and let me adjust. PERT = (O + 4M + P) / 6.
  - Show the total planned hours and flag any task I can't estimate as a timeboxed spike.
- **At the start of each phase:** remind me to note my start time.
- **At the end of each phase:** ask me for the actual learning and build hours per task, fill the columns, compute the ratio, and ask me for the "why it was off" reason in one line.
- **At the end of the project:** add a summary section: planned vs actual total, ratio per category, the 3 biggest estimation lessons, and suggested multipliers for the next project. Keep this short so I can copy it into my cross-project tracker.
- If we're falling behind the plan by more than 30% during a phase, tell me immediately and propose what to cut or simplify (like I would tell a client).

## Estimate-before-you-code habit (every task)
This applies to every coding task, big or small, not only the phases in `ESTIMATES.md`.
- **Before starting:** if I haven't given an estimate, ask for one (hours, plus a one-line "done means…") before writing any code. Record it and the start time in `ESTIMATES.md`.
- **While working:** if elapsed time passes ~150% of my estimate, stop and say so. Don't keep coding. Help me diagnose which it is: unclear scope, tooling/environment issue, task bigger than expected, or Claude going in the wrong direction. Then we choose: re-scope, re-estimate, cut, or ask for help.
- **When finished:** ask for the actual time, compute actual ÷ estimate, and log it with a one-line "why it was off".
```
# <Project name> — <one-line impact with a number>
<demo GIF or screenshot> · ▶ Demo video: <link>
## Problem
## Solution (architecture diagram in Mermaid)
## Results (benchmark table: quality · p95 latency · cost/unit · before → after)
## Key design decisions (links to ADRs)
## Reliability & safety
## Quick start
## What I'd do next
```

## Project: P01 AI Lead & Inbox Triage
Goal: Contact-form webhook + Gmail polling → LLM extracts {name, email, company, intent, category, priority 1-5, reason, confidence} → dedupe → Google Sheet row → Slack alert if priority >= 4 → Streamlit dashboard of last 50 entries (shared-password protected).
Two implementations: (A) n8n workflow (self-hosted, exported JSON committed in /n8n), (B) Python FastAPI service (/app). Same eval set runs against both.
Must survive: API failures (retry + DLQ), invalid JSON from the model (repair then retry, then DLQ), duplicate submissions (idempotency key = hash of normalized sender+body), Slack/Sheets downtime.
Optional human approval: category "refund/complaint" goes to an approval queue instead of auto-actions.
Eval: evals/labeled_messages.jsonl (200 synthetic but realistic messages with gold labels; create with an LLM, then I hand-correct 50).
Optimize: model routing (small model first, escalate to larger when confidence < threshold), prompt trimming, Batch API for backlog mode, caching of the system prompt.
Deploy: Python version to AWS Lambda (via container image or Mangum) with API Gateway; n8n via docker compose.
