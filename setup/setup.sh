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
    echo '[*] Installing Kali2 Dependencies'
    apt-get install -y cmake qt4-qmake python xvfb python-qt4 python-pip python-netaddr python-dev tesseract-ocr
    echo '[*] Upgrading paramiko'
    pip install --upgrade paramiko
    echo '[*] Installing RDPY'
    git clone https://github.com/ChrisTruncer/rdpy.git
    cd rdpy
    python setup.py install
    cd ..
    rm -rf rdpy
    echo '[*] Installing Python Modules'
    pip install fuzzywuzzy
    pip install selenium --upgrade
    pip install python-Levenshtein
    pip install pyasn1 --upgrade
    pip install pyvirtualdisplay
    pip install pytesseract
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget -O phantomjs https://www.christophertruncer.com/InstallMe/kali2phantomjs
      wget https://github.com/mozilla/geckodriver/releases/download/v0.22.0/geckodriver-v0.22.0-linux64.tar.gz
      tar -xvf geckodriver-v0.22.0-linux64.tar.gz
      rm geckodriver-v0.22.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      rm /usr/bin/geckodriver
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    else
      wget -O phantomjs https://www.christophertruncer.com/InstallMe/phantom32kali2
      wget https://github.com/mozilla/geckodriver/releases/download/v0.22.0/geckodriver-v0.22.0-linux32.tar.gz
      tar -xvf geckodriver-v0.22.0-linux32.tar.gz
      rm geckodriver-v0.22.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      rm /usr/bin/geckodriver
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
    fi
    chmod +x phantomjs
    cd ..
  ;;
  # Kali Dependency Installation
  Kali)
    apt-get update
    echo '[*] Installing Kali Dependencies'
    apt-get install -y python-qt4 python-pip xvfb python-netaddr python-dev tesseract-ocr
    echo '[*] Upgrading paramiko'
    pip install --upgrade paramiko
    echo '[*] Installing RDPY'
    git clone https://github.com/ChrisTruncer/rdpy.git
    cd rdpy
    python setup.py install
    cd ..
    rm -rf rdpy
    echo '[*] Installing Python Modules'
    pip install fuzzywuzzy
    pip install selenium --upgrade
    pip install python-Levenshtein
    pip install pyasn1 --upgrade
    pip install pyvirtualdisplay
    pip install pytesseract
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget -O phantomjs https://www.christophertruncer.com/InstallMe/phantomjs
    else
      wget -O phantomjs https://www.christophertruncer.com/InstallMe/kali32phantomjs
    fi
    chmod +x phantomjs
    cd ..
  ;;
   # Parrot Dependency Installation
  Parrot)
    apt-get update
    echo '[*] Installing Parrot Dependencies'
    apt-get install -y python-qt4 python-pip xvfb python-netaddr python-dev tesseract-ocr
    echo '[*] Upgrading paramiko'
    pip install --upgrade paramiko
    echo '[*] Installing RDPY'
    git clone https://github.com/ChrisTruncer/rdpy.git
    cd rdpy
    python setup.py install
    cd ..
    rm -rf rdpy
    echo '[*] Installing Python Modules'
    pip install fuzzywuzzy
    pip install selenium --upgrade
    pip install python-Levenshtein
    pip install pyasn1 --upgrade
    pip install pyvirtualdisplay
    pip install pytesseract
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget -O phantomjs https://www.christophertruncer.com/InstallMe/phantomjs
    else
      wget -O phantomjs https://www.christophertruncer.com/InstallMe/kali32phantomjs
    fi
    chmod +x phantomjs
    cd ..
  ;;
  # Debian 7+ Dependency Installation
  Debian)
    apt-get update
    echo '[*] Installing Debian Dependencies'
    apt-get install -y cmake qt4-qmake python xvfb python-qt4 python-pip python-netaddr python-dev tesseract-ocr
    echo '[*] Upgrading paramiko'
    pip install --upgrade paramiko
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
    pip install selenium --upgrade
    pip install python-Levenshtein
    pip install pyasn1
    pip install pyvirtualdisplay
    pip install beautifulsoup4
    pip install pytesseract
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36" https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2
      wget https://github.com/mozilla/geckodriver/releases/download/v0.22.0/geckodriver-v0.22.0-linux64.tar.gz
      tar -xvf geckodriver-v0.22.0-linux64.tar.gz
      rm geckodriver-v0.22.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      rm /usr/bin/geckodriver
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
      tar -xvf phantomjs-2.1.1-linux-x86_64.tar.bz2
      cd phantomjs-2.1.1-linux-x86_64/bin/
      mv phantomjs ../../
      cd ../..
      rm -rf phantomjs-2.1.1-linux-x86_64
      rm phantomjs-2.1.1-linux-x86_64.tar.bz2
    else
      wget --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36" https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-i686.tar.bz2
      wget https://github.com/mozilla/geckodriver/releases/download/v0.22.0/geckodriver-v0.22.0-linux32.tar.gz
      tar -xvf geckodriver-v0.22.0-linux32.tar.gz
      rm geckodriver-v0.22.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      rm /usr/bin/geckodriver
      ln -s /usr/sbin/geckodriver /usr/bin/geckodriver
      tar -xvf phantomjs-2.1.1-linux-i686.tar.bz2
      cd phantomjs-2.1.1-linux-i686/bin/
      mv phantomjs ../../
      cd ../..
      rm -rf phantomjs-2.1.1-linux-i686
      rm phantomjs-2.1.1-linux-i686.tar.bz2
    fi
    cd ..
  ;;
  # Ubuntu (tested in 13.10) Dependency Installation
  Ubuntu)
    apt-get update
    echo '[*] Installing Ubuntu Dependencies'
    apt-get install -y cmake qt4-qmake python python-qt4 python-pip xvfb python-netaddr python-dev libffi-dev libssl-dev tesseract-ocr
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
    pip install selenium --upgrade
    pip install python-Levenshtein
    pip install pyasn1
    pip install pyvirtualdisplay
    pip install beautifulsoup4
    pip install pytesseract
    pip install enum34
    pip install ipaddress
    pip install asn1crypto
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36" https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2
      wget https://github.com/mozilla/geckodriver/releases/download/v0.22.0/geckodriver-v0.22.0-linux64.tar.gz
      tar -xvf geckodriver-v0.22.0-linux64.tar.gz
      rm geckodriver-v0.22.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      tar -xvf phantomjs-2.1.1-linux-x86_64.tar.bz2
      cd phantomjs-2.1.1-linux-x86_64/bin/
      mv phantomjs ../../
      cd ../..
      rm -rf phantomjs-2.1.1-linux-x86_64
      rm phantomjs-2.1.1-linux-x86_64.tar.bz2
    else
      wget --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36" https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-i686.tar.bz2
      wget https://github.com/mozilla/geckodriver/releases/download/v0.22.0/geckodriver-v0.22.0-linux32.tar.gz
      tar -xvf geckodriver-v0.22.0-linux32.tar.gz
      rm geckodriver-v0.22.0-linux64.tar.gz
      mv geckodriver /usr/sbin
      tar -xvf phantomjs-2.1.1-linux-i686.tar.bz2
      cd phantomjs-2.1.1-linux-i686/bin/
      mv phantomjs ../../
      cd ../..
      rm -rf phantomjs-2.1.1-linux-i686
      rm phantomjs-2.1.1-linux-i686.tar.bz2
    fi
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
      popd > /dev/null
      exit 1
    fi
    echo '[*] Installing CentOS Dependencies'
    yum install cmake python python-pip PyQt4 PyQt4-webkit \
                python-argparse xvfb python-netaddr python-dev tesseract-ocr
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
    pip install selenium --upgrade
    pip install python-Levenshtein
    pip install pyasn1
    pip install pyvirtualdisplay
    pip install beautifulsoup4
    pip install pytesseract
    echo
    cd ../bin/
    MACHINE_TYPE=`uname -m`
    if [ ${MACHINE_TYPE} == 'x86_64' ]; then
      wget --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36" https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2
      tar -xvf phantomjs-2.1.1-linux-x86_64.tar.bz2
      cd phantomjs-2.1.1-linux-x86_64/bin/
      mv phantomjs ../../
      cd ../..
      rm -rf phantomjs-2.1.1-linux-x86_64
      rm phantomjs-2.1.1-linux-x86_64.tar.bz2
    else
      wget --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36" https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-i686.tar.bz2
      tar -xvf phantomjs-2.1.1-linux-i686.tar.bz2
      cd phantomjs-2.1.1-linux-i686/bin/
      mv phantomjs ../../
      cd ../..
      rm -rf phantomjs-2.1.1-linux-i686
      rm phantomjs-2.1.1-linux-i686.tar.bz2
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
