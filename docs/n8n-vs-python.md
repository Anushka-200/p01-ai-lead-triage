# n8n vs Python: the same pipeline built twice

Both versions do the same job: a signed contact-form webhook, dedupe, Claude Haiku extraction with the
same prompt (v4), refund/complaint held, Google Sheets row, Slack alert for priority ≥ 4, and a
dead-letter record when something fails. The Python version is in `app/`; the n8n version is in `n8n/`.

## At a glance

| | Python (FastAPI) | n8n 2.41 (self-hosted) |
|---|---|---|
| **Size** | ~1,100 lines of app code + ~960 lines of tests | 15 + 3 nodes, 4 Code nodes (~106 lines of JS, mostly the prompt) |
| **Build effort** | ~6 h of my time over 3 days, but Claude wrote the code | ~2.75 h, **built by hand** by me, including learning n8n |
| **Signature check** | `signing.py`, HMAC + 5-min timestamp | Code node, same HMAC + timestamp (n8n's built-in Header Auth has no replay protection) |
| **Dedupe** | Postgres UNIQUE fingerprint + status: **skip if done, resume if unfinished** | Remove Duplicates node: **skip if ever seen** (see gap 1) |
| **Concurrent duplicates** | Per-message claim lock; proven with 10 parallel connections | No lock. The rapid duplicate in our batch was dropped, but one run doesn't prove it's race-safe |
| **Bad AI output** | Repair-then-retry (tells the model what was wrong), then DLQ | Run fails straight to the error workflow; no repair step |
| **Model routing** | Haiku → Sonnet when confidence < 0.7 | Haiku only |
| **Retries** | Exponential backoff + jitter, **only for temporary errors** (429/5xx/timeouts) | Retry On Fail: fixed 2 s wait, 3 tries, **retries everything**, including permanent errors like 401/404 |
| **Dead-letter queue** | `dlq` table (permanent), `dlq_cli replay` resumes without re-calling the AI | `n8n_dlq` Sheet tab + Slack warning; **Retry** from the Executions list |
| **Human approval** | Streamlit dashboard: approve → delivers, reject → nothing sent | Row marked `waiting_approval`; no approve button (see gap 3) |
| **Debugging** | Langfuse traces, JSON logs, database state | **Executions list: every run, every node's input and output, visually.** Kept 14 days by default |
| **Tests / evals** | 136 automated tests, CI on every push, 60-message eval (96.7%) | Manual test runs only; no unit tests, no CI, eval not wired up |
| **Who can change it** | A developer | Anyone who can use the canvas (e.g. change the Slack wording) |
| **Version control** | Normal code diffs and review | Exported JSON; diffs are hard to read |
| **Running cost** | Claude ~$2.63 / 1,000 messages + a small server | Same Claude cost + n8n host (self-hosted free; n8n Cloud is a paid plan) |

## Gaps found in the n8n version (all honest, all fixable)
1. **"Seen" is not "done".** Remove Duplicates remembers a fingerprint as soon as the node runs, even if
   Claude or Sheets fails later. A customer who resends after a failure is dropped as a duplicate. The
   Python version had the same bug on day 1 and fixed it with skip-vs-resume by status.
2. **Retrying permanent errors wastes time.** Retry On Fail can't tell a 503 (worth retrying) from a
   401 (never going to work); it retries both.
3. **No approval UI.** n8n can do human-in-the-loop with "Send and wait for response" (Slack or email),
   but that needs a Slack app with a bot token, not the incoming webhook we used.
4. **No repair loop or routing.** Both are possible with extra nodes (a loop back to Claude with the
   error; an IF on confidence), but each adds canvas complexity.

## What we saw in a real failure (Sep 29)
Anthropic's authentication started failing for our key mid-test (`503 credential validation failed`,
confirmed in Claude Console itself). In the n8n version, every message that reached Claude got its
`202` first, then failed after 3 retries, and produced an `n8n_dlq` row and a Slack warning. **Nothing
was lost silently.** Replay result: _to be added after the key recovers._

## Could the n8n version close its gaps?
Mostly yes. We left the database out on purpose, to compare a *typical* n8n build rather than Python
rebuilt in boxes.

