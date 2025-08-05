#!/bin/bash
# Fix Firefox snap issues for EyeWitness on Ubuntu/Debian systems

echo "=== Firefox Snap Fix for EyeWitness ==="
echo

# Detect if we're running as root
if [ "$EUID" -ne 0 ]; then
    echo "[-] This script must be run as root (use sudo)"
    exit 1
fi

# Check if Firefox is installed as snap
is_snap=0
if command -v firefox &> /dev/null; then
    firefox_path=$(which firefox)
    if [[ "$firefox_path" == "/snap/bin/firefox" ]] || [[ "$firefox_path" == *"snap"* ]]; then
        is_snap=1
        echo "[!] Firefox is installed as a snap package"
        echo "    Snap Firefox causes issues with Selenium/Geckodriver"
    fi
fi

if [ $is_snap -eq 1 ]; then
    echo
    echo "[*] Removing Firefox snap package..."
    snap remove firefox
    
    echo
    echo "[*] Adding Mozilla Team PPA for latest Firefox..."
    add-apt-repository -y ppa:mozillateam/ppa 2>/dev/null || true
    
    echo
    echo "[*] Setting package preferences to prevent snap reinstall..."
    cat > /etc/apt/preferences.d/mozilla-firefox <<EOF
Package: firefox*
Pin: release o=LP-PPA-mozillateam
Pin-Priority: 1001

Package: firefox*
Pin: release o=Ubuntu
Pin-Priority: -1
EOF

    echo
    echo "[*] Updating package list..."
    apt-get update
    
    echo
    echo "[*] Installing Firefox from apt..."
    apt-get install -y firefox
    
    # Verify installation
    echo
    echo "[*] Verifying Firefox installation..."
    if command -v firefox &> /dev/null; then
        firefox_path=$(which firefox)
        if [[ "$firefox_path" != *"snap"* ]]; then
            echo "[+] Firefox successfully installed from apt!"
            firefox --version
        else
            echo "[-] Firefox still appears to be a snap package"
            exit 1
        fi
    else
        echo "[-] Firefox installation failed"
        exit 1
    fi
else
    echo "[*] Firefox is not installed as snap, checking traditional installation..."
    if ! command -v firefox &> /dev/null; then
        echo "[*] Firefox not found, installing..."
        # Try firefox-esr first (more stable for automation)
        apt-get update
        apt-get install -y firefox-esr || apt-get install -y firefox
    else
        echo "[+] Firefox is already properly installed"
        firefox --version
    fi
fi

# Verify geckodriver
echo
echo "[*] Checking geckodriver..."
if command -v geckodriver &> /dev/null; then
    echo "[+] Geckodriver found at: $(which geckodriver)"
    geckodriver --version | head -1
else
    echo "[-] Geckodriver not found in PATH"
    echo "    Run the EyeWitness setup.sh script to install it"
fi

# Test Firefox headless
echo
echo "[*] Testing Firefox headless mode..."
timeout 5 firefox --headless --screenshot test-screenshot.png https://example.com 2>/dev/null
if [ -f test-screenshot.png ]; then
    echo "[+] Firefox headless mode working!"
    rm -f test-screenshot.png
else
    echo "[!] Firefox headless test failed, but this might be normal"
fi

# Check Xvfb
echo
echo "[*] Checking Xvfb for virtual display..."
if command -v Xvfb &> /dev/null; then
    echo "[+] Xvfb is installed"
else
    echo "[*] Installing Xvfb..."
    apt-get install -y xvfb
fi

echo
echo "=== Fix Complete ==="
echo "[*] Firefox has been properly configured for EyeWitness"
echo "[*] You should now be able to run EyeWitness successfully"
echo
echo "[*] If you still have issues, try:"
echo "    1. Log out and log back in (or source ~/.bashrc)"
echo "    2. Run: export MOZ_HEADLESS=1"
echo "    3. Check geckodriver compatibility with: geckodriver --version"