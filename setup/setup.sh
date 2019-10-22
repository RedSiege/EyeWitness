#!/bin/bash

# Global Variables
userid=`id -u`
osinfo=`cat /etc/issue|cut -d" " -f1|head -n1`
eplpkg='http://linux.mirrors.es.net/fedora-epel/6/i386/epel-release-6-8.noarch.rpm'

# Setting environment variables
export TERM=linux

# Clear Terminal (For Prettyness)
clear

# Print Title
echo '#######################################################################'
echo '#                          EyeWitness Setup                           #'
echo '#######################################################################'
echo

# Check to make sure you are root!
# Thanks to @themightyshiv for helping to get a decent setup script out
if [ "${userid}" != '0' ]; then
  echo '[Error]: You must run this setup script with root privileges.'
  echo
  exit 1
fi
#Support for kali 2 and kali rolling
if [[ `(lsb_release -sd || grep ^PRETTY_NAME /etc/os-release) 2>/dev/null | grep "Kali GNU/Linux.*\(2\|Rolling\)"` ]]; then
  osinfo="Kali2"
fi

if [[ `(lsb_release -sd || grep ^PRETTY_NAME /etc/os-release) 2>/dev/null | grep "Parrot GNU/Linux.*\(4\)"` ]]; then
  osinfo="Parrot"
fi

# make sure we run from this directory
pushd . > /dev/null && cd "$(dirname "$0")"

# OS Specific Installation Statement
case ${osinfo} in
  # Kali 2 dependency Install
  Kali2)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python-netaddr python3-dev tesseract-ocr firefox-esr
    echo '[*] Upgrading paramiko'
    python3 -m pip install --upgrade paramiko
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyasn1
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install beautifulsoup4
    python3 -m pip install pytesseract
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
      tar -xvf geckodriver-v0.24.0-linux64.tar.gz
      rm geckodriver-v0.24.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux32.tar.gz
      tar -xvf geckodriver-v0.24.0-linux32.tar.gz
      rm geckodriver-v0.24.0-linux32.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    fi
    cd ..
  ;;
  # Kali Dependency Installation
  Kali)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python-netaddr python3-dev tesseract-ocr firefox-esr
    echo '[*] Upgrading paramiko'
    python3 -m pip install --upgrade paramiko
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyasn1
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install beautifulsoup4
    python3 -m pip install pytesseract
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
      tar -xvf geckodriver-v0.24.0-linux64.tar.gz
      rm geckodriver-v0.24.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux32.tar.gz
      tar -xvf geckodriver-v0.24.0-linux32.tar.gz
      rm geckodriver-v0.24.0-linux32.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    fi
    cd ..
  ;;
   # Parrot Dependency Installation
  Parrot)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python-netaddr python3-dev tesseract-ocr firefox-esr
    echo '[*] Upgrading paramiko'
    python3 -m pip install --upgrade paramiko
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyasn1
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install beautifulsoup4
    python3 -m pip install pytesseract
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
      tar -xvf geckodriver-v0.24.0-linux64.tar.gz
      rm geckodriver-v0.24.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux32.tar.gz
      tar -xvf geckodriver-v0.24.0-linux32.tar.gz
      rm geckodriver-v0.24.0-linux32.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    fi
    cd ..
  ;;
  # Debian 7+ Dependency Installation
  Debian)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python-netaddr python3-dev tesseract-ocr firefox-esr
    echo '[*] Upgrading paramiko'
    python3 -m pip install --upgrade paramiko
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyasn1
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install beautifulsoup4
    python3 -m pip install pytesseract
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
      tar -xvf geckodriver-v0.24.0-linux64.tar.gz
      rm geckodriver-v0.24.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux32.tar.gz
      tar -xvf geckodriver-v0.24.0-linux32.tar.gz
      rm geckodriver-v0.24.0-linux32.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    fi
    cd ..
  ;;
  # Ubuntu (tested in 13.10) Dependency Installation
  Ubuntu)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python-netaddr python3-dev tesseract-ocr firefox x11-utils
    pip3 install --upgrade pip
    echo '[*] Upgrading paramiko'
    python3 -m pip install --upgrade paramiko
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyasn1
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install beautifulsoup4
    python3 -m pip install pytesseract
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz
      tar -xvf geckodriver-v0.26.0-linux64.tar.gz
      rm geckodriver-v0.26.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux32.tar.gz
      tar -xvf geckodriver-v0.26.0-linux32.tar.gz
      rm geckodriver-v0.26.0-linux32.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    fi
    cd ..
  ;;
  # Arch or Manjaro Dependency Installation
  Arch | Manjaro)
    pacman -Syu
    echo '[*] Installing Arch Dependencies'
    pacman -S cmake python3 python-xvfbwrapper python-pip python-netaddr firefox
    echo '[*] Upgrading paramiko'
    python3 -m pip install --upgrade paramiko
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyasn1
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install beautifulsoup4
    python3 -m pip install pytesseract
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
      tar -xvf geckodriver-v0.24.0-linux64.tar.gz
      rm geckodriver-v0.24.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux32.tar.gz
      tar -xvf geckodriver-v0.24.0-linux32.tar.gz
      rm geckodriver-v0.24.0-linux32.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    fi
    cd ..
  ;;
  # Notify Manual Installation Requirement And Exit
  *)
    echo "[Error]: ${osinfo} is not supported by this setup script."
    echo
    popd > /dev/null
    exit 1
esac

# Finish Message
popd > /dev/null
echo '[*] Setup script completed successfully, enjoy EyeWitness! :)'
echo '[*] Be sure to check out FortyNorth Security!'
echo '[*] https://www.fortynorthsecurity.com'
echo
