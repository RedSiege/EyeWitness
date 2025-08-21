# EyeWitness - Web Screenshot Tool

EyeWitness is designed to take screenshots of websites, provide server header info, and identify default credentials if known. **Now powered by Chromium browser for better reliability and easier installation.**

## 🚀 Key Features
- **Cross-platform support** - Windows, Linux, and macOS
- **Chromium-powered** - Reliable headless screenshots with Google Chrome/Chromium
- **Adaptive resource management** - Automatically adjusts to system capabilities
- **Configuration file support** - Save your preferred settings
- **URL validation** - Pre-flight checks to ensure URLs are valid
- **Progress tracking with ETA** - Know exactly when your scan will complete
- **Enhanced error handling** - Specific error types with actionable guidance
- **Multiple input formats** - Text files, Nmap XML, Nessus XML
- **Isolated virtual environment** - Zero system conflicts and PEP 668 bypass

## 🔒 Virtual Environment Architecture

EyeWitness now uses **Python virtual environments** for all installations, providing:

### ✅ **Key Benefits**
- **No system conflicts** - All Python packages installed in isolated environment
- **No PEP 668 issues** - Completely bypasses "externally-managed-environment" errors on Kali/modern Linux
- **Cross-platform consistency** - Same approach on Windows, Linux, and macOS
- **Easy cleanup** - Delete `eyewitness-venv/` directory to remove everything
- **Production ready** - Automatic error handling and rollback on failures

### 🚀 **How It Works**
1. **Setup creates virtual environment** - `eyewitness-venv/` directory with isolated Python
2. **Helper scripts handle activation** - No manual virtual environment management needed
3. **All packages installed in isolation** - Zero impact on your system Python
4. **Multiple execution methods** - Helper scripts, manual activation, or direct execution

### 📁 **File Structure After Installation**
```
EyeWitness/
├── eyewitness-venv/          # 🔒 Virtual environment (isolated Python packages)
├── eyewitness.sh/.bat        # 🚀 Helper scripts (auto-activate venv)
├── activate-eyewitness.*     # 🔧 Manual activation helpers
└── Python/EyeWitness.py     # 📜 Main script (runs in virtual environment)
```

## 📦 Installation Options

> **🔥 NEW**: EyeWitness now uses **Python virtual environments** for zero conflicts and bulletproof installation across all platforms!
>
> **Note**: Docker support is currently in development. Please use native installation options below for now.

### 🪟 Windows Installation
**Automated setup with Python virtual environment:**

```powershell
# 1. Open PowerShell as Administrator
# 2. Navigate to EyeWitness directory
cd path\to\EyeWitness\setup

# 3. Run the setup script (creates virtual environment)
.\setup.ps1

# 4. Test installation using helper script
cd ..
.\eyewitness.bat --single https://example.com
```

**What gets installed:**
- **🔒 Isolated Python virtual environment** (eyewitness-venv/)
- Python dependencies in virtual environment (selenium, etc.)
- Google Chrome browser (if not present)
- ChromeDriver for automation
- **📝 Helper scripts** for easy execution

**✨ Usage Options:**
- Direct execution: `.\eyewitness.bat [options]`
- PowerShell execution: `.\eyewitness.ps1 [options]`  
- Manual activation: `.\activate-eyewitness.bat`

### 🐧 Linux Installation
**Production-ready setup with Python virtual environment:**

```bash
# 1. Navigate to setup directory
cd EyeWitness/setup

# 2. Run the setup script (creates virtual environment)
sudo ./setup.sh

# 3. Test installation using helper script
cd ..
./eyewitness.sh --single https://example.com
```

**What gets installed:**
- **🔒 Isolated Python virtual environment** (eyewitness-venv/)
- All Python packages in virtual environment (completely bypasses PEP 668)
- Chromium browser and ChromeDriver via system packages
- Virtual display support (xvfb)
- **📝 Helper scripts** for easy execution

**✨ Usage Options:**
- Direct execution: `./eyewitness.sh [options]`
- Manual activation: `source activate-eyewitness.sh`
- Advanced: `source eyewitness-venv/bin/activate`

