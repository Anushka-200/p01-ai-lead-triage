"""Run the extractor against evals/labeled_messages.jsonl and print quality/cost/latency.

uv run python -m evals.run_eval
"""

import json
import statistics
import time

from app.extractor import extract_card
from app.schemas import Category

FIELDS = ["name", "email", "company"]


def load(path: str = "evals/labeled_messages.jsonl") -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def norm(v) -> str | None:
    return v.strip().lower() if isinstance(v, str) and v.strip() else None


def macro_f1(gold: list[str], pred: list[str]) -> float:
    """Average, over each category, of how well we did on just that category (F1),
    then averaged across categories. Treats rare categories as equally important as common
    ones - a model that's great at 'spam' but useless at 'refund_complaint' scores lower here
    than plain accuracy would show."""
    scores = []
    for cat in Category:
        c = cat.value
        tp = sum(1 for g, p in zip(gold, pred, strict=True) if g == c and p == c)
        fp = sum(1 for g, p in zip(gold, pred, strict=True) if g != c and p == c)
        fn = sum(1 for g, p in zip(gold, pred, strict=True) if g == c and p != c)
        if tp == 0 and (fp or fn):
            scores.append(0.0)
        elif tp == 0:
            continue  # category absent from both gold and predictions: skip, not a failure
        else:
            precision, recall = tp / (tp + fp), tp / (tp + fn)
            scores.append(2 * precision * recall / (precision + recall))
    return sum(scores) / len(scores) if scores else 0.0


def percentile(values: list[float], p: float) -> float:
    return (
        statistics.quantiles(values, n=100, method="inclusive")[int(p) - 1]
        if len(values) > 1
        else values[0]
    )


def main() -> None:
    items = load()
    gold_cat, pred_cat, priority_errors = [], [], []
    field_correct = dict.fromkeys(FIELDS, 0)
    hallucinations = dict.fromkeys(FIELDS, 0)
    latencies, costs, tokens_total = [], [], 0
    invalid = 0
    rows = []

    for item in items:
        start = time.monotonic()
        try:
            result = extract_card(item["text"])
        except Exception as e:  # noqa: BLE001 - one bad item (ExtractionError, a dropped
            # network call, anything) must not abort the whole run; it's counted and shown below.
            invalid += 1
            rows.append({**item, "error": str(e)})
            continue
        latencies.append(time.monotonic() - start)
        costs.append(result.cost_usd)
        tokens_total += result.tokens_in + result.tokens_out
        card = result.card

        gold_cat.append(item["gold_category"])
        pred_cat.append(card.category.value)
        priority_errors.append(abs(card.priority - item["gold_priority"]))

        for field in FIELDS:
            gold_v, pred_v = norm(item[f"gold_{field}"]), norm(getattr(card, field))
            if gold_v == pred_v:
                field_correct[field] += 1
            elif gold_v is None and pred_v is not None:
                hallucinations[field] += 1

        rows.append(
            {
                "id": item["id"], "kind": item["kind"],
                "gold_category": item["gold_category"], "pred_category": card.category.value,
                "gold_priority": item["gold_priority"], "pred_priority": card.priority,
                "ok": item["gold_category"] == card.category.value and item["gold_priority"] == card.priority,
            }
        )  # fmt: skip

    n = len(items)
    accuracy = (
        sum(g == p for g, p in zip(gold_cat, pred_cat, strict=True)) / len(gold_cat)
        if gold_cat
        else 0
    )
    print(f"Items: {n}   Invalid/failed extractions: {invalid} ({invalid / n:.1%})\n")
    print(f"Category accuracy : {accuracy:.1%}")
    print(f"Category macro-F1 : {macro_f1(gold_cat, pred_cat):.3f}")
    print(f"Priority MAE      : {statistics.mean(priority_errors):.2f}")
    for field in FIELDS:
        print(
            f"{field:8} match : {field_correct[field] / len(gold_cat):.1%}   "
            f"hallucinated: {hallucinations[field]} / {len(gold_cat)}"
        )
    print(
        f"\nCost per message  : ${statistics.mean(costs):.5f}   -> per 1,000: ${statistics.mean(costs) * 1000:.2f}"
    )
    print(f"Tokens per message: {tokens_total / len(costs):.0f}")
    print(
        f"Latency p50 / p95 : {percentile(latencies, 50):.2f}s / {percentile(latencies, 95):.2f}s"
    )

    print("\nMisses (predicted != gold):")
    for r in rows:
        if "error" in r:
            print(f"  #{r['id']:3} [{r['kind']:20}] EXTRACTION FAILED: {r['error'][:60]}")
        elif not r["ok"]:
            print(
                f"  #{r['id']:3} [{r['kind']:20}] gold={r['gold_category']}/{r['gold_priority']}"
                f"  pred={r['pred_category']}/{r['pred_priority']}"
            )

    with open("docs/benchmarks.md", "a") as f:
        f.write(
            f"\n| {n} | {accuracy:.1%} | {macro_f1(gold_cat, pred_cat):.3f} | "
            f"{statistics.mean(priority_errors):.2f} | {invalid / n:.1%} | "
            f"${statistics.mean(costs) * 1000:.2f} | {percentile(latencies, 50):.2f}s | "
            f"{percentile(latencies, 95):.2f}s | haiku, prompt v1 baseline |\n"
        )
    print("\nAppended a row to docs/benchmarks.md")


if __name__ == "__main__":
    main()
