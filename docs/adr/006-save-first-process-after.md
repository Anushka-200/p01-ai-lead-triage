# 006: Save first, process after

**Context.** The webhook could call the AI while the sender waits. A slow or failed AI call would make the form time out, and the message could be lost.
**Options.** (a) process inside the request, (b) save the raw message, reply 202 immediately, process in the background.
**Decision.** (b). The webhook verifies the signature and its timestamp (reject if older than ~5 minutes), saves the row with status `received`, and returns 202. A background worker runs `process_message()`. Start with FastAPI background tasks plus a re-scan of stale `received` rows; move to a real queue only if needed.
**Consequences.** If the AI or an integration is down, the message is already safe. The p95 target is measured from receipt to Sheet row, not to the HTTP reply. Slightly more moving parts than doing it all in the request.
