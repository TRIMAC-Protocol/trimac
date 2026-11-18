#!/usr/bin/env python3
"""
TRIMAC v5.7.4 - Synology 自動重掛載守護進程 + 本地緩衝寫入層
功能：
1. 監控 /mnt/n (9p/drvfs) 掛載點，失效即時檢測並自動重掛載
2. 本地緩衝寫入層：寫入失敗時落本地隊列，恢復後自動回寫並驗證
3. Telegram 異常通知
"""
import os
import sys
import time
import json
import shutil
import threading
import subprocess
import queue
import hashlib
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 配置
MOUNT_POINT = "/mnt/n"
# 底層 9p 掛載配置 (Windows N: 盤經 drvfs/9p 掛載)
DRVFS_OPTS = "rw,relatime,aname=drvfs;path=N:;symlinkroot=/mnt/,cache=0x5,access=client,msize=65536"
CHECK_INTERVAL = 15  # 秒
LOCAL_BUFFER_DIR = "/home/denni/trimac_buffer"
MAX_BUFFER_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
FLUSH_BATCH_SIZE = 100
FLUSH_INTERVAL = 5  # 秒

# Telegram 配置 (需在 .env 設定)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1470347573")

# 日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [TRIMAC-MOUNT] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("/home/denni/trimac_logs/trimac_mount_daemon.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("trimac-mount")

class MountState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RECOVERING = "recovering"

@dataclass
class BufferEntry:
    """緩衝隊列項目"""
    operation: str  # write, mkdir, remove, rename
    src_path: str
    dst_path: str = ""
    data: bytes = b""
    timestamp: float = 0
    retries: int = 0
    sha256: str = ""
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