**🎯 Benefits:**
- ✅ **No PEP 668 conflicts** - Virtual environment bypasses all restrictions
- ✅ **No system package issues** - All Python deps isolated
- ✅ **Easy cleanup** - Just delete eyewitness-venv/ directory
- ✅ **Production ready** - Automatic rollback on installation failures

**Supported Linux Distributions:**
- Ubuntu 20.04+ / Linux Mint
- Debian 10+ / Kali Linux  
- CentOS 8+ / RHEL / Rocky Linux
- Arch Linux / Manjaro
- Alpine Linux

### 🍎 macOS Installation
**Homebrew-based setup with Python virtual environment:**

```bash
# 1. Install Chrome via Homebrew
brew install --cask google-chrome

# 2. Navigate to setup directory and run setup
cd EyeWitness/setup
sudo ./setup.sh

# 3. Test installation using helper script
cd ..
./eyewitness.sh --single https://example.com
```

**What gets installed:**
- **🔒 Isolated Python virtual environment** (eyewitness-venv/)
- Python dependencies in virtual environment
- Chrome browser (via Homebrew)
- ChromeDriver for automation
- **📝 Helper scripts** for easy execution

## 🎯 Usage Examples

> **💡 Important**: EyeWitness now uses **virtual environments**. Use the helper scripts below for automatic virtual environment activation, or manually activate as shown in the advanced section.

### 📱 **Easy Method - Helper Scripts (Recommended)**
After running the setup script, use the helper scripts that automatically handle virtual environment activation:

**🐧 Linux/macOS:**
```bash
# Single website
./eyewitness.sh --single https://example.com

# URL list from file  
./eyewitness.sh -f urls.txt

# Nmap XML scan results
./eyewitness.sh -x nmap_scan.xml

# Custom output directory
./eyewitness.sh -f urls.txt -d /path/to/output

# Performance tuning for large scans
./eyewitness.sh -f large_list.txt --threads 20 --timeout 10
```

**🪟 Windows:**
```powershell
# Single website
.\eyewitness.bat --single https://example.com

# URL list from file  
.\eyewitness.bat -f urls.txt

# Nmap XML scan results
.\eyewitness.ps1 -x nmap_scan.xml

# Custom output directory
.\eyewitness.bat -f urls.txt -d C:\path\to\output

# Performance tuning for large scans
.\eyewitness.bat -f large_list.txt --threads 20 --timeout 10
```

### 🛠️ **Advanced Method - Manual Virtual Environment**
For advanced users who want direct control over the virtual environment:

**🐧 Linux/macOS:**
```bash
# Activate virtual environment
source eyewitness-venv/bin/activate

# Run EyeWitness directly
python Python/EyeWitness.py --single https://example.com
python Python/EyeWitness.py -f urls.txt

# Deactivate when done
deactivate
```

**🪟 Windows:**
```powershell
# Activate virtual environment
eyewitness-venv\Scripts\activate.bat

# Run EyeWitness directly
python Python\EyeWitness.py --single https://example.com
python Python\EyeWitness.py -f urls.txt

# Deactivate when done
deactivate
```

### 📄 Configuration Files
**🐧 Linux/macOS:**
```bash
# Create a sample config file
./eyewitness.sh --create-config

# Use a config file
./eyewitness.sh -f urls.txt --config ~/.eyewitness/config.json
```

**🪟 Windows:**
```powershell
# Create a sample config file
.\eyewitness.bat --create-config

# Use a config file
.\eyewitness.bat -f urls.txt --config C:\Users\%USERNAME%\.eyewitness\config.json
```

### 🔍 URL Validation
**🐧 Linux/macOS:**
```bash
# Validate URLs without taking screenshots
./eyewitness.sh -f urls.txt --validate-urls

# Skip validation (use with caution)
./eyewitness.sh -f urls.txt --skip-validation
```

**🪟 Windows:**
```powershell
# Validate URLs without taking screenshots
.\eyewitness.bat -f urls.txt --validate-urls

# Skip validation (use with caution)
.\eyewitness.bat -f urls.txt --skip-validation
```

