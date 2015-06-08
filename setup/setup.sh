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
    apt-get update
    apt-get dist-upgrade
    echo '[*] Installing Kali Dependencies'
    apt-get install -y python-qt4 python-pip xvfb python-netaddr python-dev
    echo '[*] Installing RDPY'
    git clone https://github.com/ChrisTruncer/rdpy.git
    cd rdpy
    python setup.py install
    cd ..
    rm -rf rdpy
    echo '[*] Installing Python Modules'
    pip install fuzzywuzzy
    pip install selenium
    pip install python-Levenshtein
    pip install pyasn1 --upgrade
    pip install pyvirtualdisplay
    cd ../bin/
    wget http://www.christophertruncer.com/InstallMe/phantomjs
    chmod +x phantomjs
    cd ..
  ;;
  # Debian 7+ Dependency Installation
  Debian)
    apt-get update
    apt-get dist-upgrade
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake qt4-qmake python xvfb python-qt4 python-pip python-netaddr python-dev
    echo '[*] Installing RDPY'
    git clone https://github.com/ChrisTruncer/rdpy.git
    cd rdpy
    python setup.py install
    cd ..
    rm -rf rdpy
    echo
    echo '[*] Installing Python Modules'
    pip install python_qt_binding
    pip install fuzzywuzzy
    pip install selenium
    pip install python-Levenshtein
    pip install pyasn1
    pip install pyvirtualdisplay
    echo
    cd ../bin/
    wget -O phantomjs http://www.christophertruncer.com/InstallMe/phantom_deb
    chmod +x phantomjs
    cd ..
  ;;
  # Ubuntu (tested in 13.10) Dependency Installation
  Ubuntu)
    apt-get update
    apt-get dist-upgrade
    echo '[*] Installing Ubuntu Dependencies'
    apt-get install -y cmake qt4-qmake python python-qt4 python-pip xvfb python-netaddr python-dev
    echo '[*] Installing RDPY'
    git clone https://github.com/ChrisTruncer/rdpy.git
    cd rdpy
    python setup.py install
    cd ..
    rm -rf rdpy
    echo
    echo '[*] Installing Python Modules'
    pip install python_qt_binding
    pip install fuzzywuzzy
    pip install selenium
    pip install python-Levenshtein
    pip install pyasn1
    pip install pyvirtualdisplay
    echo
    cd ../bin/
    wget -O phantomjs http://www.christophertruncer.com/InstallMe/phantom_ubu
    chmod +x phantomjs
    cd ..
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
                python-argparse xvfb python-netaddr python-dev
    echo
    echo '[*] Installing RDPY'
    git clone https://github.com/ChrisTruncer/rdpy.git
    cd rdpy
    python setup.py install
    cd ..
    rm -rf rdpy
    echo '[*] Installing Python Modules'
    pip install python_qt_binding
    pip install fuzzywuzzy
    pip install selenium
    pip install python-Levenshtein
    pip install pyasn1
    pip install pyvirtualdisplay
    echo
    cd ../bin/
    wget http://www.christophertruncer.com/InstallMe/phantomjs
    chmod +x phantomjs
    cd ..
  ;;
  # Notify Manual Installation Requirement And Exit
  *)
    echo "[Error]: ${OS} is not supported by this setup script."
    echo
    exit 1
esac

# Finish Message
echo '[*] Setup script completed successfully, enjoy EyeWitness! :)'
echo
