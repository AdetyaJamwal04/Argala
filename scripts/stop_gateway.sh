#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Clean Stop Script for Argala Gateway & Watchdog Supervisor
# ==============================================================================

BASE_DIR="$HOME/addy_space"
PID_FILE="$BASE_DIR/watchdog.pid"

if [ -f "$PID_FILE" ]; then
    WPID=$(cat "$PID_FILE")
    echo "Stopping watchdog supervisor process (PID: $WPID)..."
    kill "$WPID" 2>/dev/null
    rm -f "$PID_FILE"
fi

echo "Terminating running Uvicorn server..."
for pid in $(ps -A | grep '[p]ython' | awk '{print $1}'); do
    kill "$pid" 2>/dev/null
done


if command -v termux-wake-unlock >/dev/null 2>&1; then
    termux-wake-unlock
    echo "Released Termux wake-lock."
fi

echo "Argala shutdown complete."
