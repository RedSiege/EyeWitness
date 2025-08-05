#!/bin/bash

echo "=== EyeWitness Dependency Check ==="
echo

# Check Firefox
echo -n "Firefox: "
if command -v firefox &> /dev/null; then
    echo "✓ Installed ($(firefox --version 2>&1 | head -1))"
else
    echo "✗ NOT FOUND"
fi

# Check geckodriver
echo -n "Geckodriver: "
if command -v geckodriver &> /dev/null; then
    echo "✓ Installed ($(geckodriver --version 2>&1 | head -1))"
else
    echo "✗ NOT FOUND"
fi

# Check Xvfb
echo -n "Xvfb: "
if command -v Xvfb &> /dev/null; then
    echo "✓ Installed"
else
    echo "✗ NOT FOUND"
fi

# Check Python packages
echo
echo "Python packages:"
echo -n "  - pyvirtualdisplay: "
python3 -c "import pyvirtualdisplay; print('✓ Installed')" 2>/dev/null || echo "✗ NOT FOUND"

echo -n "  - selenium: "
python3 -c "import selenium; print('✓ Installed')" 2>/dev/null || echo "✗ NOT FOUND"

echo -n "  - argcomplete: "
python3 -c "import argcomplete; print('✓ Installed')" 2>/dev/null || echo "✗ NOT FOUND"

# Check display
echo
echo -n "DISPLAY variable: "
if [ -n "$DISPLAY" ]; then
    echo "Set to '$DISPLAY'"
else
    echo "NOT SET (expected for headless)"
fi

echo
echo "=== Quick Fix Commands ==="
echo
if ! command -v firefox &> /dev/null; then
    echo "Install Firefox:"
    echo "  Ubuntu/Debian: sudo apt install -y firefox"
    echo "  CentOS/RHEL: sudo yum install -y firefox"
fi

if ! command -v geckodriver &> /dev/null; then
    echo
    echo "Install geckodriver:"
    echo "  Run: sudo /opt/tools/EyeWitness/setup/setup.sh"
fi

if ! command -v Xvfb &> /dev/null; then
    echo
    echo "Install Xvfb:"
    echo "  Ubuntu/Debian: sudo apt install -y xvfb"
    echo "  CentOS/RHEL: sudo yum install -y xorg-x11-server-Xvfb"
fi