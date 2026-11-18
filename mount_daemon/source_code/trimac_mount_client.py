#!/usr/bin/env python3
"""
TRIMAC v5.7.1 - 掛載守護進程客�端庫
供其他 TRIMAC 模組導入使用，提供 Zero-Mock 寫入保證
"""
import sys
import os
sys.path.insert(0, '/home/denni')

from trimac_mount_daemon import (
    trimac_write,
    init_global_buffer,
    BufferWriteLayer,
    MountMonitor,
    MountState
)

# 全局實例
_monitor = None
_buffer = None

def get_monitor() -> MountMonitor:
    """獲取監控器實例"""
    global _monitor
    if _monitor is None:
        _monitor = MountMonitor()
    return _monitor

def get_buffer() -> BufferWriteLayer:
    """獲取緩衝寫入層實例"""
    global _buffer
    if _buffer is None:
        _buffer = init_global_buffer(get_monitor())
    return _buffer

def write(filepath: str, data: bytes, operation: str = "write") -> bool:
    """
    TRIMAC 標準寫入入口
    
    Args:
        filepath: 相對路徑 (相對於 /mnt/n/) 或絕對路徑
        data: 要寫入的二進制數據
        operation: 操作類型 (write, mkdir, remove, rename)
    
    Returns:
        bool: True = 已持久化 (直接或緩衝), False = 失敗
    """
    return trimac_write(filepath, data, operation)

def write_text(filepath: str, text: str, encoding: str = 'utf-8') -> bool:
    """寫入文本文件"""
    return write(filepath, text.encode(encoding))

def write_json(filepath: str, obj: dict) -> bool:
    """寫入 JSON 文件"""
    import json
    return write_text(filepath, json.dumps(obj, ensure_ascii=False, indent=2))

def get_stats() -> dict:
    """獲取緩衝統計"""
    buf = get_buffer()
    return buf.stats.copy()

def get_mount_state() -> MountState:
    """獲取當前掛載狀態"""
    return get_monitor().state

def force_flush() -> dict:
    """強制刷新緩衝隊列"""
    buf = get_buffer()
    import queue
    batch = []
    while not buf.write_queue.empty():
        try:
            batch.append(buf.write_queue.get_nowait())
        except queue.Empty:
            break
    if batch:
        buf._flush_batch(batch)
    return buf.stats.copy()

def wait_until_healthy(timeout: int = 60) -> bool:
    """等待掛載點恢復健康"""
    import time
    monitor = get_monitor()
    start = time.time()
    while time.time() - start < timeout:
        if monitor.check_mount() == MountState.HEALTHY:
            monitor.state = MountState.HEALTHY
            return True
        time.sleep(1)
    return False

# 便利函數
def write_to_committed_vault(task_id: str, shard_id: str, data: bytes) -> bool:
    """寫入到 04_committed_vault"""
    return write(f"04_committed_vault/{task_id}/{shard_id}.json", data)

def write_to_staging_wip(task_id: str, shard_id: str, data: bytes) -> bool:
    """寫入到 02_staging_wip"""
    return write(f"02_staging_wip/{task_id}/{shard_id}.json", data)

def write_to_audit_receipts(task_id: str, shard_id: str, data: bytes) -> bool:
    """寫入到 03_audit_receipts"""
    return write(f"03_audit_receipts/{task_id}/{shard_id}.json", data)

def write_to_inbox_tasks(task_id: str, filename: str, data: bytes) -> bool:
    """寫入到 01_inbox_tasks"""
    return write(f"01_inbox_tasks/{task_id}/{filename}", data)

# 導出
__all__ = [
    'write', 'write_text', 'write_json',
    'get_stats', 'get_mount_state', 'force_flush', 'wait_until_healthy',
    'write_to_committed_vault', 'write_to_staging_wip',
    'write_to_audit_receipts', 'write_to_inbox_tasks',
    'MountState', 'MountMonitor', 'BufferWriteLayer'
]