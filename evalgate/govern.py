"""Govern stage: tamper-evident audit ledger of every gate decision + an
evidence pack (model card / compliance summary) attached to each release.
Hash-chain design reused from the author's Invoice-to-Payout project."""
from __future__ import annotations
import hashlib, json, os, time
from pathlib import Path

LEDGER = Path(os.getenv("EVALGATE_LEDGER", "out/ledger.jsonl"))


def _h(prev: str, body: str) -> str:
    return hashlib.sha256((prev + body).encode()).hexdigest()


def append(event: str, detail: dict) -> dict:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    prev = "GENESIS"
    if LEDGER.exists() and LEDGER.read_text().strip():
        prev = json.loads(LEDGER.read_text().strip().splitlines()[-1])["hash"]
    body = json.dumps({"ts": time.time(), "event": event, "detail": detail,
                       "sha": os.getenv("CI_COMMIT_SHA", "local"), "actor": os.getenv("GITLAB_USER_LOGIN", "local")}, sort_keys=True)
    rec = {"body": body, "prev": prev, "hash": _h(prev, body)}
    with open(LEDGER, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def verify() -> bool:
    if not LEDGER.exists():
        return True
    prev = "GENESIS"
    for line in LEDGER.read_text().splitlines():
        rec = json.loads(line)
        if rec["prev"] != prev or _h(prev, rec["body"]) != rec["hash"]:
            return False
        prev = rec["hash"]
    return True


def evidence_pack(run: dict, verdict: dict, policy: dict) -> str:
    return f"""# Release evidence pack

- Commit: `{os.getenv('CI_COMMIT_SHA', 'local')}`  Pipeline: {os.getenv('CI_PIPELINE_URL', 'local')}
- Model: {'mock (deterministic)' if run['mock'] else os.getenv('LLM_MODEL', 'unknown')}
- Gate decision: **{verdict['decision']}**; violations: {len(verdict['violations'])}
- Eval cases: {run['n']}; overall pass rate {run['pass_rate']:.1%}
- Category pass rates: {', '.join(f'{k} {v:.0%}' for k, v in sorted(run['by_category'].items()))}
- Security: prompt-injection + secret-canary suite (OWASP LLM01 / LLM07) pass rate {run['by_category'].get('security', 0):.0%}
- Policy thresholds: `{json.dumps(policy['min_pass_rate'])}`, max regression {policy['max_regression_pp']} pp
- Estimated eval energy: {verdict['energy_wh']} Wh (~{verdict['co2_g']} gCO2e)
- Audit ledger intact: {verify()}

Mapped controls: NIST AI RMF MEASURE 2.3 / 2.7 (performance & security testing), MANAGE 4.1 (post-deployment monitoring); EU AI Act Art. 15 (accuracy, robustness, cybersecurity) evidence.
"""
