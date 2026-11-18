#!/usr/bin/env python3
"""
TRIMAC v5.7.4 - Unified Orchestrator, Dual-Track Failover Auditor & Mount-Daemon Storage Bridge
Integrates:
1. Two AI Chapters (Venus :9902 & NewMoon :9904) with strict anti-bypass governance
2. Primary Auditor Perfect (100.125.85.1:9903) + 3.0s Fail-Fast Failover to Saturn (127.0.0.1:9120) with monotonic Fencing Token
3. Synology Three Brothers (/mnt/n) persistence via trimac_mount_client (Zero-Mock + Local Buffer Auto-Flush)
"""
import os
import sys
import time
import json
import hashlib
import urllib.request
import urllib.error
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "trimac_mount_daemon", "source_code")))
import trimac_mount_client as storage_client

PRIMARY_AUDITOR_URL = os.getenv("PRIMARY_AUDITOR_URL", "http://100.125.85.1:9903/a2a/audit")
BACKUP_AUDITOR_URL = os.getenv("BACKUP_AUDITOR_URL", "http://127.0.0.1:9120/a2a/audit")
FAIL_FAST_TIMEOUT = 3.0

class TrimacV574Coordinator:
    def __init__(self):
        self.fencing_token = 0

    def next_fencing_token(self) -> int:
        self.fencing_token += 1
        return self.fencing_token

    def persist_shard_to_wip(self, task_id: str, node_code: str, payload: Dict[str, Any]) -> str:
        raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        digest = hashlib.sha256(raw_bytes).hexdigest()
        storage_client.write_to_staging_wip(task_id, f"shard_{node_code}", raw_bytes)
        return digest

    def submit_audit_with_failover(self, task_id: str, shard_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        body = json.dumps({
            "task_id": task_id,
            "shard_results": shard_results,
            "timestamp": time.time()
        }, ensure_ascii=False).encode("utf-8")

        # 1. Try Primary Auditor Perfect (100.125.85.1:9903) with strict 3.0s Fail-Fast timeout
        req = urllib.request.Request(PRIMARY_AUDITOR_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=FAIL_FAST_TIMEOUT) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                result["auditor_used"] = "TRI-PERFECT-03"
                result["failover_triggered"] = False
                storage_client.write_to_audit_receipts(task_id, "audit_verdict", json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
                return result
        except Exception as primary_err:
            token = self.next_fencing_token()
            failover_payload = json.dumps({
                "task_id": task_id,
                "shard_results": shard_results,
                "fencing_token": token,
                "acting_for": "TRI-PERFECT-03",
                "failover_reason": str(primary_err),
                "timestamp": time.time()
            }, ensure_ascii=False).encode("utf-8")

            req_backup = urllib.request.Request(BACKUP_AUDITOR_URL, data=failover_payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req_backup, timeout=5.0) as resp_b:
                result = json.loads(resp_b.read().decode("utf-8"))
                result["auditor_used"] = "TRI-SATURN-06"
                result["acting_for"] = "TRI-PERFECT-03"
                result["fencing_token"] = token
                result["failover_triggered"] = True
                storage_client.write_to_audit_receipts(task_id, f"audit_verdict_fencing_{token}", json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
                return result
