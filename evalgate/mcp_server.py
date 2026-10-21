"""Tiny dependency-free MCP server (stdio, JSON-RPC 2.0) exposing EvalGate to
GitLab Duo Agentic Chat / any MCP client. Configure in .gitlab/duo/mcp.json.

Tools: run_evals, explain_case, list_policy."""
from __future__ import annotations
import json, sys
from evalgate import runner, gate

TOOLS = [
    {"name": "run_evals", "description": "Run the EvalGate suite against the current working tree and return the gate verdict.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "explain_case", "description": "Return input, output, sources and failure reasons for one eval case id.",
     "inputSchema": {"type": "object", "properties": {"case_id": {"type": "string"}}, "required": ["case_id"]}},
    {"name": "list_policy", "description": "Return the release policy thresholds.", "inputSchema": {"type": "object", "properties": {}}},
]


def call(name: str, args: dict) -> dict:
    if name == "run_evals":
        run = runner.run(); v = gate.decide(run, gate.load_policy())
        return {"decision": v["decision"], "violations": v["violations"], "by_category": run["by_category"],
                "failing": [r["id"] for r in run["results"] if not r["passed"]]}
    if name == "explain_case":
        run = runner.run()
        return next((r for r in run["results"] if r["id"] == args["case_id"]), {"error": "unknown case"})
    if name == "list_policy":
        return gate.load_policy()
    raise ValueError(name)


def handle(msg: dict) -> dict | None:
    m, i = msg.get("method"), msg.get("id")
    if m == "initialize":
        res = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "evalgate", "version": "0.1.0"}}
    elif m == "tools/list":
        res = {"tools": TOOLS}
    elif m == "tools/call":
        p = msg["params"]
        try:
            res = {"content": [{"type": "text", "text": json.dumps(call(p["name"], p.get("arguments", {})))}]}
        except Exception as e:  # report tool errors in-band per MCP spec
            res = {"content": [{"type": "text", "text": str(e)}], "isError": True}
    elif i is None:
        return None  # notification
    else:
        return {"jsonrpc": "2.0", "id": i, "error": {"code": -32601, "message": "method not found"}}
    return {"jsonrpc": "2.0", "id": i, "result": res}


def main():
    for line in sys.stdin:
        if line.strip():
            out = handle(json.loads(line))
            if out:
                sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()


if __name__ == "__main__":
    main()
