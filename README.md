# EyeWitness

EyeWitness is designed to take screenshots of websites, provide server header info, and identify default credentials if known.

## Key Features
- **Cross-platform support** - Windows, Linux, and macOS
- **Adaptive resource management** - Automatically adjusts to system capabilities
- **Configuration file support** - Save your preferred settings
- **URL validation** - Pre-flight checks to ensure URLs are valid
- **Progress tracking with ETA** - Know exactly when your scan will complete
- **Comprehensive error handling** - Actionable troubleshooting for every error
- **Multiple input formats** - Text files, Nmap XML, Nessus XML
- **Offline operation** - All dependencies bundled locally

## Installation

### Windows
1. Install Firefox if not already installed
2. Run PowerShell as Administrator
3. Navigate to the Python/setup directory
4. Run: `.\setup.ps1`

### Linux
1. Navigate to the Python/setup directory
2. Run: `./setup.sh`

**Supported Linux Distributions:**
- Kali Linux
- Debian 7+
- Ubuntu 18.04+
- CentOS 7/8
- Rocky Linux 8
- Arch Linux

### macOS
1. Install Firefox: `brew install --cask firefox`
2. Run: `./setup.sh`

## Usage

### Basic Usage
```bash
# Single URL
./EyeWitness.py --single http://example.com

# URL list from file
./EyeWitness.py -f urls.txt --web

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

**Firefox/Geckodriver not found:**
- Linux: `sudo apt install firefox-esr firefox-geckodriver`
- Windows: Re-run `setup.ps1` as Administrator
- macOS: `brew install --cask firefox`

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
- Firefox browser
- Geckodriver (automatically installed by setup script)

## Changes from Original

This fork includes significant modernization:
- Fixed deprecated Selenium APIs
- Replaced archived dependencies (fuzzywuzzy → rapidfuzz)
- Added comprehensive error handling
- Improved cross-platform support
- Added resource monitoring
- Removed Docker support (unmaintained)
- Added configuration file support
- Enhanced user experience

## Contact

**E-Mail:** GetOffensive [@] redsiege [dot] com

## License

EyeWitness is licensed under the GNU General Public License v3.0.