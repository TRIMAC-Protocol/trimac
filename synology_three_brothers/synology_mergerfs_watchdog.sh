#!/bin/bash
# ==============================================================================
# TRIMAC v5.7.4 - Synology「三兄弟伺服器」內部 NFS + MergerFS 5分鐘自癒巡檢腳本
# 部署位置：TRI-Synas01 (DS218+ 192.168.50.111) DSM 控制台 -> 任務排程器 (root)
# 觸發條件：開機 (Boot-up) + 每 5 分鐘定時巡檢
# ==============================================================================
POOL_DIR="/volume1/TRIMAC-POOL"
LOCAL_V1="/volume1/local_vol1"
BIN_DIR="/volume1/@mergerfs"
TMP_LOG="/tmp/trimac_pool_status.log"

# 快速健康檢查：若 MergerFS 已掛載且 .116 與 .114 均在 3 秒內可讀，直接 0 開銷退出
if mountpoint -q "$POOL_DIR" && \
   mountpoint -q "/mnt/nas_branches/nas_116" && \
   mountpoint -q "/mnt/nas_branches/nas_114" && \
   timeout 3 ls "/mnt/nas_branches/nas_116" >/dev/null 2>&1 && \
   timeout 3 ls "/mnt/nas_branches/nas_114" >/dev/null 2>&1; then
    exit 0
fi

# 偵測到任一節點重啟或掛載脫落，立即啟動自癒重掛載
mkdir -p "$BIN_DIR" "$LOCAL_V1"
umount -l "$POOL_DIR" 2>/dev/null

echo "=== TRIMAC v5.7.4 三兄弟伺服器自癒重掛載報告 ($(date)) ===" > "$TMP_LOG"

if [ ! -x "$BIN_DIR/mergerfs" ]; then
    curl -k -L -s "https://github.com/trapexit/mergerfs/releases/download/2.40.2/mergerfs-static-linux_amd64.tar.gz" -o "$BIN_DIR/mfs.tar.gz"
    tar -xzf "$BIN_DIR/mfs.tar.gz" -C "$BIN_DIR" 2>>"$TMP_LOG"
    FOUND_BIN=$(find "$BIN_DIR" -name "mergerfs" -type f | head -n 1)
    [ -n "$FOUND_BIN" ] && cp "$FOUND_BIN" "$BIN_DIR/mergerfs" && chmod +x "$BIN_DIR/mergerfs"
fi

BRANCH_LIST="$LOCAL_V1"

for IP in 192.168.50.116 192.168.50.114; do
    EXPORT_PATH=$(showmount -e "$IP" 2>/dev/null | awk '/^\/volume1\// {print $1; exit}')
    if [ -z "$EXPORT_PATH" ]; then
        [ "$IP" = "192.168.50.116" ] && EXPORT_PATH="/volume1/pool_vol1" || EXPORT_PATH="/volume1/pool_vol2"
    fi
    MNT="/mnt/nas_branches/nas_${IP##*.}"
    mkdir -p "$MNT"
    umount -l "$MNT" 2>/dev/null
    if mount -t nfs -o rw,soft,timeo=30,retrans=2,nolock "${IP}:${EXPORT_PATH}" "$MNT" 2>>"$TMP_LOG"; then
        chmod 777 "$MNT" 2>/dev/null
        BRANCH_LIST="$BRANCH_LIST:$MNT"
        echo "[自癒掛載成功] ${IP}:${EXPORT_PATH} -> $MNT" >> "$TMP_LOG"
    else
        echo "[節點暫未就緒，將於下輪重試] ${IP}:${EXPORT_PATH}" >> "$TMP_LOG"
    fi
done

chmod 777 "$LOCAL_V1" 2>/dev/null
"$BIN_DIR/mergerfs" -o allow_other,category.create=mfs,moveonenospc=true,minfreespace=10G,fsname=TRIMAC_Pool "$BRANCH_LIST" "$POOL_DIR" 2>>"$TMP_LOG"
df -h "$POOL_DIR" >> "$TMP_LOG" 2>&1
cp -f "$TMP_LOG" "$POOL_DIR/POOL_STATUS.txt"
chmod 666 "$POOL_DIR/POOL_STATUS.txt"
