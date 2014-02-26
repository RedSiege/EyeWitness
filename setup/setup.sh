#!/bin/bash

# Check to make sure you are root!
# Thanks to @themightyshiv for helping to get a decent setup script out
uid=`id -u`
if [ "${uid}" != '0' ]; then
  echo ' [Error]: You must run this setup with root privileges.'
  exit 1
fi

apt-get install python-pip
pip install Ghost.py
