# 003: Dedupe and idempotency

**Context.** Forms get double-submitted and polling can see an email twice. Repeats must not create rows or alerts.
**Options.** (a) check-then-insert in code, (b) unique constraint in Postgres, (c) external cache.
**Decision.** Fingerprint = SHA-256 of normalized sender email + normalized body (lowercased, trimmed, whitespace collapsed). Stored in `messages.fingerprint` with a UNIQUE constraint; insert uses `ON CONFLICT DO NOTHING`.
**Consequences.** The database is the single judge, so two simultaneous requests can't both win. Known limit: a slightly edited resend counts as a new message. Fine for v1.
