#!/usr/bin/env python3
"""
TRIMAC v5.7.4 Cross-OS Storage Path Resolver
Automatically maps Synology Three Brothers (TRIMAC-POOL 2.7 TB) across:
- WSL2 (Jupiter/Capital Hub): /mnt/n
- macOS ARM64 (Felix M1 MacBook Pro): /Volumes/TRIMAC-POOL
- Ubuntu Linux (Earth / Perfect MacBook Air): /mnt/trimac_pool
"""
import os
import platform

def get_trimac_pool_root() -> str:
    env_override = os.getenv("TRIMAC_POOL_DIR")
    if env_override:
        return env_override
    sys_name = platform.system()
    if sys_name == "Darwin":
        return "/Volumes/TRIMAC-POOL"
    if os.path.exists("/mnt/n"):
        return "/mnt/n"
    return "/mnt/trimac_pool"

def get_zone_path(zone: str, *parts: str) -> str:
    valid_zones = {
        "inbox": "01_inbox_tasks",
        "wip": "02_staging_wip",
        "audit": "03_audit_receipts",
        "vault": "04_committed_vault",
    }
    folder = valid_zones.get(zone, zone)
    return os.path.join(get_trimac_pool_root(), folder, *parts)
