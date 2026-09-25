# 003: Dedupe and idempotency

**Context.** Forms get double-submitted and polling can see an email twice. Repeats must not create rows or alerts, and a crash must not lose a lead.
**Options.** (a) check-then-insert in code, (b) unique constraint in Postgres, (c) external cache.
**Decision.** Fingerprint = SHA-256 of normalized sender email + normalized body (lowercased, trimmed, whitespace collapsed), stored in `messages.fingerprint` with a UNIQUE constraint. Insert uses `ON CONFLICT DO NOTHING`. On a repeat, read the existing row's status: skip if `delivered`, `waiting_approval`, `rejected` or `failed`; resume if `received` or `extracted`.
**Consequences.** The database is the single judge, so two simultaneous requests can't both win, and a crash after the insert cannot swallow a lead. Known limit: a slightly edited resend counts as new. Fine for v1.
