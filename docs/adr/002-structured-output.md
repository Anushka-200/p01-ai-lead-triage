# 002: How we get structured output

**Context.** The AI's reply is text. Downstream code needs a typed card.
**Options.** (a) ask for JSON in the prompt, (b) forced tool call with a schema, (c) a wrapper library (instructor).
**Decision.** Forced tool call with the LeadCard schema through LiteLLM, then validate with Pydantic in our code. On a validation error, send the error text back once or twice (repair-then-retry). Still invalid: DLQ.
**Consequences.** Wrong shapes become rare (tool call) and impossible to pass on (Pydantic). No extra library, so the retry loop is plain code I can explain. Cost: a few extra tokens per retry.
