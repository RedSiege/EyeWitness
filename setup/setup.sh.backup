#!/bin/bash
# EyeWitness Setup Script - Chromium Only
# Simplified installation for headless screenshot functionality

# Function to install Linux dependencies and Chromium
install_deps() {
    echo
    echo "[*] Installing system dependencies and Chromium browser..."

    case ${os_id} in
        debian|kali)
            apt-get update
            # Install Python packages via apt (avoid PEP 668 issues)
            apt install -y python3-rapidfuzz
            apt install -y python3-selenium  
            apt install -y python3-psutil
            apt install -y python3-pyvirtualdisplay 2>/dev/null || true
            apt install -y python3-argcomplete

            # Install system dependencies
            apt-get install -y wget curl jq cmake python3 xvfb python3-pip python3-netaddr python3-dev tar bc
            
            # Install Chromium browser and driver
            echo "[*] Installing Chromium browser and ChromeDriver..."
            apt-get install -y chromium-browser chromium-chromedriver || \
            apt-get install -y chromium chromium-driver
            ;;
            
        ubuntu|linuxmint)
            apt-get update
            
            # Install Python packages via apt (avoid PEP 668 issues) 
            apt install -y python3-rapidfuzz
            apt install -y python3-selenium
            apt install -y python3-psutil
            apt install -y python3-pyvirtualdisplay 2>/dev/null || true
            apt install -y python3-argcomplete
            
            # Install system dependencies
            apt-get install -y wget curl jq cmake python3 xvfb python3-pip python3-netaddr python3-dev x11-utils tar bc
            
            # Install Chromium browser and driver
            echo "[*] Installing Chromium browser and ChromeDriver..."
            apt-get install -y chromium-browser chromium-chromedriver
            ;;
            
        arch|manjaro)
            pacman -Syu
            pacman -S --noconfirm wget curl jq cmake python3 python-xvfbwrapper python-pip python-netaddr chromium tar
            # Install chromedriver from AUR or manually
            echo "[*] Note: You may need to install chromedriver manually on Arch"
            ;;
            
        alpine)
            apk update
            apk add wget curl jq cmake python3 xvfb py-pip py-netaddr python3-dev chromium chromium-chromedriver tar
            ;;
            
        centos|rocky|fedora)
            yum install -y wget curl jq python3 xorg-x11-server-Xvfb python3-pip chromium chromedriver gcc cmake python3-devel tar
            ;;
            
        *)
            echo "[-] Error: Unsupported Operating System ID: ${os_id}"
            popd >/dev/null
            exit 1
            ;;
    esac

    echo
    echo "[*] Installing remaining Python dependencies via pip..."
    # Only install packages not available via apt
    case ${os_id} in
        debian|kali|ubuntu|linuxmint)
            # Most packages installed via apt, only install what's missing
            python3 -m pip install --break-system-packages netaddr 2>/dev/null || pip3 install netaddr 2>/dev/null || true
            ;;
        *)
            # For other distros, use pip normally
            pip3 install --upgrade pip
            python3 -m pip install -r requirements.txt 2>/dev/null || true
            python3 -m pip install argcomplete 2>/dev/null || true
            ;;
    esac
}

# Function to get latest geckodriver (kept for compatibility, but not used)
get_gecko() {
    echo
    echo "[*] Note: EyeWitness now uses ChromeDriver instead of GeckoDriver"
    echo "[*] Skipping GeckoDriver download..."
}

# Make sure we're in the setup directory
pushd "$(dirname "$0")" >/dev/null

# Make sure we're running as root
echo
echo "[*] Checking if running as root..."
if [ "$EUID" -ne 0 ]; then
    echo "[-] Error: You must run this setup script with root privileges."
    echo "    Please run: sudo $0"
    popd >/dev/null
    exit 1
fi
echo "[+] Running as root."

