# ESTIMATES: P01 AI Lead & Inbox Triage

PERT = (O + 4M + P) / 6. Ratio = actual / PERT. All concepts New, so x2.0 unless noted.
Estimates for A-C are the user's own (given before seeing Claude's).

| # | Task | Category | Familiarity | O | M | P | PERT | x mult | Planned h | Learning h | Build h | Actual total h | Ratio | Why it was off |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.1 | Concepts reading + quiz (timebox) | learning | New | - | - | - | 1.00 | 1.0 | 1.00 | 0.45 | 0 | 0.45 | 0.45 | Reading is faster than the timebox; quiz answers were mostly right |
| 0.1 | Repo scaffold (done by Claude, user time not logged) | setup | New | .25 | .5 | 1 | 0.54 | 2.0 | 1.08 | - | - | n/a | n/a | Not timed |
| 0.2 | Anthropic + Langfuse accounts and keys | setup | New | .25 | .5 | 1 | 0.54 | 2.0 | 1.08 | 0.2 | 0.45 | 0.65 | 1.20 | Console screens differed slightly from the guide; extra questions on spend limits |
| 1.2b | Review PLAN + ADRs | learning | New | .25 | .4 | .75 | 0.42 | 2.0 | 0.83 | 1.07 | 0 | 1.07 | 2.55 | Many good concept questions (webhook, signature, dedupe); Claude then applied fixes |
| A | LeadCard schema + injection-safe prompt | llm-logic | New | .25 | .5 | .75 | 0.50 | 2.0 | 1.00 | 0.25 | 0.17 | 0.42 | 0.83 | Claude wrote the code; time went on reading and questions about validators and the tag-stripping attack |
| B | Extractor: LiteLLM, forced tool call, repair-retry, Langfuse tracing | llm-logic | New | .25 | .5 | .75 | 0.50 | 2.0 | 1.00 | 0.40 | 0.22 | 0.62 | 1.23 | Claude wrote the code; Langfuse legacy API was disabled (needed v2 to verify traces); time went on line-by-line reading and concept questions |
| C | Unit tests with recorded fixtures | testing-evals | New | .25 | .5 | .75 | 0.50 | 2.0 | 1.00 | 0.05 | 0.10 | 0.15 | 0.30 | Claude wrote and ran the tests; user time was only reading and quiz |
| D | Postgres tables + db.py | data | New | - | 0.33 | - | 0.33 | 2.0 | 0.67 | | | | | logged combined with E, F |
| E | Fingerprint + register_message (skip/resume/new) | data | New | - | 0.33 | - | 0.33 | 2.0 | 0.67 | | | | | logged combined with D, F |
| F | Tests for D and E | testing-evals | New | - | 0.33 | - | 0.33 | 2.0 | 0.67 | | | | | logged combined with D, E |
| D+E+F | Phase 3.1 combined (22:39-23:02) | data | New | - | 1.0 | - | 1.00 | 2.0 | 2.00 | 0.10 | 0.28 | 0.38 | 0.38 | Claude wrote code and tests; user gave single-point estimates (no O/P), 20 min each |
| 3.2 | Google Cloud project, Sheets API, service account, key, test Sheet (Sep 26, 13:22-13:54) | setup | New | 0.25 | 0.5 | 0.75 | 0.50 | 2.0 | 1.00 | 0.15 | 0.38 | 0.53 | 1.07 | Two keys created by mistake; menu path for service accounts differed from the guide; key file left under its download name |
| 3.3 | Slack workspace + incoming webhook (Sep 26, 14:00-14:10) | setup | New | 0.25 | 0.5 | 0.75 | 0.50 | 2.0 | 1.00 | 0.05 | 0.12 | 0.17 | 0.33 | Simple setup, one URL; the webhook concept was the only question |
| 3.4 | Signed webhook: signing.py, api.py, tests, demo sender (Sep 26, 14:39-15:25) | integration | New | .25 | .33 | .42 | 1.00 | 2.0 | 2.00 | 0.35 | 0.42 | 0.77 | 0.77 | Claude wrote code; user time went on concept questions (API types, decorators, HMAC). Estimate read as 15/20/25 min for each of G, H, I |
| 3.5 | save_card, Sheets writer, Slack notifier, idempotent delivery, fake-based tests (Sep 26, 17:19-17:42) | integration | New | .25 | .5 | .75 | 2.00 | 2.0 | 4.00 | 0.12 | 0.26 | 0.38 | 0.19 | Claude wrote all code and tests; user time was reading and quiz. Estimate read as 15/30/45 min for each of J, K, L, M |
| 3.6 | retry.py, pipeline.py worker, DLQ replay CLI, tests (Sep 26, 18:17-18:46) | integration | New | .25 | .33 | .42 | 0.33 | 2.0 | 0.67 | 0.20 | 0.28 | 0.48 | 1.45 | Claude wrote code; user time on reading and concept questions; estimate was 15/20/25 min for N+O+P+Q together (over the 25 min worst case) |
| 3.7 | Wire webhook to worker, live end-to-end run, fix defects found (Sep 26, 18:58-20:36) | integration | New | .25 | .33 | .42 | 0.33 | 2.0 | 0.67 | 0.55 | 1.08 | 1.63 | 4.9 | Live run with real services exposed 3 defects no unit test had: duplicate worker race (needed a claim lock), sender email/name never stored, Sheets append overwriting rows under parallel writes. Also many concept questions (locks, background tasks) |
| 3.8 | Approval logic (decide/approve/reject), approvals_cli, tests; live run found a Sheet dedupe/id-reuse gotcha after truncating (Sep 28, 15:11-16:07) | integration | New | .25 | .33 | .42 | 0.33 | 2.0 | 0.67 | 0.42 | 0.51 | 0.93 | 2.79 | Live run found the id-reuse gotcha: after TRUNCATE the ids restarted, and the Sheet's own dedupe skipped Meera's row |
| 3.9 | Streamlit dashboard: approvals/messages/DLQ tabs, password, wired to decide()/replay() (Sep 28, 16:32-16:51) | integration | New | .25 | .33 | .42 | 0.33 | 2.0 | 0.67 | 0.10 | 0.22 | 0.32 | 0.96 | Missing PYTHONPATH bootstrap for `streamlit run` (different entry point than pytest/uvicorn); fixed by adding sys.path bootstrap in dashboard.py and pytest.ini_options pythonpath |
| — | Explain multi-process vs multi-threaded logging safety (concept only) (Sep 28, 20:50-20:53) | learning | New | .17 | .25 | .33 | 0.25 | 2.0 | 0.50 | 0 | 0.05 | 0.05 | 0.20 | Pure explanation, no code; user asked a clarifying concept question before moving to step 16 |
| 3.10 | Evals: 60 labeled messages, run_eval.py, gold-label fix (Sep 28, 17:12-?) | testing-evals | New | .25 | .33 | .42 | 0.33 | 2.0 | 0.67 | - | - | ≤0.77 | ≤2.3 | End time not recorded; next step began 17:58, so at most 0.77 h. Found 4 wrong gold labels (empty messages) |
| 3.11 | Prompt fix (v2 regression → v3) + Haiku→Sonnet routing + temperature fix (Sep 28, 17:58-18:28) | optimization | New | .25 | .33 | .42 | 0.33 | 2.0 | 0.67 | - | - | 0.50 | 1.50 | Eval caught a regression (priority fix broke category); Claude 5 models reject temperature=0 |
| 3.12 | Prompt trim (v4) + prompt caching (Sep 28, 18:47-18:57) | optimization | New | .17 | .25 | .33 | 0.25 | 2.0 | 0.50 | - | - | 0.17 | 0.67 | Caching inactive below Anthropic's min token threshold - measured quickly, documented in ADR 007 |
| — | Batch API | optimization | - | - | - | - | - | - | - | - | - | 0 | - | Scoped out by user: live triage can't know priority before extraction |
| 3.13 | Structured JSON logs (Sep 28, 20:36-20:46) | infra | New | .17 | .25 | .33 | 0.25 | 2.0 | 0.50 | - | - | 0.17 | 0.67 | Found LiteLLM's own logger polluting the JSON stream; quick fix |
| 3.14 | README + Mermaid diagram + PNG (Sep 28, 20:55-21:02) | docs-video | New | .17 | .25 | .33 | 0.25 | 2.0 | 0.50 | - | - | 0.12 | 0.47 | Local PNG renderer broken (missing Chrome libs); used mermaid.ink instead |
| 3.15 | Dockerfile, Makefile, GitHub Actions CI (Sep 28, 21:10-21:30) | infra | New | .17 | .25 | .33 | 0.25 | 2.0 | 0.50 | - | - | 0.33 | 1.33 | Container re-synced deps on every start (`uv run`); fixed after running it for real |
| 3.16 | Demo script, rehearsed live (Sep 28, 21:30-21:39) | docs-video | New | .08 | .17 | .25 | 0.17 | 2.0 | 0.33 | - | - | 0.15 | 0.90 | Rehearsal found the narration was wrong (404 is permanent, 1 try not 4) and root-owned logs/ |
| — | Unplanned (Sep 28): send_demo PYTHONPATH fix, CI test-isolation bug, full C: drive diagnosis | debugging | - | - | - | - | - | - | - | - | - | not timed | - | No estimate given; environment and test-isolation surprises |
| 4.1 | Demo runs ×2 (self, then friend) (Sep 29) | docs-video | Seen | .25 | .33 | .42 | 0.33 | 1.5 | 0.50 | - | - | not recorded | - | Times not given; unclear whether the estimate was per run or both. Slack app was offline (not a code issue) |
| 5.R-T | n8n twin, hand-built: Docker, Google credential, 15-node workflow, error workflow + DLQ tab (Sep 29, 15:07-16:13 + 18:08-19:40) | integration | New | .5 | 1 | 1.5 | 1.00 | 2.0 | 2.00 | - | - | 2.63 | 2.63 | Estimate was for option A (import); user chose B (hand-build) after estimating. Also: Drive API needed for "From list", $env hidden in editor, n8n 2.x publish step |
| — | Blocked: Anthropic auth outage (`503 credential validation failed`) (Sep 29, from ~19:35) | - | - | - | - | - | - | - | - | - | - | not counted | - | Provider-side; Console itself couldn't authenticate. Replay of 4 failed runs pending |
| 5.U | n8n export + cleanup + comparison doc (Claude, Sep 29) | docs-video | - | - | - | - | - | - | - | - | - | n/a | - | Claude's work; user reviewed |

