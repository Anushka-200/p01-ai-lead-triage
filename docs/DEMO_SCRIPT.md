# Demo script (3 minutes)

Recording checklist before you start: `docker compose up -d`, Sheet and Slack cleared of old
test rows, `.env` has real keys, `git log` shows the latest commit.

## 1. Problem (15s)

> "A small consultancy owner reads every contact-form message and email by hand. Buried among
> routine questions and spam are the real leads — worth thousands of dollars — and if she misses
> one, or a broken automation silently drops one, that's lost revenue."

## 2. Architecture (30s)

Show `docs/architecture.png` (or the README's Mermaid diagram rendered on GitHub). Name three
decisions:
> "Three things make this reliable, not just functional. One: the webhook saves the message and
> replies immediately, *before* calling any AI — so a message is safe even if the AI or Google
> is down. Two: every message is fingerprinted, so a duplicate submission never creates two rows
> or two alerts. Three: nothing is lost silently — if a step fails, it lands on a dead-letter
> queue with the exact reason, and I can replay it once the problem's fixed."

## 3. Live demo — happy path + one failure handled (90s)

**Happy path (35s):**
```bash
uv run uvicorn app.api:app --port 8000        # terminal 1
uv run python scripts/send_demo.py            # terminal 2
```
Point out live: the hot lead (Raj, priority 5) gets a Sheet row *and* a Slack alert within ~2
seconds; the duplicate submission is silently skipped (`"action": "resume"` then one row, not
two); the refund/complaint message is held, **not** auto-sent — open the dashboard
(`uv run streamlit run app/dashboard.py`) and show it sitting in the Approvals tab.

**One failure, handled (55s) — verified live, not scripted from memory:**
> "Here's what happens when something breaks. I'll point Slack at a bad URL and restart."
```bash
# temporarily break SLACK_WEBHOOK_URL in .env, restart the server, then send one hot lead
uv run uvicorn app.api:app --port 8000
```
Send Raj's hot-lead message again (from `scripts/send_demo.py` or the webhook directly). Then:
```bash
uv run python -m app.dlq_cli list
```
> "It's on the shelf after just one attempt, not four — a bad URL is a *permanent* problem, so
> retrying it can't help. My retry logic knows the difference: it only retries *temporary*
> failures like a timeout, and fails straight to the queue for anything retrying can't fix, so
> it doesn't waste time. Real transient failures — Slack rate-limited, a network blip — do get
> the full retry-with-backoff treatment first; you can see that split in `app/retry.py`."

Fix the URL back, then:
```bash
uv run python -m app.dlq_cli replay 1
```
> "It resumes exactly where it stopped — the Sheet row was already written before Slack failed,
> so replay only re-sends the missing Slack alert, no duplicate row, and it didn't need to ask
> the AI again, so no extra cost either."

## 4. Results (30s)

Show the final row of `docs/benchmarks.md` on screen:
> "96.7% category accuracy on a 60-message labeled test set, including spam, non-English
> messages, and prompt-injection attempts — all correctly caught, by the way. $2.63 per 1,000
> messages. p95 latency from webhook to Sheet row: 4 seconds, well under my 6-second target.
> And I logged every optimization I tried — including two that *didn't* work as expected, model
> routing and prompt caching — because a client deserves the honest number, not just the best
> one I could cherry-pick."

## 5. Close (10s)

> "Code's on GitHub, link below — including the ADRs behind every decision, 135 automated
> tests, and the full benchmark history. Also built as an n8n workflow for comparison. Happy to
> walk through the reliability details on a call."

---

## n8n side-by-side (30s, once the n8n twin is built)

_To be added after the n8n phase: same flow, drag-and-drop version, 30s comparison of build
time and where each tool's strengths show._
