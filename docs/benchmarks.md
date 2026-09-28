# Benchmarks

Eval set: `evals/labeled_messages.jsonl` (AI-generated messages, gold labels reviewed by hand).

| N | Category accuracy | Macro-F1 | Priority MAE | Invalid/failed | Cost / 1,000 | p50 latency | p95 latency | Notes |
|---|---|---|---|---|---|---|---|---|

| 60 | 96.7% | 0.878 | 0.47 | 0.0% | $2.26 | 1.99s | 2.67s | haiku, prompt v1 baseline |
