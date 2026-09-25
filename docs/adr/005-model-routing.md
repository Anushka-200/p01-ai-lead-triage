# 005: Model routing

**Context.** Most messages are easy; a few are ambiguous. Big models cost much more.
**Options.** (a) always small, (b) always large, (c) small first, escalate when unsure.
**Decision.** Haiku 4.5 first. Escalate to Sonnet 5 if the card's confidence is below a threshold or the repair loop failed. Start threshold at 0.7, then tune it on the eval set.
**Consequences.** Target: at least 40% cheaper than always-large with no drop in macro-F1. Risk: the model's self-reported confidence can be off, so the eval, not a guess, sets the threshold.
