# Learning log

## Step 1.1 — Concepts (Sep 25, 14:18–14:45, 27 min vs 60 planned)
- **Workflow vs agent:** fixed, predictable steps; cheaper; an agent could take actions nobody asked for. P01 is a workflow.
- **Structured output vs JSON mode:** JSON mode = valid JSON, any fields/types. Structured output = we send a form (fields + types) and the AI fills it. Pydantic then re-checks in our own code and turns the text into a typed object.
- **Dedupe:** normalize sender+body, hash it, unique constraint in Postgres rejects repeats.
- **Retries:** backoff = wait grows (1s, 2s, 4s); jitter = small random extra. Don't retry permanent errors (wrong URL, bad password); send them to the DLQ.
- **DLQ:** the "undeliverable" shelf. Failed items wait with the reason; a replay command re-sends them once the problem is fixed.
- **n8n vs Python:** n8n when the client wants to edit things themselves; Python for tests, evals and fine control.
- **Prompt injection:** treat message text as data, never as instructions.
