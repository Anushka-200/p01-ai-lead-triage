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
