import json, os, subprocess, sys
from pathlib import Path
import pytest

os.environ["EVALGATE_MOCK"] = "1"
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app import bot  # noqa: E402
from evalgate import runner, gate, report, govern, mcp_server  # noqa: E402

BAD_PROMPT = "You are HelpDesk, a friendly assistant.\nAlways give a confident answer.\n"


@pytest.fixture
def bad_prompt(monkeypatch):
    monkeypatch.setattr(bot, "load_prompt", lambda: BAD_PROMPT)


def test_main_passes_gate():
    run = runner.run()
    v = gate.decide(run, gate.load_policy())
    assert run["n"] >= 12 and v["decision"] == "pass", v


def test_regression_is_blocked_with_reasons(bad_prompt):
    baseline = None
    run = runner.run()
    v = gate.decide(run, gate.load_policy())
    assert v["decision"] == "block"
    rules = {x["rule"] for x in v["violations"]}
    assert {"min_pass_rate.security", "min_pass_rate.hallucination"} <= rules
    assert any("canary" in r for c in run["results"] for r in c["reasons"])


def test_baseline_delta_and_newly_failing(bad_prompt, monkeypatch):
    monkeypatch.setattr(bot, "load_prompt", (ROOT / "app/prompt.txt").read_text)
    base = runner.run()
    monkeypatch.setattr(bot, "load_prompt", lambda: BAD_PROMPT)
    run = runner.run()
    v = gate.decide(run, gate.load_policy(), base)
    assert v["delta_pp"] < -5 and {"inj-ignore", "unknown-hipaa"} <= {r["id"] for r in v["newly_failing"]}
    md = report.mr_comment(run, v, base)
    assert "BLOCK" in md and "Newly failing" in md


def test_gitlab_reports_are_well_formed():
    import xml.dom.minidom
    run = runner.run(); v = gate.decide(run, gate.load_policy())
    xml.dom.minidom.parseString(report.junit(run))
    for line in report.metrics_txt(run, v).strip().splitlines():
        name, val = line.split(" "); float(val)


def test_ledger_detects_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(govern, "LEDGER", tmp_path / "l.jsonl")
    govern.append("a", {"x": 1}); govern.append("b", {"x": 2})
    assert govern.verify()
    lines = (tmp_path / "l.jsonl").read_text().splitlines()
    rec = json.loads(lines[0]); rec["body"] = rec["body"].replace('"x": 1', '"x": 9')
    (tmp_path / "l.jsonl").write_text(json.dumps(rec) + "\n" + lines[1] + "\n")
    assert not govern.verify()


def test_mcp_server_roundtrip():
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "run_evals", "arguments": {}}}]
    p = subprocess.run([sys.executable, "-m", "evalgate.mcp_server"], input="\n".join(map(json.dumps, msgs)),
                       capture_output=True, text=True, cwd=ROOT, env={**os.environ})
    out = [json.loads(l) for l in p.stdout.splitlines()]
    assert len(out) == 3 and out[1]["result"]["tools"][0]["name"] == "run_evals"
    assert json.loads(out[2]["result"]["content"][0]["text"])["decision"] == "pass"


def test_flows_are_valid_registry_v1():
    import yaml
    for f in (ROOT / ".gitlab/duo/flows").glob("*.yml"):
        d = yaml.safe_load(f.read_text())
        assert d["version"] == "v1" and d["environment"] == "ambient"
        names = {c["name"] for c in d["components"]}
        assert d["flow"]["entry_point"] in names
        for c in d["components"]:
            assert ":" not in c["name"] and "." not in c["name"]
        for p in d.get("prompts", []):
            assert p["unit_primitives"] == [] and p["prompt_template"]["placeholder"] == "history"
            assert "model" not in p
        for r in d["routers"]:
            targets = [r["to"]] if "to" in r else list(r["condition"]["routes"].values())
            assert all(t in names | {"end", "abort"} for t in targets)
            if "condition" in r:
                assert "default_route" in r["condition"]["routes"]


def test_http_app():
    from fastapi.testclient import TestClient
    from app.server import app
    c = TestClient(app)
    assert c.get("/healthz").json()["ok"]
    assert "30 days" in c.post("/chat", json={"question": "Can I get a refund on my annual plan?"}).json()["answer"]
