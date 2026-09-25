# 004: Retries and the dead-letter queue

**Context.** Anthropic, Google and Slack all fail sometimes. Nothing may be lost silently.
**Options.** (a) retry forever, (b) no retries, (c) bounded retries then park the item.
**Decision.** Retry only temporary failures (timeouts, 429, 5xx), max 4 attempts, exponential backoff with full jitter. Permanent failures (bad credentials, invalid output after repair) go straight to the `dlq` table with stage and error. A CLI lists and replays DLQ items.
**Consequences.** No lost messages and no retry storms. Extra table and CLI to maintain. Every DLQ entry is a visible signal on the dashboard.
