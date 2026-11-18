#!/bin/bash
set -e
echo "=== TRIMAC v5.7.4 金星號 (M1 MacBook Pro arm64) 一鍵部署 ==="

BASE_DIR="$HOME/trimac_venus"
VENV_DIR="$BASE_DIR/.venv_arm64"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$BASE_DIR/logs"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$BASE_DIR" "$LAUNCH_DIR" "$LOG_DIR"
cp -f "$SCRIPT_DIR/venus_node.py" "$BASE_DIR/venus_node.py"

# 1. 建立原生 ARM64 Python 虛擬環境 (避開 macOS PEP 668)
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet fastapi uvicorn httpx

# 2. 生成金星號專屬防越級密鑰 (僅本機存留)
SECRET_FILE="$BASE_DIR/.venus_chapter_secret"
if [ ! -f "$SECRET_FILE" ]; then
    python3 -c "import secrets; print(secrets.token_hex(32))" > "$SECRET_FILE"
    chmod 600 "$SECRET_FILE"
fi
CHAPTER_SECRET="$(cat "$SECRET_FILE")"
NIM_KEY="${NVIDIA_API_KEY:-REPLACE_WITH_NVIDIA_API_KEY}"

create_plist() {
    local LABEL="$1"
    local NODE_ID="$2"
    local NODE_CODE="$3"
    local ROLE="$4"
    local BIND="$5"
    local PORT="$6"
    local PLIST="$LAUNCH_DIR/${LABEL}.plist"

    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${VENV_DIR}/bin/python</string>
        <string>${BASE_DIR}/venus_node.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TRIMAC_NODE_ID</key><string>${NODE_ID}</string>
        <key>TRIMAC_NODE_CODE</key><string>${NODE_CODE}</string>
        <key>TRIMAC_ROLE</key><string>${ROLE}</string>
        <key>BIND_HOST</key><string>${BIND}</string>
        <key>PORT</key><string>${PORT}</string>
        <key>VENUS_CHAPTER_SECRET</key><string>${CHAPTER_SECRET}</string>
        <key>NVIDIA_API_KEY</key><string>${NIM_KEY}</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>${LOG_DIR}/${NODE_ID}.out.log</string>
    <key>StandardErrorPath</key><string>${LOG_DIR}/${NODE_ID}.err.log</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load -w "$PLIST"
}

create_plist "com.trimac.venus.felix"    "felix"    "TRI-VENUS-02"  "captain" "0.0.0.0"   "9902"
create_plist "com.trimac.venus.qinglong" "qinglong" "TRI-VENUS-02A" "worker"  "127.0.0.1" "9921"
create_plist "com.trimac.venus.baihu"    "baihu"    "TRI-VENUS-02B" "worker"  "127.0.0.1" "9922"
create_plist "com.trimac.venus.zhuque"   "zhuque"   "TRI-VENUS-02C" "worker"  "127.0.0.1" "9923"
create_plist "com.trimac.venus.xuanwu"   "xuanwu"   "TRI-VENUS-02D" "worker"  "127.0.0.1" "9924"

echo ""
echo "✅ 金星號 1+4 LaunchAgents 已載入！請緊記執行一次防休眠鎖："
echo "   sudo pmset -a sleep 0 displaysleep 0 disksleep 0 disablesleep 1"
echo "✅ 請執行 tailscale ip -4 取得本機新 IP，並更新至都中樞 Jupiter！"
