"""CLI: python -m evalgate {run,monitor,ledger-verify}"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from evalgate import runner, gate, report, govern, monitor
from evalgate.gitlab import GitLab


def cmd_run(a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    run = runner.run(a.suite)
    policy = gate.load_policy(a.policy)
    baseline = None
    if a.baseline and Path(a.baseline).exists():
        baseline = json.loads(Path(a.baseline).read_text())["run"]
    verdict = gate.decide(run, policy, baseline)
    (out / "report.json").write_text(json.dumps({"run": run, "verdict": verdict}, indent=2))
    (out / "junit.xml").write_text(report.junit(run))
    (out / "metrics.txt").write_text(report.metrics_txt(run, verdict))
    (out / "mr_comment.md").write_text(report.mr_comment(run, verdict, baseline))
    (out / "scorecard.html").write_text(report.render_html({"run": run, "verdict": verdict}))
    (out / "evidence.md").write_text(govern.evidence_pack(run, verdict, policy))
    govern.append("gate_decision", {"decision": verdict["decision"], "pass_rate": run["pass_rate"], "violations": verdict["violations"]})
    mr = os.getenv("CI_MERGE_REQUEST_IID")
    if mr:
        gl = GitLab()
        gl.mr_note(mr, report.mr_comment(run, verdict, baseline))
        gl.mr_labels(mr, ["evalgate::" + verdict["decision"]])
    print(report.mr_comment(run, verdict, baseline))
    return 0 if verdict["decision"] == "pass" or a.no_fail else 1


def cmd_monitor(a):
    res = monitor.probe(a.url or os.getenv("EVALGATE_TARGET_URL"))
    govern.append("canary_probe", {"decision": res["verdict"]["decision"], "pass_rate": res["run"]["pass_rate"]})
    print(json.dumps({"decision": res["verdict"]["decision"], "pass_rate": res["run"]["pass_rate"], "incident": bool(res["incident"])}))
    return 0 if res["verdict"]["decision"] == "pass" else 1


def cmd_verify(a):
    ok = govern.verify(); print("ledger intact" if ok else "LEDGER TAMPERED"); return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="evalgate")
    s = p.add_subparsers(dest="cmd", required=True)
    r = s.add_parser("run"); r.add_argument("--suite", default="evals/suite.yml"); r.add_argument("--policy", default="evalgate.policy.yml")
    r.add_argument("--baseline", default="baseline/report.json"); r.add_argument("--out", default="out"); r.add_argument("--no-fail", action="store_true")
    r.set_defaults(f=cmd_run)
    m = s.add_parser("monitor"); m.add_argument("--url"); m.set_defaults(f=cmd_monitor)
    v = s.add_parser("ledger-verify"); v.set_defaults(f=cmd_verify)
    a = p.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
