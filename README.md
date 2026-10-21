# EvalGate: CI/CD for LLM behaviour, run by GitLab Duo agents

**When the code is "done", an LLM app can still break in production. A one-line prompt edit can make your support bot invent features or leak its system prompt, and unit tests won't catch it. EvalGate makes LLM evaluations a first-class GitLab gate. Duo agents plan the evals, block regressions, fix them (with your approval), ship, and watch production.**

Built for **GitLab "Life After Code"**: Path A (Start Fresh), autonomy level **Supervised**, touches **9/9 DevSecOps stages**, and deploys to **Google Cloud Run**.

![architecture](docs/screenshots/architecture.png)

| Stage | What EvalGate does | Where |
|---|---|---|
| **Plan** | *EvalGate Planner* Duo flow turns an issue into acceptance eval cases and opens an MR | `.gitlab/duo/flows/evalgate-planner.yml` |
| **Create** | *EvalGate Reviewer* custom agent + EvalGate **MCP server** (`run_evals`, `explain_case`, `list_policy`); *Fixer* flow writes the fix | `.gitlab/duo/agents/`, `evalgate/mcp_server.py` |
| **Verify** | `evalgate` job runs the suite, diffs it against the **main-branch baseline**, writes JUnit + Metrics reports to the MR widget, posts a scorecard note, sets the `evalgate::block/pass` label | `.gitlab-ci.yml`, `evalgate/` |
| **Secure** | SAST, Secret Detection, Dependency Scanning templates, plus an **LLM red-team** job (prompt injection, indirect injection, planted secret-canary leakage; OWASP LLM01/LLM07) | `llm-redteam` job |
| **Package** | Container image pushed to the GitLab Container Registry, with its own scorecard baked in | `Dockerfile` |
| **Release** | GitLab Release whose description is the **evidence pack** and whose assets link to the scorecard | `release` job |
| **Configure** | Cloud Run `staging` / `production` GitLab Environments (asia-south1) | `deploy/cloudrun.sh` |
| **Monitor** | Post-deploy **canary evals** against the live URL, plus an hourly scheduled probe. Drift opens an `incident` issue, which triggers the Fixer | `evalgate/monitor.py` |
| **Govern** | `CODEOWNERS` on policy/evals, a **hash-chained audit ledger** of every gate decision, and NIST AI RMF / EU AI Act Art. 15 evidence | `evalgate/govern.py` |

## The Duo flow: EvalGate Fixer (Supervised)
A failed MR pipeline (trigger: **Pipeline events**) or an `@mention` runs:
`triage` (reads the MR diff, failing job log and report) → `fixer` (smallest fix + **adds a regression eval case**, re-runs the suite) → `approval_gate` (**HumanInputComponent**: approve / modify / reject) → `publisher` (commits to the MR branch and posts the new scorecard). The fixer is forbidden to weaken the suite or the policy, and CODEOWNERS enforces that too.

![MR comment](docs/screenshots/mr-comment-block.png)

## Quick start (mock mode, no keys, ~1 min)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest -q                       # 8 tests: gate, regression detection, reports, ledger tamper, MCP, flow schema, HTTP
EVALGATE_MOCK=1 bash scripts/demo.sh   # replays the whole demo story locally
uvicorn app.server:app --port 8080     # http://localhost:8080 = live scorecard, POST /chat = the bot
```
Mock mode uses a deterministic stand-in model whose behaviour depends on `app/prompt.txt`, so prompt edits really change the eval results.

## Environment variables (all optional)
| Var | Purpose |
|---|---|
| `EVALGATE_MOCK` | `1` = deterministic offline model and GitLab writes go to `out/gitlab_actions.jsonl` |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | any OpenAI-compatible endpoint (e.g. Gemini `https://generativelanguage.googleapis.com/v1beta/openai`, model `gemini-2.5-flash`) |
| `EVALGATE_GITLAB_TOKEN` | project access token (`api`): posts MR notes, labels and incident issues |
| `EVALGATE_TARGET_URL` | deployed URL for `python -m evalgate monitor` |
| `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SA_KEY` (file var), `STAGING_URL`, `PRODUCTION_URL` | Cloud Run deploy jobs (skipped if unset) |
| `EVALGATE_AUTOPROMOTE=1` | Hands-off mode: production deploys automatically after the canary passes (default is a manual gate) |

## Set up on GitLab (about 15 min)
1. Create a public project and push this repo. MIT license is in `LICENSE`.
2. CI/CD variables: `EVALGATE_GITLAB_TOKEN` (masked), plus the optional GCP vars above.
3. **Automate → Flows → New flow**: paste `.gitlab/duo/flows/evalgate-fixer.yml` and enable it with the triggers **Pipeline events** and **Mention**. Do the same for `evalgate-planner.yml` with **Assign** and **Mention**.
4. **Automate → Agents → New agent**: use the prompt in `.gitlab/duo/agents/eval-reviewer.md`. Add the MCP server from `.gitlab/duo/mcp.json` in Duo Agentic Chat (IDE).
5. CI/CD → Schedules: hourly, which runs `production-canary`.

## Sustainability
Each MR eval run is about 12 short generations. EvalGate reports estimated energy and CO2e in every scorecard. The estimate uses `wh_per_1k_tokens` (0.3 Wh/1K tokens, order of magnitude from Luccioni et al., 2024, *Power Hungry Processing*) and the IEA 2024 world grid average (475 gCO2/kWh). Retrieval is lexical (no embedding model), Cloud Run scales to zero, and evals only re-run on MRs that touch app files. A broken prompt caught before deploy also saves the serving cost of a bad release.

## Limits
- The mock model is a deterministic simulator for demos and tests. Set `LLM_API_KEY` for real-model numbers.
- String-match scoring is deliberately simple and auditable. Swap in an LLM judge (DeepEval / inspect_evals scorers) via `evalgate/runner.py:score_case`.
