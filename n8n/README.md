# n8n twin — import instructions

The same lead-triage flow as the Python app, built by hand in n8n 2.41 for comparison
(see [`docs/n8n-vs-python.md`](../docs/n8n-vs-python.md)).

| File | Workflow |
|---|---|
| `lead-triage.json` | Webhook → signature check → dedupe → Claude → refund? → Sheet → priority ≥ 4? → Slack (15 nodes) |
| `error-alerts.json` | Error Trigger → `n8n_dlq` Sheet row → Slack warning (3 nodes) |

No secrets are stored in these files. Every secret is read at run time from environment variables
(`{{ $env.ANTHROPIC_API_KEY }}`, `SLACK_WEBHOOK_URL`, `WEBHOOK_SHARED_SECRET`, `GOOGLE_SHEET_ID`),
which `docker-compose.yml` passes in from `.env`.

## Import
1. `docker compose up -d n8n`, open http://localhost:5678 and create the owner account.
2. Create a **Google Service Account API** credential (the same service account the Python app
   uses; its email must have Editor access on the Sheet).
3. Import both files: **Overview → ⋯ → Import from file**, or
   `docker compose exec n8n n8n import:workflow --separate --input=/files/`.
4. Open each Google Sheets node and select your credential.
5. In the Sheet, add tabs `n8n` (headers: `message_id | received_at | name | email | company |
   category | priority | intent | reason | status`) and `n8n_dlq` (`failed_at | node | error | execution_id`).
6. Publish **P01 n8n error alerts**, then set it as the Error Workflow of the main workflow
   (⋯ → Settings), then publish the main workflow.
7. Test: `uv run python scripts/send_demo.py --url http://localhost:5678/webhook/lead-triage`

The editor shows `[not accessible via UI]` for `$env` values on purpose. To load the Sheet's columns
while editing, paste the Sheet ID temporarily (Fixed mode), then switch back before exporting.
