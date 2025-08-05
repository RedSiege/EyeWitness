#!/bin/bash
# Helper function to ensure Firefox is properly installed from apt

fix_firefox_installation() {
    echo "[*] Ensuring Firefox is installed from apt repository..."
    
    # Remove ALL Firefox installations first
    echo "[*] Removing any existing Firefox installations..."
    snap remove firefox 2>/dev/null || true
    snap remove firefox-esr 2>/dev/null || true
    apt-get remove -y firefox firefox-esr 2>/dev/null || true
    apt-get purge -y firefox firefox-esr 2>/dev/null || true
    
    # Clean up any snap-related Firefox symlinks
    rm -f /usr/bin/firefox 2>/dev/null || true
    rm -f /usr/local/bin/firefox 2>/dev/null || true
    
    # Update package cache
    apt-get update
    
    # Install Firefox from PPA with force
    apt-get install -y --allow-downgrades --allow-remove-essential --allow-change-held-packages firefox
    
    # Create a wrapper script if needed
    if command -v firefox &> /dev/null; then
        firefox_bin=$(which firefox)
        if [[ "$firefox_bin" != *"snap"* ]]; then
            echo "[+] Firefox successfully installed from apt!"
            return 0
        fi
    fi
    
    # If we get here, something went wrong
    echo "[!] Firefox installation may have failed"
    return 1
}

# Export the function so it can be used
export -f fix_firefox_installation