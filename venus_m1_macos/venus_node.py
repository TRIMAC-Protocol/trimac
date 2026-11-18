#!/usr/bin/env python3
"""
TRIMAC v5.7.4 - Venus AI Chapter A2A Server (macOS M1 ARM64)
Runs as Captain (Felix :9902, 0.0.0.0) or Worker (Qinglong/Baihu/Zhuque/Xuanwu :9921-9924, 127.0.0.1)
Enforces X-Chapter-Key anti-bypass lock (HTTP 403) and NVIDIA NIM reasoning_content fallback.
"""
import os
import json
import uuid
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List
import httpx
from fastapi import FastAPI, Request, HTTPException
import uvicorn

NODE_ID = os.getenv("TRIMAC_NODE_ID", "felix")
NODE_CODE = os.getenv("TRIMAC_NODE_CODE", "TRI-VENUS-02")
ROLE = os.getenv("TRIMAC_ROLE", "captain")  # captain | worker
BIND_HOST = os.getenv("BIND_HOST", "0.0.0.0" if ROLE == "captain" else "127.0.0.1")
PORT = int(os.getenv("PORT", "9902"))
CHAPTER_SECRET = os.getenv("VENUS_CHAPTER_SECRET", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NIM_BASE_URL = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
MODEL_ID = os.getenv("NIM_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")

WORKERS = [
    {"node_id": "qinglong", "node_code": "TRI-VENUS-02A", "url": "http://127.0.0.1:9921/a2a/task"},
    {"node_id": "baihu", "node_code": "TRI-VENUS-02B", "url": "http://127.0.0.1:9922/a2a/task"},
    {"node_id": "zhuque", "node_code": "TRI-VENUS-02C", "url": "http://127.0.0.1:9923/a2a/task"},
    {"node_id": "xuanwu", "node_code": "TRI-VENUS-02D", "url": "http://127.0.0.1:9924/a2a/task"},
]

app = FastAPI(title=f"TRIMAC Venus Node {NODE_ID}")

def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

@app.get("/health")
async def health():
    return {
        "ack": True,
        "status": "healthy",
        "node_id": NODE_ID,
        "node_code": NODE_CODE,
        "role": ROLE,
        "listen_port": PORT,
        "arch": "arm64-darwin",
        "model": MODEL_ID,
        "pid": os.getpid(),
    }

@app.post("/a2a/broadcast")
async def broadcast(request: Request):
    raw = await request.body()
    payload = json.loads(raw.decode("utf-8")) if raw else {}
    return {
        "ack": True,
        "status": "ok",
        "node_id": NODE_ID,
        "node_code": NODE_CODE,
        "listen_port": PORT,
        "pid": os.getpid(),
        "payload_hash": sha256_hex(raw if raw else b"{}"),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "echo": payload,
    }

async def call_nim(prompt_text: str) -> str:
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY not configured")
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.2,
        "max_tokens": 512,
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(NIM_BASE_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        text = msg.get("content") or msg.get("reasoning_content") or ""
        return text.strip()

@app.post("/a2a/task")
async def handle_task(request: Request):
    raw = await request.body()
    if ROLE == "worker":
        key = request.headers.get("X-Chapter-Key", "")
        if not CHAPTER_SECRET or key != CHAPTER_SECRET:
            raise HTTPException(
                status_code=403,
                detail={"ack": False, "error": "RANK_BYPASS_FORBIDDEN: 嚴禁越級調度，必須經由金星號支團長 Felix (:9902) 派單"}
            )
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        prompt = payload.get("prompt") or payload.get("task") or json.dumps(payload, ensure_ascii=False)
        inference = await call_nim(prompt)
        out_bytes = inference.encode("utf-8")
        return {
            "ack": True,
            "status": "ok",
            "http_status": 200,
            "node_id": NODE_ID,
            "node_code": NODE_CODE,
            "inference": inference,
            "payload_hash": sha256_hex(out_bytes),
            "pid": os.getpid(),
        }

    # Captain orchestration across 4 local workers
    payload = json.loads(raw.decode("utf-8")) if raw else {}
    task_id = payload.get("task_id") or f"venus_{uuid.uuid4().hex[:8]}"
    base_prompt = payload.get("prompt") or payload.get("task") or "Analyze assigned shard."
    shards = payload.get("shards") or [f"[{w['node_id']}] {base_prompt}" for w in WORKERS]

    async def dispatch_worker(idx: int, worker: Dict[str, str]):
        shard_prompt = shards[idx] if idx < len(shards) else base_prompt
        headers = {"X-Chapter-Key": CHAPTER_SECRET, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(worker["url"], headers=headers, json={"task_id": task_id, "prompt": shard_prompt})
            r.raise_for_status()
            return r.json()

    results = await asyncio.gather(*(dispatch_worker(i, w) for i, w in enumerate(WORKERS)))
    return {
        "ack": True,
        "status": "task_completed",
        "task_id": task_id,
        "captain": NODE_CODE,
        "shard_count": len(results),
        "shard_results": results,
    }

if __name__ == "__main__":
    uvicorn.run(app, host=BIND_HOST, port=PORT)
