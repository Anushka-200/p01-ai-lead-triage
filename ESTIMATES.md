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
