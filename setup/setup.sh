#!/bin/bash

# Global Variables
userid=`id -u`
osinfo=`cat /etc/issue|cut -d" " -f1|head -n1`

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
    apt-get install python-pip
    echo
    echo '[*] Installing Python Modules'
    pip install Ghost.py python_qt_binding
    echo
  ;;
  # Debian Dependency Installation
  Debian)
    echo '[*] Installing Debian Dependencies'
    apt-get install unzip cmake qt4-qmake python python-qt4 python-pip
    echo
    echo '[*] Installing Python Modules'
    pip install Ghost.py python_qt_binding
    echo
  ;;
  # Notify Manual Installation Requirement And Exit
  *)
    echo "[Error]: ${OS} is not supported by this setup script."
    echo '[Error]: To use EyeWitness, manually install python, PyQt4, and Ghost.py.'
    echo
    exit 1
esac

# Finish Message
echo '[*] Setup script completed successfully, enjoy EyeWitness! :)'
echo
