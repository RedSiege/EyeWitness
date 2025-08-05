#!/bin/bash
# Wrapper script to run EyeWitness with proper headless configuration

# Set proper environment for headless operation
export MOZ_HEADLESS=1
export MOZ_DISABLE_GPU=1
export DISPLAY=:99

# Ensure we're in the right directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/Python" || exit 1

# Check if Xvfb is running, start if needed
if ! pgrep -x Xvfb > /dev/null; then
    echo "[*] Starting virtual display (Xvfb)..."
    Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
    sleep 2
fi

# Pass all arguments to EyeWitness
echo "[*] Running EyeWitness with headless configuration..."
python3 EyeWitness.py "$@"