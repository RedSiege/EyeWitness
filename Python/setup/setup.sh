#!/bin/bash
# Original script by @themightyshiv
# Rewritten by moth@bhis (@0x6d6f7468)

require_root() {
    echo
    echo "[*] Checking if running as root...";
    if [ "$EUID" -ne 0 ]; then
        echo "[-] Error: You must run this setup script with root privileges."
        echo
        exit 1
    else
        echo "[+] Running as root."
    fi
}

check_system() {
    echo
    echo "[*] Getting system information..."
    os_id=$(grep ^ID= /etc/os-release | cut -d'=' -f2)
    mach_type=$(uname -m)
}

get_gecko() {
    echo
    echo "[*] Getting latest Gecko driver..."

    # Get download links for latest geckodriver via GitHub API
    local latest_geckos=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest \
            | grep browser_download_url | cut -d':' -f2,3 | tr -d \" | tr -d '[:blank:]')
    
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
            exit 1
            ;;
    esac

    # Download, extract, and clean up latest driver tarball
    wget "$gecko_url" -O geckodriver.tar.gz
    tar -xvf geckodriver.tar.gz -C /usr/bin
    rm geckodriver.tar.gz
}

install_deps() {
    echo
    echo "[*] Installing system dependencies..."

    case ${os_id} in
        debian|kali)
            apt update
            apt install -y wget cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox-esr
            ;;
        ubuntu|linuxmint)
            apt update
            apt install -y wget cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox x11-utils
            ;;
        arch|manjaro)
            pacman -Syu
            pacman -S --noconfirm wget cmake python3 python-xvfbwrapper python-pip python-netaddr firefox
            ;;
        alpine)
            apk update
            apk add wget cmake python3 xvfb py-pip py-netaddr python3-dev firefox

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
            yum install -y wget python3 xorg-x11-server-Xvfb python3-pip firefox
            yum install -y gcc
            yum install -y cmake
            yum install -y python3-devel
            ;;
        *)
            echo "[-] Error: Unsupported Operating System ID: ${os_id}"
            ;;
    esac

    # PEP 668 workaround
    PIP_BREAK_SYSTEM_PACKAGES=1

    echo
    echo "[*] Installing Python dependencies..."
    pip3 install --upgrade pip
    python3 -m pip install -r requirements.txt

    unset PIP_BREAK_SYSTEM_PACKAGES
}

done_success() {
    echo
    echo "[+] Setup script completed successfully. Enjoy EyeWitness! ^_^"
    echo "[*] Be sure to check out Red Siege!"
    echo "[*] https://www.redsiege.com"
    echo
}

# check root
require_root;
check_system;
get_gecko;
install_deps;
done_success;
