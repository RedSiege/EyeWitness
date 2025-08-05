#!/bin/bash
# Original script by @themightyshiv
# Rewritten by moth@bhis (@0x6d6f7468)

# Function for downloading latest geckodriver for the correct CPU architecture
get_gecko() {
    echo
    echo "[*] Getting latest Gecko driver..."

    # Get download links for latest geckodriver via GitHub API
    local latest_geckos=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest \
            | jq '.assets[].browser_download_url' | tr -d \")
    
    # Construct appropriate download URL (or exit if unsupported arch)
    local gecko_url="";
    case ${mach_type} in
        x86_64)
            gecko_url=$(echo "$latest_geckos" | grep "linux64.tar.gz$");;
        i386|i686)
            gecko_url=$(echo "$latest_geckos" | grep "linux32.tar.gz$");;
        aarch64)
            gecko_url=$(echo "$latest_geckos" | grep "linux-aarch64.tar.gz$");;
        *)
            echo "[-] Error: Unsupported architecture: ${mach_type}"
            popd >/dev/null
            exit 1
            ;;
    esac

    # Download, extract, and clean up latest driver tarball
    wget "$gecko_url" -O geckodriver.tar.gz
    tar -xvf geckodriver.tar.gz -C /usr/bin
    rm geckodriver.tar.gz
}

# Function to install Linux and Python dependencies
install_deps() {
    echo
    echo "[*] Installing system dependencies..."

    case ${os_id} in
        debian|kali)
            apt-get update
            apt install -y python3-rapidfuzz
            apt install -y python3-selenium
            apt install -y python3-psutil
            apt install -y python3-pyvirtualdisplay 2>/dev/null || true

            apt-get install -y wget curl jq cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox-esr tar
            # Ensure Firefox ESR is really installed (sometimes package name varies)
            if ! command -v firefox &> /dev/null; then
                echo "[*] Firefox not found, trying alternative package names..."
                apt-get install -y firefox || apt-get install -y firefox-browser || true
            fi
            ;;
        ubuntu|linuxmint)
            apt-get update
            apt install -y python3-rapidfuzz
            apt install -y python3-selenium
            apt install -y python3-psutil
            apt install -y python3-pyvirtualdisplay 2>/dev/null || true
            apt-get install -y wget curl jq cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox x11-utils tar
            # Ensure Firefox is really installed (sometimes package name varies)
            if ! command -v firefox &> /dev/null; then
                echo "[*] Firefox not found, trying alternative package names..."
                apt-get install -y firefox-esr || apt-get install -y firefox-browser || true
            fi
            ;;
        arch|manjaro)
            pacman -Syu
            pacman -S --noconfirm wget curl jq cmake python3 python-xvfbwrapper python-pip python-netaddr firefox tar
            ;;
        alpine)
            apk update
            apk add wget curl jq cmake python3 xvfb py-pip py-netaddr python3-dev firefox tar

            # from https://stackoverflow.com/questions/58738920/running-geckodriver-in-an-alpine-docker-container
            # Get all the prereqs
            wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://alpine-pkgs.sgerrand.com/sgerrand.rsa.pub
            wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.30-r0/glibc-2.30-r0.apk
            wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.30-r0/glibc-bin-2.30-r0.apk
            apk add glibc-2.30-r0.apk
            apk add glibc-bin-2.30-r0.apk
            
            # And of course we need Firefox if we actually want to *use* GeckoDriver
            apk add firefox-esr=60.9.0-r0
            ;;
        centos|rocky|fedora)
            yum install -y wget curl jq python3 xorg-x11-server-Xvfb python3-pip firefox gcc cmake python3-devel gcc cmake python3-devel tar
            ;;
        *)
            echo "[-] Error: Unsupported Operating System ID: ${os_id}"
            popd >/dev/null
            exit 1
            ;;
    esac

    echo
    echo "[*] Installing Python dependencies..."
    # Check if pip needs upgrade using system package manager
    case ${os_id} in
        debian|kali|ubuntu|linuxmint)
            # Install pyvirtualdisplay via apt if available
            apt install -y python3-pyvirtualdisplay 2>/dev/null || true
            # Install argcomplete via apt
            apt install -y python3-argcomplete 2>/dev/null || python3 -m pip install --break-system-packages argcomplete
            ;;
        *)
            # For non-debian systems, use pip normally
            pip3 install --upgrade pip
            python3 -m pip install -r requirements.txt
            python3 -m pip install argcomplete
            ;;
    esac
}

# Make sure we're in the setup directory
pushd "$(dirname "$0")" >/dev/null

# Make sure we're running as root
echo
echo "[*] Checking if running as root..."
if [ "$EUID" -ne 0 ]; then
    echo "[-] Error: You must run this setup script with root privileges."
    echo
    popd >/dev/null
    exit 1
else
    echo "[+] Running as root."
fi

# Get some system information
echo
echo "[*] Getting system information..."
os_id=$(grep ^ID= /etc/os-release | cut -d'=' -f2 | tr -d '"')
mach_type=$(uname -m)

# Install dependencies
install_deps

# Get the gecko
get_gecko

# Get out of there!
popd >/dev/null

# Verify critical dependencies
echo
echo "[*] Verifying installation..."
missing_deps=0

if ! command -v firefox &> /dev/null; then
    echo "[-] Firefox not found - EyeWitness requires Firefox to capture screenshots"
    echo "    Try: sudo apt install firefox-esr (or firefox)"
    missing_deps=1
fi

if ! command -v geckodriver &> /dev/null; then
    echo "[-] Geckodriver not found in PATH"
    missing_deps=1
fi

if ! command -v Xvfb &> /dev/null && [ "${os_id}" != "windows" ]; then
    echo "[-] Xvfb not found - required for headless operation"
    echo "    Try: sudo apt install xvfb"
    missing_deps=1
fi

if [ $missing_deps -eq 0 ]; then
    echo "[+] All critical dependencies verified!"
else
    echo
    echo "[!] Some dependencies are missing. EyeWitness may not work properly."
    echo "[*] Run setup/check-dependencies.sh for detailed diagnostics"
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
echo "[+] Setup script completed successfully. Enjoy EyeWitness! ^_^"
echo "[*] Be sure to check out Red Siege!"
echo "[*] https://www.redsiege.com"
echo