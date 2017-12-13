#!/bin/bash

# python-qt5
brew install qt
brew install sip
brew install pyqt

# tesseract
brew install tesseract

# python libs
pip install netaddr
pip install fuzzywuzzy
pip install selenium
pip install python-Levenshtein
pip install pyasn1 --upgrade
pip install pyvirtualdisplay
pip install pytesseract
pip install bs4


# rdpy
git clone https://github.com/vyrus001/rdpy
cd rdpy
python setup.py install
cd ..
rm -rf rdpy

# phantomJS and geckodriver
brew install phantomjs
brew install geckodriver
