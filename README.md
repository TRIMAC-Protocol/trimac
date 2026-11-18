# TRIMAC Fleet Platform (v5.7.4+)

Trilogies AI Equipment — Multi-Agent Collaborative Platform (`x86_64` + Apple Silicon `arm64` Hybrid Architecture).

## Repository Structure
- `venus_m1_macos/` — Venus AI Chapter (`Felix :9902` + 4 Mythical Beast Workers `:9921-9924` + SLP `:19902`) native `LaunchAgents` deployment kit for Apple Silicon M1 (`macOS arm64`).
- `mount_daemon/` — Patched `trimac-mount-daemon v1.0.1` (`setuid` C wrapper + 15s health check + SHA-256 local buffer auto-flush for `/mnt/n`).
- `synology_three_brothers/` — 5-minute NFS + MergerFS self-healing watchdog for the 2.7 TB `TRIMAC-POOL` (`TRI-Synas01 .111`, `Tri-Synas02 .116`, `TRI-Synas03 .114`).
- `trimac_a2a/` — Dual-track Fail-Fast coordinator (`Perfect :9903` primary + `Saturn :9120` 3s failover with monotonic Fencing Tokens).
- `common/` — Cross-OS storage path resolver (`Darwin` `/Volumes/TRIMAC-POOL`, `WSL2` `/mnt/n`, `Ubuntu` `/mnt/trimac_pool`).

## Quick Deploy Workflow (GitHub SSOT)
1. Clone this repository on target node (`git clone ...`).
2. Copy `.env.example` to `.env` and set your local `NVIDIA_API_KEY` (never commit `.env`).
3. On M1 MacBook Pro (`Venus`): run `cd venus_m1_macos && chmod +x install_venus_m1.sh && ./install_venus_m1.sh`.
4. To update any node later: `git pull origin main`.
