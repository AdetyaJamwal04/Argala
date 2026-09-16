#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Argala Process Supervisor & Watchdog for Android Termux
# Ensures 24/7 uptime, holds Android wake-lock, and auto-restarts on termination.
# ==============================================================================

BASE_DIR="$HOME/addy_space"
LOG_FILE="$BASE_DIR/gateway.log"
PID_FILE="$BASE_DIR/watchdog.pid"

echo $$ > "$PID_FILE"
cd "$BASE_DIR" || exit 1

# Ensure Termux wake-lock is acquired to prevent Android battery sleep
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Acquired Termux wake-lock" >> "$LOG_FILE"
fi

# Activate virtualenv
if [ -f "$BASE_DIR/.venv/bin/activate" ]; then
    source "$BASE_DIR/.venv/bin/activate"
fi

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting Argala Supervisor loop..." >> "$LOG_FILE"

while true; do
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Launching Uvicorn server on 0.0.0.0:8000..." >> "$LOG_FILE"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "$LOG_FILE" 2>&1
    EXIT_STATUS=$?
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Argala gateway exited with status $EXIT_STATUS. Restarting in 2s..." >> "$LOG_FILE"
    sleep 2
done
