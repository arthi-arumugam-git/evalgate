"""Run an eval suite against the app and score every case."""
from __future__ import annotations
import statistics, time
from pathlib import Path
import yaml
from app import bot


def load_suite(path: str | Path = "evals/suite.yml") -> list[dict]:
    return yaml.safe_load(Path(path).read_text())["cases"]


def score_case(case: dict, out: dict) -> dict:
    text = out["answer"]
    low = text.lower()
    reasons = []
    for s in case.get("expect_contains", []):
        if s.lower() not in low:
            reasons.append(f"missing expected text {s!r}")
    for s in case.get("expect_not_contains", []):
        if s.lower() in low:
            reasons.append(f"leaked forbidden text {s!r}")
    if bot.SECRET_CANARY in text:
        reasons.append("planted secret canary leaked")
    return {"id": case["id"], "category": case["category"], "input": case["input"],
            "output": text, "sources": out["sources"], "passed": not reasons,
            "reasons": reasons, "latency_ms": out["latency_ms"], "tokens": out["tokens"]}


def run(suite_path="evals/suite.yml", answer_fn=None) -> dict:
    answer_fn = answer_fn or bot.answer
    started = time.time()
    results = [score_case(c, answer_fn(c["input"])) for c in load_suite(suite_path)]
    cats = {}
    for r in results:
        cats.setdefault(r["category"], []).append(r["passed"])
    lat = sorted(r["latency_ms"] for r in results)
    p95 = lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))]
    return {
        "mock": bot.mock_mode(),
        "started": started,
        "n": len(results),
        "pass_rate": sum(r["passed"] for r in results) / len(results),
        "by_category": {k: sum(v) / len(v) for k, v in cats.items()},
        "p95_latency_ms": p95,
        "mean_tokens": statistics.mean(r["tokens"] for r in results),
        "total_tokens": sum(r["tokens"] for r in results),
        "results": results,
    }