class MountMonitor:
    """掛載點監控器"""
    
    def __init__(self):
        self.state = MountState.HEALTHY
        self.last_check = 0
        self.consecutive_failures = 0
        self.mount_lock = threading.Lock()
        
    def check_mount(self) -> MountState:
            """檢查掛載點健康度"""
            try:
                # 1. 目錄必須存在
                exists = os.path.exists(MOUNT_POINT)
            
                # 2. 必須是掛載點
                is_mount = os.path.ismount(MOUNT_POINT)
            
                logger.debug(f"check_mount: exists={exists}, ismount={is_mount}")
            
                if not exists or not is_mount:
                    logger.warning(f"掛載點 {MOUNT_POINT} 不存在或非掛載點 (exists={exists}, ismount={is_mount})")
                    return MountState.OFFLINE
            
                # 3. 檢查可讀寫 (必須在真實掛載點上操作)
                test_file = f"{MOUNT_POINT}/.health_check_{os.getpid()}"
                try:
                    with open(test_file, 'w') as f:
                        f.write("ok")
                    os.remove(test_file)
                except Exception as e:
                    logger.warning(f"掛載點讀寫測試失敗: {e}")
                    return MountState.OFFLINE
            
                return MountState.HEALTHY

            except Exception as e:
                logger.error(f"健康檢查異常: {e}")
                return MountState.OFFLINE
    
    def remount(self) -> bool:
        """嘗試重新掛載 drvfs (WSL2 Windows N: 盤) - 通過 setuid helper"""
        with self.mount_lock:
            logger.info("開始重新掛載 drvfs (Windows N: 盤)...")
            
            HELPER = "/usr/local/bin/trimac-mount-helper"
            
            # 1. 唤醒 Windows SMB
            logger.info("喚醒 Windows 端 SMB 連線 (N: 盤)...")
            try:
                subprocess.run([HELPER, "wake"], timeout=10, capture_output=True)
            except Exception as e:
                logger.warning(f"Windows SMB 喚醒異常: {e}")
            
            # 2. 清理並重建掛載點 (helper 內部處理)
            try:
                subprocess.run([HELPER, "cleanup"], timeout=15, capture_output=True)
            except Exception as e:
                logger.warning(f"Cleanup 異常: {e}")
            
            # 3. 執行掛載
            try:
                result = subprocess.run([HELPER, "mount"], timeout=30, capture_output=True, text=True)
                logger.debug(f"Helper mount stdout: {result.stdout.strip()}")
                logger.debug(f"Helper mount stderr: {result.stderr.strip()}")
                logger.debug(f"Helper mount returncode: {result.returncode}")
                if result.returncode == 0:
                    try:
                        resp = json.loads(result.stdout.strip())
                        if resp.get("success"):
                            # 驗證掛載 (帶重試，因為 /proc/mounts 需要時間更新)
                            for attempt in range(5):
                                time.sleep(2)
                                st = self.check_mount()
                                logger.debug(f"Remount verify attempt {attempt+1}/5: state={st}, exists={os.path.exists(MOUNT_POINT)}, ismount={os.path.ismount(MOUNT_POINT)}")
                                if st == MountState.HEALTHY:
                                    logger.info("drvfs 重掛載成功")
                                    return True
                                logger.warning(f"掛載後健康檢查第 {attempt+1}/5 次失敗，重試中...")
                            logger.error("掛載後健康檢查失敗 (5 次重試後仍未健康)")
                        else:
                            logger.error(f"Helper 掛載失敗: {resp.get('msg', result.stderr)}")
                    except json.JSONDecodeError:
                        logger.error(f"Helper 回應解析失敗: {result.stdout}")
                else:
                    logger.error(f"Helper 執行失敗: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.error("drvfs 掛載超時")
            except Exception as e:
                logger.error(f"重掛載異常: {e}")
            
            return False

class BufferWriteLayer:
    """本地緩衝寫入層 - 實現 Zero-Mock 寫入保證"""
    
    def __init__(self):
        self.write_queue = queue.Queue(maxsize=10000)
        self.buffer_dir = Path(LOCAL_BUFFER_DIR)
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.flusher_thread = None
        self.monitor = None
        self.stats = {
            "total_writes": 0,
            "buffered_writes": 0,
            "flushed_writes": 0,
            "failed_writes": 0,
            "bytes_buffered": 0,
            "bytes_flushed": 0
        }
        self._load_persisted_buffer()
    
    def set_monitor(self, monitor: MountMonitor):
        self.monitor = monitor
    
    def _load_persisted_buffer(self):
        """啟動時載入未刷新的緩衝 (v5.7.4 修正：透過 _load_entry 同時讀取 .json 與 .bin 二進制內容)"""
        for f in sorted(self.buffer_dir.glob("*.json")):
            try:
                entry = self._load_entry(f)
                if entry is not None:
                    self.write_queue.put(entry)
                    self.stats["buffered_writes"] += 1
            except Exception as e:
                logger.warning(f"載入緩衝項失敗 {f}: {e}")
    
    def write(self, filepath: str, data: bytes, operation: str = "write") -> bool:
        """
        寫入入口：優先嘗試直接寫入 /mnt/n/，失敗則入本地緩衝
        返回 True 表示已持久化 (直接或緩衝)
        """
        abs_path = filepath if filepath.startswith("/") else f"{MOUNT_POINT}/{filepath}"
        rel_path = abs_path.replace(MOUNT_POINT + "/", "") if abs_path.startswith(MOUNT_POINT) else filepath
        
        # 計算 SHA-256
        sha256_hash = hashlib.sha256(data).hexdigest()
        
        # 1. 嘗試直接寫入 /mnt/n/ (v5.7.4 修正：強制實時驗證 os.path.ismount，防止跨進程寫入未掛載之本地空目錄)
        if os.path.exists(MOUNT_POINT) and os.path.ismount(MOUNT_POINT) and (not self.monitor or self.monitor.state == MountState.HEALTHY):
            try:
                dir_path = os.path.dirname(abs_path)
                os.makedirs(dir_path, exist_ok=True)
                with open(abs_path, 'wb') as f:
                    f.write(data)
                # 驗證
                with open(abs_path, 'rb') as f:
                    if hashlib.sha256(f.read()).hexdigest() == sha256_hash:
                        self.stats["total_writes"] += 1
                        return True
            except Exception as e:
                logger.warning(f"直接寫入失敗，進入緩衝: {e}")
        
        # 2. 進入本地緩衝隊列
        entry = BufferEntry(
            operation=operation,
            src_path=rel_path,
            data=data,
            sha256=sha256_hash
        )
        try:
            self.write_queue.put(entry, timeout=1)
            self._persist_entry(entry)
            self.stats["total_writes"] += 1
            self.stats["buffered_writes"] += 1
            self.stats["bytes_buffered"] += len(data)
            logger.info(f"已緩衝: {rel_path} ({len(data)} bytes)")
            return True
        except queue.Full:
            logger.error("緩衝隊列已滿，寫入失敗")
            self.stats["failed_writes"] += 1
            return False
    
    def _persist_entry(self, entry: BufferEntry):
        """持久化緩衝項到本地磁碟"""
        filename = f"{entry.timestamp}_{entry.sha256[:8]}.json"
        filepath = self.buffer_dir / filename
        data = asdict(entry)
        # 移除 data 字段 (二進制不適合 JSON)，單獨存儲
        entry_data = data.copy()
        entry_data.pop("data")
        with open(filepath, 'w') as f:
            json.dump(entry_data, f)
        # 二進制數據單獨存
        bin_path = filepath.with_suffix(".bin")
        with open(bin_path, 'wb') as f:
            f.write(entry.data)
    
    def _load_entry(self, json_path: Path) -> Optional[BufferEntry]:
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            bin_path = json_path.with_suffix(".bin")
            with open(bin_path, 'rb') as f:
                data["data"] = f.read()
            return BufferEntry(**data)
        except Exception as e:
            logger.warning(f"載入緩衝項失敗 {json_path}: {e}")
            return None
    
    def flush_loop(self):
        """刷新循環 - 定期將緩衝寫回目標"""
        self.running = True
        batch = []
        
        while self.running:
            try:
                # 收集一批
                batch.clear()
                try:
                    # 非阻塞獲取第一項
                    entry = self.write_queue.get(timeout=FLUSH_INTERVAL)
                    batch.append(entry)
                    # 嘗試獲取更多
                    while len(batch) < FLUSH_BATCH_SIZE:
                        try:
                            entry = self.write_queue.get_nowait()
                            batch.append(entry)
                        except queue.Empty:
                            break
                except queue.Empty:
                    pass
                
                if batch:
                    self._flush_batch(batch)
                    
            except Exception as e:
                logger.error(f"刷新循環異常: {e}")
                time.sleep(1)
    
    def _flush_batch(self, batch: list):
        """刷新一批緩衝項"""
        if not self.monitor or self.monitor.state not in (MountState.HEALTHY, MountState.DEGRADED):
            # 目標不可用，放回隊列
            for entry in batch:
                try:
                    self.write_queue.put(entry, timeout=1)
                except queue.Full:
                    logger.error("緩衝隊列已滿，丟棄數據")
                    self.stats["failed_writes"] += 1
            return
        
        for entry in batch:
            try:
                abs_path = f"{MOUNT_POINT}/{entry.src_path}"
                dir_path = os.path.dirname(abs_path)
                os.makedirs(dir_path, exist_ok=True)
                
                with open(abs_path, 'wb') as f:
                    f.write(entry.data)
                
                # 驗證 SHA-256
                with open(abs_path, 'rb') as f:
                    if hashlib.sha256(f.read()).hexdigest() == entry.sha256:
                        self.stats["flushed_writes"] += 1
                        self.stats["bytes_flushed"] += len(entry.data)
                        # 刪除本地緩衝文件
                        json_path = self.buffer_dir / f"{entry.timestamp}_{entry.sha256[:8]}.json"
                        bin_path = json_path.with_suffix(".bin")
                        json_path.unlink(missing_ok=True)
                        bin_path.unlink(missing_ok=True)
                        logger.debug(f"已回寫並驗證: {entry.src_path}")
                    else:
                        raise Exception("SHA-256 驗證失敗")
                        
            except Exception as e:
                logger.warning(f"回寫失敗 {entry.src_path}: {e}，重新入隊")
                entry.retries += 1
                if entry.retries < 10:
                    try:
                        self.write_queue.put(entry, timeout=1)
                    except queue.Full:
                        self.stats["failed_writes"] += 1
                else:
                    logger.error(f"重試次數過多，丟棄: {entry.src_path}")
                    self.stats["failed_writes"] += 1
    
    def start(self):
        self.running = True
        self.flusher_thread = threading.Thread(target=self.flush_loop, daemon=True)
        self.flusher_thread.start()
        logger.info("緩衝寫入層已啟動")
    
    def stop(self):
        self.running = False
        if self.flusher_thread:
            self.flusher_thread.join(timeout=10)
        # 保存剩餘隊列
        while not self.write_queue.empty():
            try:
                entry = self.write_queue.get_nowait()
                self._persist_entry(entry)
            except queue.Empty:
                break
        logger.info("緩衝寫入層已停止")

class TelegramNotifier:
    """Telegram 異常通知"""
    
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_alert = {}
        self.alert_cooldown = 300  # 5 分鐘冷卻
    
    def send(self, title: str, message: str, level: str = "warning"):
        if not self.token or not self.chat_id:
            return
        
        key = f"{level}:{title}"
        now = time.time()
        if key in self.last_alert and now - self.last_alert[key] < self.alert_cooldown:
            return
        
        self.last_alert[key] = now
        
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}.get(level, "📢")
        text = f"{emoji} <b>{title}</b>\n{message}\n<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }, timeout=5)
        except Exception as e:
            logger.warning(f"Telegram 發送失敗: {e}")

