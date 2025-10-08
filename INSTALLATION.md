# EyeWitness Installation Guide - Virtual Environment Edition

## Overview

EyeWitness now uses **Python virtual environments** for all installations, providing:
- ✅ **Zero PEP 668 conflicts** - Completely bypasses modern Python restrictions
- ✅ **No system package conflicts** - Isolated Python environment
- ✅ **Cross-platform consistency** - Same approach on Windows, Linux, macOS
- ✅ **Production ready** - Automatic error handling and rollback
- ✅ **Easy cleanup** - Delete eyewitness-venv/ to remove completely

## Installation Methods

### 🐧 Linux/macOS Installation

```bash
# 1. Clone or navigate to EyeWitness directory
cd EyeWitness/setup

# 2. Run setup script (requires sudo for system packages)
sudo ./setup.sh

# 3. Test installation
cd ..
./eyewitness.sh --single https://example.com
```

**What gets installed:**
- **Virtual environment** at `eyewitness-venv/`
- System packages: Chromium browser, ChromeDriver, Xvfb (virtual display)
- Python packages in virtual environment: selenium, netaddr, psutil, etc.
- Helper scripts: `eyewitness.sh`, `activate-eyewitness.sh`

### 🪟 Windows Installation

```powershell
# 1. Open PowerShell as Administrator
# 2. Navigate to EyeWitness directory
cd path\to\EyeWitness\setup

# 3. Run setup script
.\setup.ps1

# 4. Test installation
cd ..
.\eyewitness.bat --single https://example.com
```

**What gets installed:**
- **Virtual environment** at `eyewitness-venv\`
- System components: Chrome browser, ChromeDriver
- Python packages in virtual environment: selenium, netaddr, psutil, etc.
- Helper scripts: `eyewitness.bat`, `eyewitness.ps1`, `activate-eyewitness.bat`

## Usage Methods

### Method 1: Helper Scripts (Recommended)

**Linux/macOS:**
```bash
./eyewitness.sh -f urls.txt
./eyewitness.sh --single https://example.com
```

**Windows:**
```powershell
.\eyewitness.bat -f urls.txt
.\eyewitness.ps1 --single https://example.com
```

### Method 2: Manual Activation

**Linux/macOS:**
```bash
# Activate virtual environment
source activate-eyewitness.sh
# OR manually: source eyewitness-venv/bin/activate

# Run EyeWitness
python Python/EyeWitness.py -f urls.txt

# Deactivate when done
deactivate
```

**Windows:**
```batch
REM Activate virtual environment
activate-eyewitness.bat
REM OR manually: eyewitness-venv\Scripts\activate.bat

REM Run EyeWitness
python Python\EyeWitness.py -f urls.txt

REM Deactivate when done
deactivate
```

## File Structure

After installation, your directory structure will be:

```
EyeWitness/
├── eyewitness-venv/          # Virtual environment (Python packages)
│   ├── bin/activate          # Linux/macOS activation
│   └── Scripts/activate.bat  # Windows activation
├── Python/
│   └── EyeWitness.py         # Main script
├── setup/
│   ├── setup.sh              # Linux/macOS setup
│   ├── setup.ps1             # Windows setup
│   └── requirements.txt      # Python dependencies
├── eyewitness.sh             # Linux/macOS helper script
├── eyewitness.bat            # Windows batch helper
├── eyewitness.ps1            # Windows PowerShell helper
└── activate-eyewitness.*     # Activation helpers
```

## Troubleshooting

### Setup Script Failures

**Virtual environment creation failed:**
```bash
# Check Python version (requires 3.7+)
python --version
python3 --version

# Ensure venv module is available
python -m venv --help
```

**System package installation failed:**
```bash
# Linux: Update package cache
sudo apt update

# Manually install missing packages
sudo apt install python3-venv python3-dev chromium-browser
```

**Permission errors:**
```bash
# Ensure you're running with proper privileges
sudo ./setup.sh    # Linux/macOS
# Run PowerShell as Administrator (Windows)
```

### Runtime Issues

**Virtual environment not found:**
```bash
# Re-run setup script
cd setup
sudo ./setup.sh  # Linux/macOS
.\setup.ps1       # Windows (as Administrator)
```

**Python package import errors:**
```bash
# Check virtual environment
source eyewitness-venv/bin/activate  # Linux/macOS
eyewitness-venv\Scripts\activate.bat # Windows

# Verify packages
python -c "import selenium; print('OK')"
```

**Browser/ChromeDriver not found:**
```bash
# Re-run setup script - it installs browsers automatically
cd setup
sudo ./setup.sh  # Linux/macOS
.\setup.ps1       # Windows
```

## Advanced Usage

### Force Reinstallation

**Linux/macOS:**
```bash
# Remove virtual environment
rm -rf eyewitness-venv/

# Re-run setup
cd setup
sudo ./setup.sh
```

**Windows:**
```powershell
# Remove virtual environment
Remove-Item -Recurse -Force eyewitness-venv\

# Re-run setup with force flag
cd setup
.\setup.ps1 -Force
```

### Manual Package Installation

If you need to add packages to the virtual environment:

```bash
# Activate virtual environment
source eyewitness-venv/bin/activate  # Linux/macOS
eyewitness-venv\Scripts\activate.bat # Windows

# Install additional packages
pip install package-name

# Deactivate
deactivate
```

### Cleanup

To completely remove EyeWitness virtual environment:

```bash
# Remove virtual environment
rm -rf eyewitness-venv/           # Linux/macOS
Remove-Item -Recurse eyewitness-venv\  # Windows PowerShell

# Remove helper scripts (optional)
rm eyewitness.sh activate-eyewitness.sh      # Linux/macOS
Remove-Item eyewitness.bat, eyewitness.ps1  # Windows
```

## Benefits of Virtual Environment Approach

### For Users
- **Zero conflicts** with system Python packages
- **No PEP 668 issues** on modern Linux distributions
- **Easy to remove** - just delete one directory
- **Consistent behavior** across all platforms
- **Production ready** - robust error handling

### For Developers
- **Reproducible environment** - same packages everywhere
- **Version pinning** - exact dependency versions
- **Isolated testing** - doesn't affect system Python
- **Easy debugging** - clear separation of concerns

## Migration from Old Installation

If you have an old EyeWitness installation:

1. **Backup any custom configurations**
2. **Remove old Python packages** (optional):
   ```bash
   pip uninstall selenium netaddr psutil rapidfuzz pyvirtualdisplay
   ```
3. **Run new setup script** to create virtual environment
4. **Test with helper scripts** instead of direct Python calls

Your existing scan results and configurations will work unchanged.

## Support

For issues with the virtual environment installation:

1. **Check system requirements** - Python 3.7+ with venv module
2. **Verify privileges** - setup scripts need admin/root access
3. **Review error messages** - scripts provide detailed error information
4. **Try force reinstall** - delete eyewitness-venv/ and re-run setup
5. **Check dependencies** - ensure system packages installed correctly

The virtual environment approach is designed to be bulletproof across platforms while maintaining the full functionality of EyeWitness.