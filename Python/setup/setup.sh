#!/bin/bash

# Function to install EyeWitness dependencies
install_dependencies() {
    case "$osinfo" in
        *Kali2* | *Kali* | *Parrot* | *Debian* | *Ubuntu*)
            apt-get update
            apt-get install -y cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox-esr
            ;;
        *Arch* | *Manjaro*)
            pacman -Syu
            for pkg_name in cmake python3 python-xvfbwrapper python-pip python-netaddr firefox; do
                pacman -S --noconfirm "${pkg_name}"
            done
            ;;
        *Alpine*)
            apk update
            apk add cmake python3 xvfb py-pip py-netaddr python3-dev firefox-esr
            wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://alpine-pkgs.sgerrand.com/sgerrand.rsa.pub
            wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.30-r0/glibc-2.30-r0.apk
            wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.30-r0/glibc-bin-2.30-r0.apk
            apk add glibc-2.30-r0.apk
            apk add glibc-bin-2.30-r0.apk
            apk add firefox-esr=60.9.0-r0
            ;;
        CentOS.*7* | Rocky.Linux8* )
            yum install -y python3 xorg-x11-server-Xvfb python3-pip python3-netaddr firefox
            for pkg_name in gcc cmake python3-devel; do
                yum list installed 2>/dev/null | grep -q "^${pkg_name}\."
                if [ $? -eq 1 ]; then
                    yum install -y ${pkg_name}
                fi
            done
            ;;
        *)
            echo "[Error]: ${osinfo} is not supported by this setup script."
            exit 1
    esac
}

# Global Variables
userid=$(id -u)
osinfo=$(lsb_release -sd 2>/dev/null || grep ^PRETTY_NAME /etc/os-release 2>/dev/null | cut -d'"' -f2)

if [ -f /etc/issue ];
then
  if [[ `cat /etc/issue | cut -d" " -f3 | head -n1 | grep "Alpine"` ]]; then
    osinfo="Alpine"
  fi
fi

if [ -f /etc/redhat-release ];
then
  if [[ `cat /etc/redhat-release | grep "CentOS Linux release 7\.[0-9]\.[0-9]\+ (Core)"` ]]; then
    osinfo="CentOS7"
  fi

  if [[ `cat /etc/redhat-release | grep "Rocky Linux release 8\.[0-9]"` ]]; then
    osinfo="RockyLinux8"
  fi
fi

# Check if the script is running as root
if [ "${userid}" != '0' ]; then
    echo '[Error]: You must run this setup script with root privileges.'
    exit 1
fi

# Setting environment variables
export TERM=linux

# Clear Terminal
clear

# Print Title
printf "
#######################################################################
#                          EyeWitness Setup                           #
#######################################################################

"

# Install EyeWitness dependencies
install_dependencies

# Download and set up GeckoDriver
geckodriver_x86_64='https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz'
geckodriver_x86_32='https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux32.tar.gz'

cd ../bin/

MACHINE_TYPE=$(uname -m)

if [ ${MACHINE_TYPE} == 'x86_64' ]; then
    wget -q ${geckodriver_x86_64}
    tar -xvf geckodriver-v0.32.0-linux64.tar.gz -C /usr/bin
    rm -f geckodriver-v0.32.0-linux64.tar.gz
else
    wget -q ${geckodriver_x86_32}
    tar -xvf geckodriver-v0.32.0-linux32.tar.gz -C /usr/bin
    rm -f geckodriver-v0.32.0-linux32.tar.gz
fi
cd ..

# Finish Message
printf "
[*] Setup script completed successfully, enjoy EyeWitness! :)
[*] Be sure to check out Red Siege!
[*] https://www.redsiege.com
"
