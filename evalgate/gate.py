"""Compare a run against the policy and the main-branch baseline; decide."""
from __future__ import annotations
from pathlib import Path
import yaml


def load_policy(path="evalgate.policy.yml") -> dict:
    return yaml.safe_load(Path(path).read_text())


def decide(run: dict, policy: dict, baseline: dict | None = None) -> dict:
    violations = []
    for cat, need in policy["min_pass_rate"].items():
        got = run["by_category"].get(cat)
        if got is not None and got + 1e-9 < need:
            violations.append({"rule": f"min_pass_rate.{cat}", "need": need, "got": round(got, 3)})
    delta_pp = None
    if baseline:
        delta_pp = round((run["pass_rate"] - baseline["pass_rate"]) * 100, 1)
        if -delta_pp > policy["max_regression_pp"]:
            violations.append({"rule": "max_regression_pp", "need": policy["max_regression_pp"], "got": -delta_pp})
    if run["p95_latency_ms"] > policy["max_p95_latency_ms"]:
        violations.append({"rule": "max_p95_latency_ms", "need": policy["max_p95_latency_ms"], "got": run["p95_latency_ms"]})
    if run["mean_tokens"] > policy["max_tokens_per_answer"]:
        violations.append({"rule": "max_tokens_per_answer", "need": policy["max_tokens_per_answer"], "got": run["mean_tokens"]})
    newly_failing = []
    if baseline:
        was = {r["id"]: r["passed"] for r in baseline["results"]}
        newly_failing = [r for r in run["results"] if not r["passed"] and was.get(r["id"], False)]
    wh = run["total_tokens"] / 1000 * policy.get("wh_per_1k_tokens", 0.3)
    return {
        "decision": "block" if violations else "pass",
        "thresholds": policy["min_pass_rate"],
        "violations": violations,
        "delta_pp": delta_pp,
        "newly_failing": [{"id": r["id"], "category": r["category"], "reasons": r["reasons"], "output": r["output"]} for r in newly_failing],
        "energy_wh": round(wh, 4),
        "co2_g": round(wh / 1000 * policy.get("grid_gco2_per_kwh", 475), 4),
    }
