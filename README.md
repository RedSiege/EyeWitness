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
- **Lightweight installation** - Simple 2-package install on most platforms

## 📦 Installation Options

> **Note**: Docker support is currently in development. Please use native installation options below for now.

### 🪟 Windows Installation
**Simple automated setup with PowerShell:**

```powershell
# 1. Open PowerShell as Administrator
# 2. Navigate to EyeWitness directory
cd path\to\EyeWitness\setup

# 3. Run the setup script
.\setup.ps1

# 4. Test the installation
cd ..\Python
python EyeWitness.py --single https://example.com
```

**What gets installed:**
- Python dependencies (selenium, etc.)
- Google Chrome browser (if not present)
- ChromeDriver for automation
- Tab completion support

### 🐧 Linux Installation
**One-line setup for most distributions:**

```bash
# 1. Navigate to setup directory
cd EyeWitness/setup

# 2. Run the setup script
sudo ./setup.sh

# 3. Test the installation
cd ../Python
python3 EyeWitness.py --single https://example.com
```

**What gets installed:**
- Python packages via system package manager (avoids PEP 668 issues)
- Chromium browser and ChromeDriver
- Virtual display support (xvfb)
- Tab completion support

**Supported Linux Distributions:**
- Ubuntu 20.04+ / Linux Mint
- Debian 10+ / Kali Linux  
- CentOS 8+ / RHEL / Rocky Linux
- Arch Linux / Manjaro
- Alpine Linux

### 🍎 macOS Installation
**Homebrew-based setup:**

```bash
# 1. Install Chrome via Homebrew
brew install --cask google-chrome

# 2. Navigate to setup directory and run setup
cd EyeWitness/setup
sudo ./setup.sh

# 3. Test the installation
cd ../Python
python3 EyeWitness.py --single https://example.com
```

**What gets installed:**
- Python dependencies via pip
- Chrome browser (via Homebrew)
- ChromeDriver for automation

## 🎯 Usage Examples

### 💻 Native Usage (Linux/Windows/macOS)
After running the setup script:

```bash
cd EyeWitness/Python

# Single website
python3 EyeWitness.py --single https://example.com

# URL list from file  
python3 EyeWitness.py -f urls.txt

# Nmap XML scan results
python3 EyeWitness.py -x nmap_scan.xml

# Custom output directory
python3 EyeWitness.py -f urls.txt -d /path/to/output

# Performance tuning for large scans
python3 EyeWitness.py -f large_list.txt --threads 20 --timeout 10

# Nmap/Nessus XML
./EyeWitness.py -x nmap_scan.xml
```

### Configuration Files
```bash
# Create a sample config file
./EyeWitness.py --create-config

# Use a config file
./EyeWitness.py -f urls.txt --config ~/.eyewitness/config.json
```

### URL Validation
```bash
# Validate URLs without taking screenshots
./EyeWitness.py -f urls.txt --validate-urls

# Skip validation (use with caution)
./EyeWitness.py -f urls.txt --skip-validation
```

### Advanced Options
```bash
# Adjust threads based on your system (default: auto-detected)
./EyeWitness.py -f urls.txt --threads 5

# Increase timeout for slow connections
./EyeWitness.py -f urls.txt --timeout 30

# Add delays and jitter
./EyeWitness.py -f urls.txt --delay 2 --jitter 5

# Use proxy
./EyeWitness.py -f urls.txt --proxy-ip 127.0.0.1 --proxy-port 8080

# Custom output directory
./EyeWitness.py -f urls.txt -d /path/to/output

# Resume a previous scan
./EyeWitness.py --resume /path/to/output/ew.db
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
- Linux: `sudo apt install chromium-browser chromium-chromedriver`
- Windows: Navigate to setup directory and run `.\setup.ps1` as Administrator
- macOS: `brew install --cask google-chrome`

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

- Python 3.7+
- Chromium browser
- ChromeDriver (automatically installed by setup script)

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