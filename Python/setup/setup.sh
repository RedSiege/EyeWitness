#!/bin/bash

# Global Variables
userid=`id -u`
osinfo=`cat /etc/issue|cut -d" " -f1|head -n1`
distinfo=`cat /etc/issue|cut -d" " -f2|head -n1`
eplpkg='http://linux.mirrors.es.net/fedora-epel/6/i386/epel-release-6-8.noarch.rpm'
geckodriver_x86_64='https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz'
geckodriver_x86_32='https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux32.tar.gz'

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

if [[ `cat /etc/issue | cut -d" " -f3 | head -n1 | grep "Alpine"` ]]; then
  osinfo="Alpine"
fi

# make sure we run from this directory
pushd . > /dev/null && cd "$(dirname "$0")"

# OS Specific Installation Statement
case ${osinfo} in
  # Kali 2 dependency Install
  Kali2)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox-esr
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget ${geckodriver_x86_64}
      tar -xvf geckodriver-v0.26.0-linux64.tar.gz
      rm geckodriver-v0.26.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget ${geckodriver_x86_32}
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
  # Kali Dependency Installation
  Kali)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox-esr
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget ${geckodriver_x86_64}
      tar -xvf geckodriver-v0.26.0-linux64.tar.gz
      rm geckodriver-v0.26.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget ${geckodriver_x86_32}
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
   # Parrot Dependency Installation
  Parrot)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox-esr
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget ${geckodriver_x86_64}
      tar -xvf geckodriver-v0.26.0-linux64.tar.gz
      rm geckodriver-v0.26.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget ${geckodriver_x86_32}
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
  # Debian 7+ Dependency Installation
  Debian)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox-esr
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget ${geckodriver_x86_64}
      tar -xvf geckodriver-v0.26.0-linux64.tar.gz
      rm geckodriver-v0.26.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget ${geckodriver_x86_32}
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
  # Ubuntu (tested in 13.10) Dependency Installation
  Ubuntu)
    apt-get update
    echo '[*] Installing Ubuntu Dependencies'
    apt-get install -y cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox x11-utils
    pip3 install --upgrade pip
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget ${geckodriver_x86_64}
      tar -xvf geckodriver-v0.26.0-linux64.tar.gz
      rm geckodriver-v0.26.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      if [ -e /usr/bin/geckodriver ]
      then
      	rm /usr/bin/geckodriver
      fi
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget ${geckodriver_x86_32}
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
    for pkg_name in cmake python3 python-xvfbwrapper python-pip python-netaddr firefox; do
        pacman -S --noconfirm "${pkg_name}"
    done
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install netaddr
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget ${geckodriver_x86_64}
      tar -xvf geckodriver-v0.26.0-linux64.tar.gz
      rm geckodriver-v0.26.0-linux64.tar.gz
      mv geckodriver /usr/bin
    else
      wget ${geckodriver_x86_32}
      tar -xvf geckodriver-v0.26.0-linux32.tar.gz
      rm geckodriver-v0.26.0-linux32.tar.gz
      mv geckodriver /usr/bin
    fi
    cd ..
  ;;
  # Alpine Dependency Installation
  Alpine)
    apk update
    echo '[*] Installing Alpine Dependencies'
    apk add cmake python3 xvfb py-pip py-netaddr python3-dev firefox
    echo
    echo '[*] Installing Python Modules'
    python3 -m pip install fuzzywuzzy
    python3 -m pip install selenium --upgrade
    python3 -m pip install python-Levenshtein
    python3 -m pip install pyvirtualdisplay
    python3 -m pip install netaddr
    echo
    # from https://stackoverflow.com/questions/58738920/running-geckodriver-in-an-alpine-docker-container
    # Get all the prereqs
    wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://alpine-pkgs.sgerrand.com/sgerrand.rsa.pub
    wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.30-r0/glibc-2.30-r0.apk
    wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.30-r0/glibc-bin-2.30-r0.apk
    apk add glibc-2.30-r0.apk
    apk add glibc-bin-2.30-r0.apk

    # And of course we need Firefox if we actually want to *use* GeckoDriver
    apk add firefox-esr=60.9.0-r0

    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget ${geckodriver_x86_64}
      tar -xvf geckodriver-v0.26.0-linux64.tar.gz -C /usr/bin
      rm geckodriver-v0.26.0-linux64.tar.gz
    else
      wget ${geckodriver_x86_32}
      tar -xvf geckodriver-v0.26.0-linux32.tar.gz -C /usr/bin
      rm geckodriver-v0.26.0-linux32.tar.gz
    fi
    cd ..
  ;;
  # Notify Manual Installation Requirement And Exit
  *)
    case ${distinfo} in
    # Mint Dependency Installation
    Mint)
      apt-get update
      echo '[*] Installing Mint Dependencies'
      apt-get install -y cmake python3 xvfb python3-pip python3-netaddr python3-dev firefox x11-utils
      pip3 install --upgrade pip
      echo
      echo '[*] Installing Python Modules'
      python3 -m pip install fuzzywuzzy
      python3 -m pip install selenium --upgrade
      python3 -m pip install python-Levenshtein
      python3 -m pip install pyvirtualdisplay
      python3 -m pip install netaddr
      echo
      cd ../bin/
      MACHINE_TYPE=`uname -m`
      if [ ${MACHINE_TYPE} == 'x86_64' ]; then
        wget ${geckodriver_x86_64}
        tar -xvf geckodriver-v0.26.0-linux64.tar.gz
        rm geckodriver-v0.26.0-linux64.tar.gz
        mv geckodriver /usr/sbin
        if [ -e /usr/bin/geckodriver ]
        then
          rm /usr/bin/geckodriver
        fi
        ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
      else
        wget ${geckodriver_x86_32}
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
    *)
      echo "[Error]: ${osinfo} is not supported by this setup script."
      echo
      popd > /dev/null
      exit 1
  esac
esac

# Finish Message
popd > /dev/null
echo '[*] Setup script completed successfully, enjoy EyeWitness! :)'
echo '[*] Be sure to check out FortyNorth Security!'
echo '[*] https://www.fortynorthsecurity.com'
echo
