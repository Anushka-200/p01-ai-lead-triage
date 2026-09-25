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