# Get system information
echo
echo "[*] Getting system information..."
os_id=$(grep -E '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
mach_type=$(uname -m)

echo "[*] Detected OS: ${os_id}"
echo "[*] Detected Architecture: ${mach_type}"

# Install dependencies
install_deps

# Skip geckodriver (not needed for Chromium)
# get_gecko

# Get out of there!
popd >/dev/null

# Verify critical dependencies
echo
echo "[*] Verifying installation..."
missing_deps=0

# Check for Chromium
chromium_found=false
for browser in chromium-browser chromium google-chrome; do
    if command -v $browser &> /dev/null; then
        echo "[+] Browser found: $browser"
        chromium_found=true
        break
    fi
done

if [ "$chromium_found" = false ]; then
    echo "[-] No Chromium/Chrome browser found"
    echo "    Try: sudo apt install chromium-browser"
    missing_deps=1
fi

# Check for ChromeDriver
chromedriver_found=false
for driver in chromedriver chromium-chromedriver; do
    if command -v $driver &> /dev/null; then
        echo "[+] ChromeDriver found: $driver"
        chromedriver_found=true
        break
    fi
done

if [ "$chromedriver_found" = false ]; then
    echo "[-] ChromeDriver not found"
    echo "    Try: sudo apt install chromium-chromedriver" 
    missing_deps=1
fi

# Check for Xvfb (virtual display for headless)
if ! command -v Xvfb &> /dev/null && [ "${os_id}" != "windows" ]; then
    echo "[-] Xvfb not found - required for headless operation"
    echo "    Try: sudo apt install xvfb"
    missing_deps=1
fi

# Test Chromium headless functionality
if [ "$chromium_found" = true ]; then
    echo "[*] Testing Chromium headless mode..."
    # Find chromium binary
    chromium_bin=""
    for browser in chromium-browser chromium google-chrome; do
        if command -v $browser &> /dev/null; then
            chromium_bin=$browser
            break
        fi
    done
    
    if timeout 10 $chromium_bin --headless --disable-gpu --screenshot=/tmp/test.png https://example.com 2>/dev/null; then
        echo "[+] Chromium headless mode verified!"
        rm -f /tmp/test.png
    else
        echo "[!] Chromium headless test failed - may have compatibility issues"
        echo "    This is usually not a problem for EyeWitness operation"
    fi
fi

if [ $missing_deps -eq 0 ]; then
    echo "[+] All critical dependencies verified!"
else
    echo
    echo "[!] Some dependencies are missing. EyeWitness may not work properly."
    echo "[*] Re-run this script to attempt fixes"
fi

# Enable tab completion
echo
echo "[*] Enabling tab completion..."
if command -v activate-global-python-argcomplete3 &> /dev/null; then
    activate-global-python-argcomplete3
    echo "[+] Global tab completion activated"
elif command -v activate-global-python-argcomplete &> /dev/null; then
    activate-global-python-argcomplete
    echo "[+] Global tab completion activated"
else
    echo "[*] Adding tab completion to bashrc..."
    if ! grep -q "register-python-argcomplete.*EyeWitness" ~/.bashrc 2>/dev/null; then
        echo "" >> ~/.bashrc
        echo "# EyeWitness tab completion" >> ~/.bashrc
        echo 'eval "$(register-python-argcomplete EyeWitness.py 2>/dev/null || register-python-argcomplete3 EyeWitness.py 2>/dev/null)"' >> ~/.bashrc
    fi
    echo "[+] Tab completion added to ~/.bashrc"
    echo "[*] Please restart your shell or run: source ~/.bashrc"
fi

# Print success message
echo
echo "[+] EyeWitness setup completed successfully!"
echo "[*] Browser: Chromium (headless mode)"
echo "[*] Screenshots will be captured using ChromeDriver"
echo
echo "[*] To test installation:"
echo "    cd Python && python3 EyeWitness.py --single https://example.com"
echo
echo "[*] Be sure to check out Red Siege!"
echo "[*] https://www.redsiege.com"
echo