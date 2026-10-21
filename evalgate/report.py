"""Render GitLab-native report artifacts + MR comment + HTML scorecard."""
from __future__ import annotations
import html
from xml.sax.saxutils import escape


def junit(run: dict) -> str:
    fails = sum(not r["passed"] for r in run["results"])
    rows = []
    for r in run["results"]:
        body = "" if r["passed"] else f'<failure message="{escape("; ".join(r["reasons"]))}">{escape(r["output"])}</failure>'
        rows.append(f'<testcase classname="evalgate.{r["category"]}" name="{escape(r["id"])}" time="{r["latency_ms"]/1000:.4f}">{body}</testcase>')
    return f'<?xml version="1.0"?><testsuite name="evalgate" tests="{run["n"]}" failures="{fails}">{"".join(rows)}</testsuite>\n'


def metrics_txt(run: dict, verdict: dict) -> str:
    """GitLab Metrics Reports format (artifacts:reports:metrics)."""
    lines = [f"eval_pass_rate {run['pass_rate']:.3f}", f"eval_p95_latency_ms {run['p95_latency_ms']}",
             f"eval_mean_tokens {run['mean_tokens']:.1f}", f"eval_energy_wh {verdict['energy_wh']}"]
    lines += [f"eval_pass_rate_{k} {v:.3f}" for k, v in sorted(run["by_category"].items())]
    return "\n".join(lines) + "\n"


def mr_comment(run: dict, verdict: dict, baseline: dict | None) -> str:
    icon = "✅" if verdict["decision"] == "pass" else "⛔"
    out = [f"## {icon} EvalGate: **{verdict['decision'].upper()}**", ""]
    out.append("| Category | This MR | main | Policy |")
    out.append("|---|---|---|---|")
    for k, v in sorted(run["by_category"].items()):
        b = baseline["by_category"].get(k) if baseline else None
        out.append(f"| {k} | {v:.0%} | {'' if b is None else f'{b:.0%}'} | ≥{verdict.get('thresholds', {}).get(k, 0):.0%} |")
    if verdict["delta_pp"] is not None:
        out.append(f"\nOverall pass rate {run['pass_rate']:.0%} ({verdict['delta_pp']:+} pp vs main) · p95 {run['p95_latency_ms']} ms · ~{verdict['energy_wh']} Wh / {verdict['co2_g']} gCO2e per eval run")
    if verdict["violations"]:
        out.append("\n**Policy violations**\n")
        out += [f"- `{v['rule']}`: need {v['need']}, got {v['got']}" for v in verdict["violations"]]
    if verdict["newly_failing"]:
        out.append("\n**Newly failing cases** (passed on main)\n")
        for r in verdict["newly_failing"]:
            out.append(f"- `{r['id']}` ({r['category']}): {'; '.join(r['reasons'])} — _\"{r['output'][:110].replace(chr(10), ' ')}…\"_")
        out.append("\n🤖 Mention `@evalgate-fixer` or wait for the **EvalGate Fixer** flow: it will propose a fix MR for your approval.")
    return "\n".join(out) + "\n"


def render_html(data: dict | None) -> str:
    if not data:
        return "<h1>EvalGate</h1><p>No report yet. Run <code>python -m evalgate run</code>.</p>"
    run, verdict = data["run"], data["verdict"]
    color = "#1f9d55" if verdict["decision"] == "pass" else "#d64545"
    rows = "".join(
        f"<tr class={'ok' if r['passed'] else 'bad'}><td>{html.escape(r['id'])}</td><td>{r['category']}</td>"
        f"<td>{'PASS' if r['passed'] else 'FAIL'}</td><td>{html.escape(r['output'][:140])}</td></tr>" for r in run["results"])
    cats = "".join(f"<div class=card><b>{v:.0%}</b><span>{k}</span></div>" for k, v in sorted(run["by_category"].items()))
    return f"""<!doctype html><html><head><meta charset=utf-8><title>EvalGate scorecard</title><style>
body{{font-family:Inter,system-ui,sans-serif;margin:32px;background:#0f1117;color:#e6e6e6}}
.badge{{display:inline-block;padding:6px 14px;border-radius:20px;background:{color};font-weight:700}}
.cards{{display:flex;gap:16px;margin:20px 0}}.card{{background:#1b1e27;padding:16px 22px;border-radius:12px}}
.card b{{display:block;font-size:28px}}.card span{{color:#9aa3b2}}table{{border-collapse:collapse;width:100%}}
td{{padding:8px;border-bottom:1px solid #2a2e3a;font-size:14px}}tr.bad td{{color:#ff8a8a}}tr.ok td:nth-child(3){{color:#6fdc9a}}
</style></head><body><h1>🛡️ EvalGate scorecard <span class=badge>{verdict['decision'].upper()}</span></h1>
<p>{run['n']} cases · overall {run['pass_rate']:.0%} · p95 {run['p95_latency_ms']} ms · {verdict['energy_wh']} Wh · {'mock model' if run['mock'] else 'live model'}</p>
<div class=cards>{cats}</div><table><tr><th>case</th><th>category</th><th>result</th><th>output</th></tr>{rows}</table></body></html>"""
