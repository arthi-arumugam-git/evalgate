"""Monitor stage: probe the deployed service with a canary subset of the eval
suite; if quality drifts below policy, open an incident issue (which in turn
triggers the EvalGate Fixer flow)."""
from __future__ import annotations
import httpx
from evalgate import runner, gate
from evalgate.gitlab import GitLab


def probe(base_url: str | None, suite="evals/suite.yml", policy_path="evalgate.policy.yml") -> dict:
    if base_url:
        def fn(q):
            r = httpx.post(base_url.rstrip("/") + "/chat", json={"question": q}, timeout=30)
            r.raise_for_status()
            return r.json()
    else:
        fn = None  # in-process (mock / local)
    run = runner.run(suite, answer_fn=fn)
    verdict = gate.decide(run, gate.load_policy(policy_path))
    incident = None
    if verdict["decision"] == "block":
        body = "Production canary eval failed.\n\n" + "\n".join(f"- `{v['rule']}` need {v['need']} got {v['got']}" for v in verdict["violations"])
        incident = GitLab().issue("[EvalGate] Production quality incident", body, ["incident", "evalgate"])
    return {"run": run, "verdict": verdict, "incident": incident}
