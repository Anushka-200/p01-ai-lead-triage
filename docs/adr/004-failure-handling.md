# 004: Retries, idempotent outputs and the dead-letter queue

**Context.** Anthropic, Google and Slack all fail sometimes. Nothing may be lost silently, and a retry must not repeat an effect that already happened.
**Options.** (a) retry forever, (b) no retries, (c) bounded retries then park the item.
**Decision.** Retry only temporary failures (timeouts, 429, 5xx), max 4 attempts, exponential backoff with full jitter. Permanent failures (bad credentials, invalid output after repair) go straight to the `dlq` table with stage and error. A CLI lists and replays DLQ items. Before any outside effect, check whether it already happened: every Sheet row carries the message id and is looked up before writing; `slack_sent` is checked before alerting.
**Consequences.** No lost messages, no retry storms, and duplicates become rare. A crash between sending and setting a flag can still double-send once; accepted for v1. Extra table and CLI to maintain.
