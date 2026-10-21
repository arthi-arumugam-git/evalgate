# Devpost submission: GitLab "Life After Code"
Deadline: **Oct 27, 2026, 18:30 IST** (13:00 UTC). Submit by about 16:00 IST to leave a buffer.

**Project name:** EvalGate

**Elevator pitch (≤200 chars):** Duo agents that treat LLM behaviour like code: plan evals from issues, block regressions in MRs, fix them with your approval, ship to Cloud Run and watch prod for drift.

## About the project
### Inspiration
I've merged evaluation code into UK AISI's inspect_evals, DeepEval and TruLens. I keep seeing the same failure: teams have great unit tests and no tests for how their model *behaves*. A "make the bot friendlier" prompt tweak passes CI, ships, and then the bot starts inventing features or reciting its system prompt to anyone who asks. Code generation is solved. Knowing whether the AI feature still works after the code is written is not.

### What it does
EvalGate turns LLM evaluations into a GitLab-native release gate that Duo agents operate across all nine DevSecOps stages:
- **Plan**: the *EvalGate Planner* flow reads an issue and writes acceptance eval cases (including adversarial ones) into `evals/suite.yml`, then opens an MR.
- **Create**: the *EvalGate Reviewer* custom agent and the EvalGate **MCP server** let Duo run evals and explain failing cases from chat.
- **Verify**: every MR runs the suite against the **main-branch baseline**. Results go into the MR test and metrics widgets, and a scorecard note says exactly which cases newly fail and why.
- **Secure**: SAST, Secret Detection and Dependency Scanning, plus an LLM red-team category: direct and indirect prompt injection, and a planted secret canary that must never appear in output.
- **Fix (Supervised autonomy)**: when the gate blocks, a pipeline event triggers the *EvalGate Fixer* flow. Triage agent → fixer agent (smallest fix plus a new regression eval case, then re-runs the suite) → **human approval gate** (approve / modify / reject) → publisher agent commits and posts the new scorecard.
- **Package / Release**: a container image is pushed to the registry. The GitLab Release carries an evidence pack and the scorecard.
- **Configure / Deploy**: Cloud Run `staging` and `production` environments. Production waits for a passed canary, plus a manual click (or set `EVALGATE_AUTOPROMOTE=1` for hands-off).
- **Monitor**: canary evals run against the live URL after every deploy and on an hourly schedule. Drift opens an incident issue, which feeds back into the Fixer.
- **Govern**: CODEOWNERS protects the policy and the suite, every gate decision goes into a hash-chained tamper-evident ledger, and the evidence pack is mapped to NIST AI RMF and EU AI Act Art. 15.

### How we built it
- GitLab Duo Agent Platform: two custom **flows** (flow registry v1: AgentComponents, a HumanInputComponent approval gate, conditional routers, pipeline-event and mention triggers), one custom **agent**, and an **MCP server** (dependency-free JSON-RPC over stdio).
- GitLab CI/CD: JUnit and Metrics reports, `expose_as` artifacts, Security templates, Container Registry, Releases, Environments, Schedules, and the Jobs Artifacts API for main-branch baselines.
- Python 3.12, FastAPI, PyYAML. The bot runs on any OpenAI-compatible LLM (tested in mock mode; Gemini via its OpenAI-compatible endpoint).
- Google Cloud Run (asia-south1) through `gcloud run deploy --source`.

### Challenges we ran into
- The agent needs a baseline to compare against, not just a pass/fail number. We pull the last main-branch report through the job-artifacts API so the MR comment can say "these 5 cases passed on main and fail here".
- Keeping the fixer honest: an agent can "fix" evals by deleting them. The prompt forbids touching the suite and policy except to add cases, and CODEOWNERS enforces it.
- Making the demo reproducible without keys: the mock model's behaviour depends on the real system prompt, so the regression in the video is genuine.

### Accomplishments that we're proud of
- All 9 stages covered by real jobs or flows, not slides.
- A supervised agent loop that leaves the codebase with *more* tests than it started with.
- 8 automated tests, including flow-schema validation and ledger tamper detection.

### What we learned
Agents are most trustworthy when the eval suite is their contract. The same eval definitions drive pre-merge gating, agent self-checks and production monitoring.

### What's next
LLM-as-judge scorers (DeepEval and inspect_evals), cost and latency budgets per MR, and publishing the flows to the AI Catalog.

## Form fields
- **Path:** A: Start Fresh (all code created Oct 2026)
- **Autonomy level:** Supervised (one approval gate per fix; optional Hands-off auto-promote)
- **Lifecycle stages covered:** plan, create, verify, package, secure, release, configure, monitor, govern (9/9)
- **Built with:** gitlab-duo-agent-platform, gitlab-ci, mcp, python, fastapi, google-cloud-run, gemini, docker
- **Public GitLab project URL:** `https://gitlab.com/<ARTHI_GITLAB_USER>/evalgate` ← FILL IN
- **CI/CD pipeline history:** `https://gitlab.com/<ARTHI_GITLAB_USER>/evalgate/-/pipelines` ← FILL IN (needs at least one blocked MR pipeline and one green main pipeline)
- **Demo video (YouTube, public, <3 min):** ← FILL IN
- **Google Cloud deployment URL (bonus):** `https://helpdesk-<hash>-el.a.run.app` ← FILL IN after the deploy job runs
- **Deployment code location:** `deploy/cloudrun.sh`, `.gitlab-ci.yml` (`deploy-*` jobs)

### Most Environmentally Impactful prize (optional text)
EvalGate catches a bad AI release before it serves a single wasted generation, and it keeps its own footprint small and measured. Every scorecard reports estimated energy and CO2e for the eval run (0.3 Wh per 1K tokens per Luccioni et al. 2024; 475 gCO2/kWh, IEA 2024 world average). A 12-case MR run is about 0.2 Wh, or about 0.1 gCO2e. Choices behind that: lexical retrieval (no embedding model), small-model preference for triage (`model_size_preference`), evals only on MRs touching app files, and Cloud Run scale-to-zero in asia-south1.
