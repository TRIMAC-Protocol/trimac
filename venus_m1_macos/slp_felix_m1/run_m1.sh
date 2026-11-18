#!/bin/bash
set -e
echo "=== 正在啟動聖語系統 (v1.0 RELEASE - M1 ARM64 適配版) 節點: TRI-VENUS-02 ==="
if [ ! -d ".venv_arm64" ]; then
    python3 -m venv .venv_arm64
fi
source .venv_arm64/bin/activate
pip install --quiet pydantic aiohttp z3-solver
python3 z3_verify.py
export SLP_SIGNING_KEY="${SLP_SIGNING_KEY:-slp-v1-prod-secret-key}"
python3 slp_daemon.py \
    --id "TRI-VENUS-02" \
    --role "作為 TRIMAC 金星號重裝支團長，負責代碼合成、多模態重裝推理與技術實施。" \
    --host "0.0.0.0" \
    --port 19902 \
    --llm-url "https://integrate.api.nvidia.com/v1" \
    --llm-model "nvidia/nemotron-3.5-super-vl-120b-a12b" \
    --db "slp_felix_v1.db"