**Planned total for A-C: 3.0 h (user). Actual A-C: 1.19 h (0.42 + 0.62 + 0.15).**

Caution: 'Actual' is the user's time. Claude wrote the code in A-C, so these ratios understate a solo build. Do not use them as client multipliers yet.

## Claude's view (for comparison)
| Task | O / M / P | PERT | x2.0 |
|---|---|---|---|
| A | .25 / .5 / 1 | 0.54 | 1.1 h |
| B | .5 / 1 / 2 | 1.08 | 2.2 h |
| C | .25 / .5 / 1 | 0.54 | 1.1 h |
| **Total** | | 2.2 | **4.4 h** |

Note: B is the riskiest task (four new things at once). Worst case in the user's B is only 1.5x the likely. Revisit after B.

## Overrun rule
At 150% of a task's planned hours: stop, diagnose (scope / tooling / bigger than expected / wrong direction), then re-scope, re-estimate, cut, or timebox a spike.

## Day 1 summary (Sep 25)
- Steps done: 1.1, 0.1, 0.2, 1.2, 1.3, A, B, C, 3.1 (D+E+F). All committed locally, nothing pushed.
- Planned vs actual (user time): learning 1.45 h vs 1.52 h; setup 2.2 h vs 0.65 h; A-C 3.0 h vs 1.19 h; 3.1 2.0 h vs 0.38 h.
- Lessons: (1) reading-heavy steps run fast, question-heavy steps run slow (1.2b was 2.5x PERT);
  (2) give O/M/P, not one number, so the worst case carries the risk;
  (3) where Claude writes the code, user time understates a solo build. Track solo time separately before quoting.
