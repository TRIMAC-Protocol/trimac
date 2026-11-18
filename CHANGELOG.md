# Changelog

## [v5.7.4] - 2026-11-19
- Established GitHub as the Single Source of Truth (SSOT) deployment bridge for TRIMAC v5.7.4+.
- Added Apple Silicon M1 (`macOS arm64`) native `LaunchAgents` deployment kit (`venus_m1_macos/`).
- Integrated patched `trimac-mount-daemon v1.0.1` (`_load_persisted_buffer` `.bin` fix + real-time `os.path.ismount` guard).
- Added Synology Three Brothers 5-minute NFS/MergerFS self-healing watchdog (`synology_three_brothers/`).
- Added cross-OS storage resolver (`common/storage_resolver.py`) and strict `.gitignore` secret protection.