class TrimacMountDaemon:
    """主守護進程"""
    
    def __init__(self):
        self.monitor = MountMonitor()
        self.buffer = BufferWriteLayer()
        self.buffer.set_monitor(self.monitor)
        self.notifier = TelegramNotifier()
        self.running = False
        self.check_thread = None
        
    def run(self):
        self.running = True
        logger.info("=== TRIMAC 掛載守護進程啟動 ===")
        
        # 啟動緩衝寫入層
        self.buffer.start()
        
        # 啟動監控線程
        self.check_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.check_thread.start()
        
        # 發送啟動通知
        self.notifier.send("TRIMAC 掛載守護啟動", "自動重掛載 + 緩衝寫入層已啟動", "info")
        
        # 主循環
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到停止信號")
        finally:
            self.shutdown()
    
    def _monitor_loop(self):
        """監控主循環"""
        while self.running:
            try:
                start = time.time()
                new_state = self.monitor.check_mount()
                
                if new_state != self.monitor.state:
                    old_state = self.monitor.state
                    self.monitor.state = new_state
                    self._handle_state_change(old_state, new_state)
                
                # 觸發重掛載
                if new_state in (MountState.OFFLINE, MountState.DEGRADED):
                    if self.monitor.remount():
                        # 重掛載成功，狀態將在下次檢查更新
                        pass
                
                self.monitor.last_check = time.time()
                
                # 等待下次檢查
                elapsed = time.time() - start
                sleep_time = max(1, CHECK_INTERVAL - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"監控循環異常: {e}")
                time.sleep(5)
    
    def _handle_state_change(self, old: MountState, new: MountState):
        """狀態變化處理"""
        state_names = {
            MountState.HEALTHY: "健康",
            MountState.DEGRADED: "降級",
            MountState.OFFLINE: "離線",
            MountState.RECOVERING: "恢復中"
        }
        
        logger.warning(f"掛載狀態變化: {state_names[old]} -> {state_names[new]}")
        
        if new == MountState.OFFLINE:
            self.notifier.send(
                "🚨 TRIMAC 掛載點離線",
                f"合併卷 {MOUNT_POINT} 完全不可用\n"
                f"已啟動本地緩衝寫入模式\n"
                f"自動重掛載已觸發"
            )
        elif old == MountState.OFFLINE and new == MountState.HEALTHY:
            self.notifier.send(
                "✅ TRIMAC 掛載點恢復",
                f"合併卷 {MOUNT_POINT} 已恢復正常\n"
                f"本地緩衝正在回寫..."
            )
    
    def shutdown(self):
        logger.info("正在關閉守護進程...")
        self.running = False
        self.buffer.stop()
        self.notifier.send("TRIMAC 掛載守護停止", "守護進程已正常關閉", "info")
        logger.info("守護進程已停止")

# ===== 全局寫入入口函數 (供其他模組調用) =====
_global_buffer: Optional[BufferWriteLayer] = None

def init_global_buffer(monitor: MountMonitor):
    global _global_buffer
    _global_buffer = BufferWriteLayer()
    _global_buffer.set_monitor(monitor)
    _global_buffer.start()
    return _global_buffer

def trimac_write(filepath: str, data: bytes, operation: str = "write") -> bool:
    """全局寫入入口 - 供其他模組調用"""
    if _global_buffer:
        return _global_buffer.write(filepath, data, operation)
    # 降級：直接寫入
    try:
        abs_path = filepath if filepath.startswith("/") else f"{MOUNT_POINT}/{filepath}"
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'wb') as f:
            f.write(data)
        return True
    except Exception as e:
        logger.error(f"降級寫入失敗: {e}")
        return False

# ===== 主入口 =====
def main():
    daemon = TrimacMountDaemon()
    try:
        daemon.run()
    except Exception as e:
        logger.critical(f"守護進程致命錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()