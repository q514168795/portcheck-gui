#!/bin/bash
# Port Checker GUI 启动器
set -e
cd "$(dirname "$(readlink -f "$0")")"

LOG_DIR="$HOME/.cache/portcheck-gui"
mkdir -p "$LOG_DIR"
ERR_LOG="$LOG_DIR/launcher.err"

# 简易日志轮转
if [[ -f "$ERR_LOG" ]] && [[ "$(stat -c%s "$ERR_LOG" 2>/dev/null || echo 0)" -gt 1048576 ]]; then
    mv -f "$ERR_LOG" "$ERR_LOG.1"
fi

# 借 portcheck venv（已带 system-site-packages，gi 在系统层）
PY="/home/hy/apps/portcheck/venv/bin/python"
[[ -x "$PY" ]] || PY="python3"

exec "$PY" main.py "$@" 2>>"$ERR_LOG"
