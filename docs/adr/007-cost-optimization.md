# 007: Cost optimization — what worked and what didn't

**Context.** The brief targets "≥40% cheaper after routing." We tried three levers in order
and measured each with the same 60-message eval, keeping every prior baseline row in
`docs/benchmarks.md` rather than overwriting it.

**What we tried.**
1. **Model routing** (Haiku first, escalate to Sonnet below a confidence threshold). Only
   2-4 of 60 messages (3-7%) were ever ambiguous enough to trigger it — our extraction was
   already good on the easy majority, so there was little headroom for routing to save money.
   Net effect: **more expensive**, not less ($2.26 -> $2.91/1,000), because escalation calls
   cost more than the saving from the few cases it improved.
2. **Prompt trimming** (720 -> 440 system-prompt tokens, same rules, tighter wording). This
   is what actually worked: same accuracy, better priority scoring, **10% cheaper**
   ($2.91 -> $2.63/1,000) on top of routing.
3. **Prompt caching** (`cache_control` on the system prompt and tool schema, both static
   across every call). Implemented correctly, verified with two back-to-back calls, but
   `cache_creation_input_tokens` and `cache_read_input_tokens` were both 0 on every call.
   Anthropic only activates caching above a minimum token threshold, and that minimum is
   larger for cheap/small models like Haiku than for Sonnet/Opus. Our system prompt + tool
   schema together are ~800 tokens - evidently under that threshold, so caching silently
   never activates. Trimming the prompt (lever 2) made this *less* likely to ever help, not
   more, since it shrank us further below the threshold.

**Decision.** Ship prompt v4 (trimmed) with routing left in place (it's occasionally right,
and does no harm at this cost delta). Keep the `cache_control` markers in the code - free
when inactive, and they'll start working automatically if the prompt grows later (e.g. more
few-shot examples, a longer tool schema). Do not claim caching as a cost saving for this
project; do not claim routing hit the "40% cheaper" target - it didn't, and the eval proves it.

**Consequences.** Final numbers vs the v1 baseline: same 96.7% category accuracy, priority
MAE improved 40% (0.47 -> 0.28), company hallucination eliminated (6/60 -> 0/60), cost up 16%
($2.26 -> $2.63/1,000). This is an honest quality-for-cost trade, not the pure cost win the
brief assumed. A real 40%+ cost reduction would need a lever we haven't tried: Batch API for
non-urgent backlog processing (still in the backlog), which trades latency for a documented
Anthropic discount and doesn't fight the same threshold problem caching does.
