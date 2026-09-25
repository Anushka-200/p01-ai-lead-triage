# 001: n8n vs Python

**Context.** Clients ask for both "an n8n workflow" and "custom code". I need to know when each fits.
**Options.** (a) n8n only, (b) Python only, (c) both.
**Decision.** Build Python first as the main version (tests, evals, cost control), then an n8n twin of the same flow.
**Consequences.** More work, but I can compare build time, reliability and cost in `docs/n8n-vs-python.md`. Rule of thumb to test: n8n when the client edits the flow themselves; Python when you need tests, evals and fine control. If time runs short, the n8n twin moves to v2.
