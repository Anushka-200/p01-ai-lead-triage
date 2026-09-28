# Benchmarks

Eval set: `evals/labeled_messages.jsonl` (AI-generated messages, gold labels reviewed by hand).

| N | Category accuracy | Macro-F1 | Priority MAE | Invalid/failed | Cost / 1,000 | p50 latency | p95 latency | Notes |
|---|---|---|---|---|---|---|---|---|

| 60 | 96.7% | 0.878 | 0.47 | 0.0% | $2.26 | 1.99s | 2.67s | haiku, prompt v1 baseline |

| 60 | 90.0% | 0.802 | 0.30 | 0.0% | $2.51 | 2.11s | 2.62s | haiku+routing, prompt v2 (tightened priority rubric + company guard) |

| 60 | 96.6% | 0.875 | 0.31 | 3.3% | $2.72 | 2.14s | 3.46s | prompt v3, no routing |

| 60 | 96.7% | 0.878 | 0.32 | 0.0% | $2.91 | 2.13s | 3.55s | prompt v3, 2/60 routed to escalation |