- Setup risk not yet met: Google Cloud/OAuth and Slack (tomorrow).
- Lesson (3.7): a live run with real services is where the biggest overrun and the most valuable finds happened (ratio 4.9). Budget a separate 'live run + fix' task of about 1 h for any integration step; unit tests alone don't show race conditions or library defaults.

## Day 2 summary (Sep 26)
- Steps: 3.2-3.7 (Google + Slack setup, signed webhook, delivery, retry/DLQ, live wiring).
- Setup ran close to estimate (3.2 ratio 1.07, 3.3 0.33). The live run (3.7) was the big overrun (4.9) and the biggest find.

## Day 3 summary (Sep 28)
- Steps: 3.8-3.16. Estimates for 10-25 min steps landed well (most ratios 0.5-1.5).
- Lessons: (1) evals catch regressions tests can't (v2 prompt); (2) running things for real (Docker, demo) found a bug in almost every step; (3) record the end time before moving on - the evals row is incomplete.

## Day 4 summary (Sep 29)
- Steps: demo prep + 2 demo runs, n8n twin (hand-built), export + comparison doc.
- n8n ratio 2.63: the estimate was made for a different approach. Lesson: re-estimate the moment the approach changes, not after.
- A provider outage blocked testing for part of the day. Lesson for client quotes: third-party outages happen mid-project; name them as a dependency risk in the proposal.