### ⚙️ Advanced Options
**🐧 Linux/macOS:**
```bash
# Adjust threads based on your system (default: auto-detected)
./eyewitness.sh -f urls.txt --threads 5

# Increase timeout for slow connections
./eyewitness.sh -f urls.txt --timeout 30

# Add delays and jitter
./eyewitness.sh -f urls.txt --delay 2 --jitter 5

# Use proxy
./eyewitness.sh -f urls.txt --proxy-ip 127.0.0.1 --proxy-port 8080

# Custom output directory
./eyewitness.sh -f urls.txt -d /path/to/output

# Resume a previous scan
./eyewitness.sh --resume /path/to/output/ew.db
```

**🪟 Windows:**
```powershell
# Adjust threads based on your system (default: auto-detected)
.\eyewitness.bat -f urls.txt --threads 5

# Increase timeout for slow connections
.\eyewitness.bat -f urls.txt --timeout 30

# Add delays and jitter
.\eyewitness.bat -f urls.txt --delay 2 --jitter 5

# Use proxy
.\eyewitness.bat -f urls.txt --proxy-ip 127.0.0.1 --proxy-port 8080

# Custom output directory
.\eyewitness.bat -f urls.txt -d C:\path\to\output

# Resume a previous scan
.\eyewitness.bat --resume C:\path\to\output\ew.db
```

### Performance Tuning
EyeWitness automatically detects your system resources and adjusts accordingly:
- Thread count based on CPU cores (2 × cores, max 20)
- Memory monitoring to prevent system overload
- Disk space checks before starting

## Configuration File Format

Create a config file to save your preferred settings:

```json
{
    "threads": 10,
    "timeout": 30,
    "delay": 0,
    "jitter": 0,
    "user_agent": "Custom User Agent",
    "proxy_ip": "127.0.0.1",
    "proxy_port": 8080,
    "output_dir": "./sessions",
    "prepend_https": false,
    "show_selenium": false,
    "resolve": false,
    "skip_validation": false,
    "results_per_page": 25,
    "max_retries": 2
}
```

## Troubleshooting

### Common Issues

**Chromium/ChromeDriver not found:**
- **All platforms**: Re-run the setup script - it installs browsers automatically
- Linux: `sudo ./setup.sh` in setup/ directory
- Windows: `.\setup.ps1` as Administrator in setup\ directory
- macOS: `sudo ./setup.sh` in setup/ directory (after `brew install --cask google-chrome`)

**Virtual environment issues:**
- Delete eyewitness-venv/ directory and re-run setup script
- Ensure Python 3.7+ is installed with venv module support
- Check that you ran setup script with proper Administrator/root privileges

**Connection timeouts:**
- Increase timeout: `--timeout 60`
- Check firewall settings
- Verify target is accessible

**High memory usage:**
- Reduce threads: `--threads 5`
- Process URLs in smaller batches
- Close other applications

**Permission errors:**
- Linux/macOS: Check file permissions
- Windows: Run as Administrator if needed

### Error Messages
All errors now include specific troubleshooting steps. For example:
- Timeout errors suggest proxy settings and timeout increases
- Connection errors provide firewall and network checks
- Resource errors show memory usage and recommendations

## Output

EyeWitness generates:
- `report.html` - Main report with screenshots
- `screens/` - Screenshot images
- `source/` - Page source code
- `ew.db` - SQLite database for resume capability

### Report Features
- Categorized results (High Value, CMS, Network Devices, etc.)
- Default credential detection
- Header analysis
- Searchable and sortable

## Requirements

- **Python 3.7+** with `venv` module support (standard in most Python installations)
- **Administrator/root privileges** for installation (system packages and virtual environment creation)
- **Internet connection** for package downloads
- **Chromium/Chrome browser** (automatically installed by setup script)
- **ChromeDriver** (automatically installed by setup script)

> **📝 Note**: The setup script handles all dependencies automatically. You just need Python 3.7+ and admin privileges.

## Changes from Original

This fork includes significant modernization:
- Fixed deprecated Selenium APIs
- Replaced archived dependencies (fuzzywuzzy → rapidfuzz)
- Added comprehensive error handling
- Improved cross-platform support
- Added resource monitoring
- Docker support in development
- Added configuration file support
- Enhanced user experience

## Contact

**E-Mail:** GetOffensive [@] redsiege [dot] com

## License

EyeWitness is licensed under the GNU General Public License v3.0.