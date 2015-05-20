#!/bin/bash

# Global Variables
userid=`id -u`
osinfo=`cat /etc/issue|cut -d" " -f1|head -n1`
eplpkg='http://linux.mirrors.es.net/fedora-epel/6/i386/epel-release-6-8.noarch.rpm'

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

# OS Specific Installation Statement
case ${osinfo} in
  # Kali Dependency Installation
  Kali)
    echo '[*] Installing Kali Dependencies'
    apt-get install python-qt4 python-pip xvfb python-netaddr
    echo '[*] Installing Python Modules'
    pip install fuzzywuzzy
    pip install selenium
    pip install pyvirtualdisplay
    cd ../bin/
    wget http://www.christophertruncer.com/InstallMe/phantomjs
    cd ..
  ;;
  # Debian 7+ Dependency Installation
  Debian)
    echo '[*] Installing Debian Dependencies'
    apt-get install cmake qt4-qmake python xvfb python-qt4 python-pip python-netaddr
    echo
    echo '[*] Installing Python Modules'
    pip install python_qt_binding
    echo
    echo '[*] Cloning and installing Ghost'
    git clone https://github.com/ChrisTruncer/Ghost.py.git
    cd Ghost.py
    python setup.py install
    cd ..
    rm -rf Ghost.py
  ;;
  # Ubuntu (tested in 13.10) Dependency Installation
  Ubuntu)
    echo '[*] Installing Ubuntu Dependencies'
    apt-get install cmake qt4-qmake python python-qt4 python-pip xvfb python-netaddr
    echo
    echo '[*] Installing Python Modules'
    pip install python_qt_binding
    echo
    echo '[*] Cloning and installing Ghost'
    git clone https://github.com/ChrisTruncer/Ghost.py.git
    cd Ghost.py
    python setup.py install
    cd ..
    rm -rf Ghost.py
  ;;
  # CentOS 6.5+ Dependency Installation
  CentOS)
    echo '[Warning]: EyeWitness on CentOS Requires EPEL Repository!'
    read -p '[?] Install and Enable EPEL Repository? (y/n): ' epel
    if [ "${epel}" == 'y' ]; then
      rpm -ivh ${eplpkg}
    else
      echo '[!] User Aborted EyeWitness Installation.'
      exit 1
    fi
    echo '[*] Installing CentOS Dependencies'
    yum install cmake python python-pip PyQt4 PyQt4-webkit \
                python-argparse xvfb python-netaddr
    echo
    echo '[*] Installing Python Modules'
    pip install python_qt_binding
    echo
    echo '[*] Cloning and installing Ghost'
    git clone https://github.com/ChrisTruncer/Ghost.py.git
    cd Ghost.py
    python setup.py install
    cd ..
    rm -rf Ghost.py
  ;;
  # Notify Manual Installation Requirement And Exit
  *)
    echo "[Error]: ${OS} is not supported by this setup script."
    echo '[Error]: To use EyeWitness, manually install python, PyQt4.'
    echo '[Error]: Install ghost.py from https://github.com/ChrisTruncer/Ghost.py.git'
    echo
    exit 1
esac

# Finish Message
echo '[*] Setup script completed successfully, enjoy EyeWitness! :)'
echo
