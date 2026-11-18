#!/usr/bin/env python3
"""
TRIMAC Mount Helper - setuid root wrapper for mount/umount operations
編譯後設置 setuid: chown root:root /usr/local/bin/trimac-mount-helper && chmod 4755 /usr/local/bin/trimac-mount-helper

功能：
- mount: 掛載 Windows N: 盤到 /mnt/n (drvfs)
- umount: 強制卸載 /mnt/n
- cleanup: 清理殘留目錄並重建
- status: 檢查掛載狀態
"""
import os
import sys
import subprocess
import json
import shutil
import time

MOUNT_POINT = "/mnt/n"
WSL_EXE = "/mnt/c/Windows/System32/wsl.exe"
DRVFS_OPTS = "rw,relatime,aname=drvfs;path=N:;symlinkroot=/mnt/,cache=0x5,access=client,msize=65536"

def run_cmd(cmd, timeout=30):
    """執行命令並返回結果"""
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "timeout", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

def _prepare_mount_point():
    """處理殘留掛載點：確保 /mnt/n 是乾淨目錄，非掛載狀態"""
    if os.path.exists(MOUNT_POINT):
        if os.path.ismount(MOUNT_POINT):
            # 已掛載，先強制卸載
            run_cmd(["umount", "-f", "-l", MOUNT_POINT], timeout=10)
            time.sleep(1)
        elif not os.path.isdir(MOUNT_POINT):
            # 是文件或其他特殊類型，刪除
            try:
                os.remove(MOUNT_POINT)
            except Exception:
                try:
                    shutil.rmtree(MOUNT_POINT, ignore_errors=True)
                except Exception:
                    pass

    # 確保目錄存在
    try:
        os.makedirs(MOUNT_POINT, exist_ok=True)
    except FileExistsError:
        pass

def cmd_mount():
    """掛載 drvfs"""
    # 1. 喚醒 Windows SMB
    run_cmd(["cmd.exe", "/c", "dir N:\\\\ >nul 2>&1"], timeout=10)

    # 2. 清理殘留掛載點
    _prepare_mount_point()

    # 3. 執行掛載 (直接使用 Linux mount，因為 helper 已經是 root)
    result = run_cmd([
        "mount", "-t", "drvfs", "N:", MOUNT_POINT, "-o", DRVFS_OPTS
    ])

    # 4. 驗證
    if result["success"]:
        verify = run_cmd(["findmnt", "-n", MOUNT_POINT])
        if verify["success"] and "drvfs" in verify["stdout"]:
            return {"success": True, "msg": "mounted"}

    return {"success": False, "msg": result["stderr"] or "mount failed"}

def cmd_umount():
    """強制卸載"""
    result = run_cmd(["umount", "-f", "-l", MOUNT_POINT])
    return {"success": result["success"], "msg": "unmounted" if result["success"] else result["stderr"]}

def cmd_cleanup():
    """清理殘留目錄並重建"""
    run_cmd(["umount", "-f", "-l", MOUNT_POINT], timeout=10)

    try:
        if os.path.exists(MOUNT_POINT):
            shutil.rmtree(MOUNT_POINT)
    except Exception:
        pass

    os.makedirs(MOUNT_POINT, exist_ok=True)
    return {"success": True, "msg": "cleaned"}

def cmd_status():
    """檢查掛載狀態"""
    if not os.path.exists(MOUNT_POINT):
        return {"mounted": False, "msg": "mount point not exist"}

    result = run_cmd(["findmnt", "-n", MOUNT_POINT])
    if result["success"] and "drvfs" in result["stdout"]:
        return {"mounted": True, "msg": "healthy", "details": result["stdout"]}
    elif result["success"]:
        return {"mounted": True, "msg": "mounted but not drvfs", "details": result["stdout"]}
    else:
        return {"mounted": False, "msg": "not mounted"}

def cmd_wake_smb():
    """喚醒 Windows SMB 連線"""
    result = run_cmd(["cmd.exe", "/c", "dir N:\\\\ >nul 2>&1"], timeout=10)
    return {"success": result["success"], "msg": "wake sent"}

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: trimac-mount-helper <mount|umount|cleanup|status|wake>"}))
        sys.exit(1)

    cmd = sys.argv[1]

    # 檢查是否為 root (setuid 會生效)
    if os.geteuid() != 0:
        print(json.dumps({"error": "must run as root (setuid required)"}))
        sys.exit(1)

    commands = {
        "mount": cmd_mount,
        "umount": cmd_umount,
        "cleanup": cmd_cleanup,
        "status": cmd_status,
        "wake": cmd_wake_smb,
    }

    if cmd not in commands:
        print(json.dumps({"error": f"unknown command: {cmd}"}))
        sys.exit(1)

    result = commands[cmd]()
    print(json.dumps(result))

if __name__ == "__main__":
    main()