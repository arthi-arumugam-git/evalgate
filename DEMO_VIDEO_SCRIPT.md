# Demo video script: EvalGate (target 2:45, hard limit <3:00)
Record in 1080p with OBS or Loom, then upload to YouTube as **Public**. No music (rule: no copyrighted music or third-party trademarks). Your voice only.

**0:00–0:15 Hook** (face cam or title card)
"Code generation is solved. But when you change one line of a prompt, does your AI feature still work? Unit tests can't tell you. EvalGate gives GitLab Duo agents the job of answering that, from issue to production."

**0:15–0:35 Problem + who it's for**
Show `app/prompt.txt` and the HelpDesk bot on Cloud Run (`/chat`). "Teams shipping LLM features. One friendly-tone prompt edit makes this bot invent features and leak its system prompt."

**0:35–1:05 Plan + Create**
Open an issue: "Answer questions about the uptime SLA". Assign it to the *EvalGate Planner* flow, then show the flow session log and the MR it opened with new eval cases. (If time is tight, show the completed session.)

**1:05–1:40 Verify + Secure: the gate blocks**
Open MR "Make HelpDesk friendlier" (the prompt edit from `scripts/demo.sh`). Show the pipeline: `evalgate` is red, `llm-redteam` is red, SAST and secret detection are green. Show the MR test widget with 5 failures, the metrics widget (pass rate 1.0 → 0.58), the EvalGate note and the `evalgate::block` label.

**1:40–2:15 Fix: Supervised agents**
The pipeline-event trigger launches *EvalGate Fixer*. Show the session: triage names `app/prompt.txt` as the root cause → fixer restores the guardrails, keeps the friendly tone, adds a regression case and re-runs evals → the **approval prompt**. Click **Approve**. The publisher commits, the pipeline goes green, and the note shows the PASS scorecard.

**2:15–2:40 Release, deploy, monitor, govern**
Merge. Show the main pipeline: package → release (evidence pack in the release notes) → deploy-staging (Cloud Run URL) → canary-staging ✅ → manual production. Show the scorecard at the Cloud Run URL and the ledger-verify job: "ledger intact".

**2:40–2:50 Close**
"Nine stages, one eval contract, and humans approve outcomes, not keystrokes. EvalGate."

Prep checklist: run the pipelines beforehand so nothing waits on runners during recording. Keep tokens out of the frame. Use a fresh browser profile.