| Gap | How n8n could add it | Verdict |
|---|---|---|
| Crash-safe dedupe + lock | Postgres nodes running the same SQL as `db.py` (skip-if-done, `locked_until` claim) | Works, but the logic becomes SQL inside boxes |
| Cost tracking | Code node turns Claude's token counts into $ and writes a column | Easy |
| Smart retries | Error output → IF on status code → Wait with growing delay → loop | Possible, messy canvas |
| Repair loop / routing | Loop back to Claude with the error / IF on confidence → Sonnet | Possible, messy canvas |
| Evals | n8n's Evaluations feature, or `run_eval.py` pointed at an "eval mode" webhook | Doable |
| Human approval | "Send and wait for response" (Slack app with bot token, or email); Wait node; Form node | **Good fit.** We didn't use it because an incoming webhook can't receive button clicks |
| Dashboard | Not n8n's job: it writes data, and Looker Studio / Metabase / Retool / Streamlit displays it | Pair with a dashboard tool |
| Unit tests + CI | Pinned data replays saved inputs, but there's nothing like 136 automated tests on every push | **The real gap** |

Every addition turns a simple visual box into hidden code or SQL. Past a point, you've rebuilt the
Python app inside n8n, without tests and with hard-to-review diffs.

## Scaling
Scale alone doesn't rule n8n out: **queue mode** (Redis + several workers) plus **Postgres** for dedupe
handles high volume of simple flows. Without a lock, though, Remove Duplicates races get *more* likely as
concurrency grows. For both versions, the first bottlenecks are external: Google Sheets write quotas,
Slack webhook rate limits (~1 message/second), and the Anthropic rate-limit tier. Neither version has
been load-tested yet.

## When to use Python, not n8n (hard stops)
1. **Actions with real consequences** (money, refunds, customer emails at scale, record changes) that need
   exactly-once behaviour, crash-safe resume and locks, **proven by tests**.
2. **Tests, CI and code review are required**: regulated industries, audits, security compliance.
3. **Complex agents**: several agents, long-running tasks with memory, dynamic planning, many tools with
   fine-grained permissions. n8n's AI Agent node suits simple agents.
4. **Heavy AI engineering**: custom RAG, fine-tuned or local models, measured routing, repair loops,
   eval gates before deploy.
5. **Part of the client's own product**: a SaaS feature, customer-facing API, white-label.
6. **Reselling or hosting it for their customers**: n8n's Sustainable Use License limits offering n8n as
   a service to others. Check the licence first.
7. **Very low latency or very high throughput per request**: n8n adds per-run overhead, including saving
   each execution.
8. **Unusual technical work**: real-time streaming and voice, binary protocols, heavy data processing,
   large files, CPU-heavy steps. n8n runs as "item in → nodes in sequence → one reply out", in a sandbox
   with time and memory limits, saving every node's data. It can't hold a live two-way connection open
   (a phone call), and it isn't built to compute. Build these as a service; let n8n call it or react to it.
9. **The client's engineers will own it** and don't want another platform to run, secure and upgrade.
10. **Strict data rules** where an extra platform is itself a compliance concern.

**Where n8n still wins at scale:** high volume of simple connector work (sync apps, route leads, send
reports), especially when the client's team wants to adjust it themselves.

## Which to choose when

**Choose n8n when**
- The job is mostly **connecting services** (form → AI → Sheet → Slack) with little custom logic.
- The **client wants to change it themselves** (wording, a new step, a different channel).
- You need a **working prototype in hours**, or the tool has a ready-made n8n node you'd otherwise build.
- Volume is moderate and "retry, then alert a human" is good enough.

**Choose Python (custom code) when**
- **Correctness under stress matters:** exactly-once alerts, crash-safe resume, parallel duplicates.
- The AI part is **non-trivial**: repair loops, routing, RAG, agents, evals you must prove with numbers.
- You need **tests, CI, and code review**, or the client wants to own real code.
- High volume, or you're optimizing cost and latency per message.

**Often the best answer is both:** n8n handles triggers and connectors (the parts clients like to see
and edit), and calls a small Python service over HTTP for the AI "brain" (the part that needs tests,
evals and careful failure handling).

> **One-line rule:** if the hard part is *connecting things*, use n8n. If the hard part is *being
> correct, being intelligent, or being part of the product*, use Python. If it's both, n8n for the
> connections and a Python service for the hard part.
