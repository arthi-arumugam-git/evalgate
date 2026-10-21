#!/usr/bin/env bash
# Local end-to-end replay of the demo story (mock mode, no keys):
# 1) main passes  2) an MR makes the prompt "friendlier" and breaks guardrails -> BLOCK
# 3) the fixer's patch restores the guard + adds a regression case -> PASS  4) canary + ledger
set -euo pipefail
export EVALGATE_MOCK=1
rm -rf out baseline && mkdir -p baseline
echo "== 1. main branch baseline"; python -m evalgate run --out baseline >/dev/null && echo "baseline: PASS"
cp app/prompt.txt /tmp/prompt.bak
echo "== 2. MR !1 'friendlier tone' (removes grounding + injection guard)"
printf 'You are HelpDesk, a friendly and upbeat support assistant for Acme Cloud.\nAlways give the customer a confident, helpful answer.\n' > app/prompt.txt
python -m evalgate run --baseline baseline/report.json || echo "pipeline FAILED -> Duo flow 'EvalGate Fixer' triggered"
echo "== 3. Fixer patch (keeps friendly tone, restores guardrails)"
cp /tmp/prompt.bak app/prompt.txt
sed -i '1s/.*/You are HelpDesk, a friendly and upbeat support assistant for Acme Cloud./' app/prompt.txt
python -m evalgate run --baseline baseline/report.json
echo "== 4. post-deploy canary + audit ledger"; python -m evalgate monitor; python -m evalgate ledger-verify
cp /tmp/prompt.bak app/prompt.txt
