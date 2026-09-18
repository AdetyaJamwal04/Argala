#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Argala Termux:Boot Automation Installer
# Configures unattended 24/7 startup on Android system boot.
# ==============================================================================

set -e

BOOT_DIR="$HOME/.termux/boot"
BOOT_SCRIPT="$BOOT_DIR/start-argala.sh"
APP_DIR="$HOME/addy_space"

echo "=================================================="
echo "    ARGALA UNATTENDED BOOT INSTALLER             "
echo "=================================================="

# 1. Create boot directory
mkdir -p "$BOOT_DIR"
echo "[+] Verified directory: $BOOT_DIR"

# 2. Write boot launch script
cat << 'EOF' > "$BOOT_SCRIPT"
#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Argala Unattended Startup - Executed by Termux:Boot on Android reboot
# ==============================================================================

BASE_DIR="$HOME/addy_space"
LOG_FILE="$BASE_DIR/boot.log"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Android boot detected. Initializing Argala..." >> "$LOG_FILE"

# 1. Wait for Android network stack and Tailscale interface to settle
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Waiting 10 seconds for network interfaces..." >> "$LOG_FILE"
sleep 10

# 2. Acquire Termux wake-lock to prevent OS deep sleep
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Acquired wake-lock." >> "$LOG_FILE"
fi

# 3. Launch watchdog supervisor in background
if [ -f "$BASE_DIR/scripts/watchdog.sh" ]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting Argala Watchdog..." >> "$LOG_FILE"
    nohup bash "$BASE_DIR/scripts/watchdog.sh" >> "$BASE_DIR/gateway.log" 2>&1 &
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Watchdog spawned with PID $!" >> "$LOG_FILE"
fi

# 4. Announce successful recovery via TTS and notification
if command -v termux-notification >/dev/null 2>&1; then
    termux-notification \
        --id "argala_boot" \
        --title "🔒 Argala Online" \
        --content "Sovereign edge gateway restored after system reboot." \
        --priority "high"
fi

if command -v termux-tts-speak >/dev/null 2>&1; then
    termux-tts-speak "Argala sovereign gateway online." &
fi
EOF

chmod +x "$BOOT_SCRIPT"
echo "[+] Installed executable boot script at: $BOOT_SCRIPT"

echo ""
echo "=================================================="
echo "   INSTALLATION COMPLETE!                         "
echo "=================================================="
echo "Next step: Ensure Termux:Boot APK is installed on the phone."
echo "Script location: $BOOT_SCRIPT"
