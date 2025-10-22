#!/bin/bash

echo "=== EyeWitness Dependency Check (Chromium Only) ==="
echo

# Check Chromium
echo -n "Chromium: "
chromium_found=false
for browser in chromium-browser chromium google-chrome; do
    if command -v $browser &> /dev/null; then
        echo "✓ Installed ($browser $(timeout 2 $browser --version 2>&1 | head -1 | cut -d' ' -f2 2>/dev/null || echo 'version unknown'))"
        chromium_found=true
        break
    fi
done

if [ "$chromium_found" = false ]; then
    echo "✗ NOT FOUND"
fi

# Check chromedriver
echo -n "ChromeDriver: "
chromedriver_found=false
for driver in chromedriver chromium-chromedriver; do
    if command -v $driver &> /dev/null; then
        echo "✓ Installed ($driver $($driver --version 2>&1 | head -1 | cut -d' ' -f2 2>/dev/null || echo 'version unknown'))"
        chromedriver_found=true
        break
    fi
done

if [ "$chromedriver_found" = false ]; then
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
echo "=== System Status ==="
echo
if [ "$chromium_found" = true ] && [ "$chromedriver_found" = true ]; then
    echo "✓ EyeWitness is ready to run!"
    echo
    echo "Test with:"
    echo "  cd Python && python3 EyeWitness.py --single https://example.com"
else
    echo "✗ Missing dependencies detected"
    echo
    echo "=== Quick Fix Commands ==="
    echo
    if [ "$chromium_found" = false ]; then
        echo "Install Chromium:"
        echo "  Ubuntu/Debian: sudo apt install chromium-browser"
        echo "  CentOS/RHEL: sudo yum install chromium"
        echo "  Arch: sudo pacman -S chromium"
    fi

    if [ "$chromedriver_found" = false ]; then
        echo
        echo "Install ChromeDriver:"
        echo "  Ubuntu/Debian: sudo apt install chromium-chromedriver"
        echo "  Or run: sudo ./setup.sh"
    fi
    
    echo
    echo "Complete setup:"
    echo "  sudo ./setup.sh"
fi