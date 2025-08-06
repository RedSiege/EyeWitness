# EyeWitness Developer Reference

## Overview

EyeWitness is a cybersecurity reconnaissance tool designed for penetration testers and security professionals. It automates the process of taking screenshots of web applications, collecting server headers, identifying default credentials, and generating comprehensive HTML reports with visual evidence.

**Primary Purpose**: Authorized security assessments, red team operations, and network reconnaissance.

## Architecture Overview

### Platform Strategy
- **Python Implementation**: Cross-platform support for Linux/Unix (Kali, Debian, CentOS, Rocky Linux), Windows, and macOS
- **Docker Support**: Containerized deployment eliminating dependency management

### Docker Architecture
The Docker implementation provides a fully isolated environment with all dependencies pre-installed:

- **Base Image**: Python 3.11-slim-bookworm (Debian-based for stability)
- **Display Server**: Xvfb (X Virtual Framebuffer) for headless screenshot capture
- **Browser**: Chromium with ChromeDriver for Selenium automation
- **Isolation**: Non-root user execution with proper permission handling
- **Volume Mounts**: Input files and output directory mapping

**Container Components**:
```
Container Environment:
├── Python 3.11 Runtime
├── Chromium Browser
├── ChromeDriver (Selenium WebDriver)
├── Xvfb Display Server
├── EyeWitness Application
└── All Python Dependencies
```

### Core Architecture Pattern
```
CLI Interface → Target Parser → Multi-threaded Capture → Database Storage → Report Generation
```

## Project Structure

```
EyeWitness/
├── Python/                     # Primary Linux/Unix implementation
│   ├── EyeWitness.py           # Main entry point and CLI interface
│   ├── modules/                # Core functionality modules
│   │   ├── objects.py          # Data models (HTTPTableObject, UAObject)
│   │   ├── selenium_module.py  # Web automation and screenshot capture
│   │   ├── db_manager.py       # SQLite database operations
│   │   ├── reporting.py        # HTML report generation
│   │   ├── helpers.py          # Utility functions and XML parsing
│   │   ├── driver_manager.py   # WebDriver management and auto-download
│   │   └── platform_utils.py   # Cross-platform compatibility
├── setup/                      # Installation and dependencies
│   ├── setup.sh               # Linux/Unix installation script
│   ├── setup.ps1              # Windows PowerShell installation
│   └── requirements.txt       # Python dependencies
├── Dockerfile                  # Docker container definition
├── .dockerignore              # Docker build exclusions
├── DOCKER.md                  # Docker usage documentation
└── docker-compose.yml         # Docker Compose configuration (optional)
```

## Core Modules and Functions

### 1. objects.py - Data Models

#### HTTPTableObject Class
**Purpose**: Core data structure representing a web target.

**Key Attributes**:
- `remote_system`: Target URL
- `page_title`: Extracted page title
- `headers`: HTTP response headers
- `source_code`: Page source HTML
- `error_state`: Connection/load error status
- `screenshot_path`: Path to captured screenshot

**Notable Methods**:
```python
def CreateDataRow(self)           # Generate HTML table row for reports
def CreateReport(self, output_dir) # Create individual target report page
def PrintCVSRow(self)             # Export data as CSV row
```

#### UAObject Class
**Purpose**: User-Agent testing variant that extends HTTPTableObject.

**Key Features**:
- Tracks differences between baseline and UA-specific requests
- Inherits all HTTPTableObject functionality
- Used for user-agent enumeration testing

### 2. selenium_module.py - Web Automation Engine

#### create_driver(cli_options, user_agent=None)
**Purpose**: Initialize Chromium WebDriver with optimized headless configuration.

**Parameters**:
- `cli_options`: Command-line arguments and settings
- `user_agent`: Custom user-agent string (optional)

**Returns**: Configured Selenium Chrome WebDriver instance

**Key Features**:
- Cross-platform Chromium/Chrome detection
- Optimized headless operation with new headless mode
- Custom user-agent configuration
- SSL certificate error handling
- Enhanced network error categorization
- Memory and performance optimization

#### capture_host(targets, selenium_driver, output_directory, cli_options)
**Purpose**: Core screenshot capture function.

**Parameters**:
- `targets`: List of HTTPTableObject instances to process
- `selenium_driver`: Configured WebDriver instance
- `output_directory`: Directory for saving screenshots and data
- `cli_options`: Configuration options

**Workflow**:
1. Navigate to target URL with timeout handling
2. Dismiss authentication prompts and alerts
3. Capture screenshot and save to file
4. Extract page source and headers
5. Handle SSL errors and connection issues
6. Store results in HTTPTableObject

### 3. db_manager.py - Data Persistence

#### Important Functions:

#### create_database_tables(db_conn, cli_options)
**Purpose**: Initialize SQLite database schema.

**Tables Created**:
- `http`: Main targets table with HTTPTableObject data
- `ua`: User-agent testing variants
- `opts`: Scan configuration and options

#### db_store_screenshot(cli_options, http_object)
**Purpose**: Store HTTPTableObject in database with pickle serialization.

#### db_get_incomplete_targets(cli_options)
**Purpose**: Retrieve unfinished targets for resume functionality.

**Returns**: List of HTTPTableObject instances that need processing

### 4. reporting.py - Report Generation

#### create_report(cli_options, report_objects)
**Purpose**: Generate main HTML report with categorized results.

**Parameters**:
- `cli_options`: Configuration including output directory
- `report_objects`: List of completed HTTPTableObject instances

**Key Features**:
- 25+ predefined service categories
- Fuzzy matching for service grouping (70% similarity threshold)
- Pagination for large result sets
- Bootstrap-based responsive design
- CSV export functionality

#### create_table_string(objects, table_head)
**Purpose**: Generate HTML table for report sections.

**Parameters**:
- `objects`: List of HTTPTableObject instances for table
- `table_head`: HTML table header string

**Returns**: Complete HTML table string with navigation

### 5. helpers.py - Utility Functions

#### create_targets_from_file(file_name)
**Purpose**: Parse input files and create target lists.

**Supported Formats**:
- Plain text files with URLs
- Nmap XML output files
- Nessus XML export files
- Masscan XML results

**Returns**: List of target URLs extracted from input

#### parse_nmap_xml(nmap_file)
**Purpose**: Extract web services from Nmap scan results.

**Logic**:
1. Parse XML for host and port information
2. Identify HTTP/HTTPS services
3. Generate URLs with appropriate protocols
4. Handle custom ports and service detection

#### default_creds_category(page_source, page_title)
**Purpose**: Identify applications with known default credentials.

**Parameters**:
- `page_source`: HTML source code of target page
- `page_title`: Extracted page title

**Returns**: Boolean indicating if default credentials detected

### 6. selenium_module.py - Enhanced Browser Management

#### find_chromedriver()
**Purpose**: Locate ChromeDriver executable in system paths.

**Search Locations**:
1. Standard system paths (/usr/bin, /usr/local/bin)
2. Snap package locations
3. System PATH environment
4. Common installation directories

#### check_browsers_available()
**Purpose**: Verify Chromium/Chrome and ChromeDriver availability.

**Returns**: Dictionary with browser and driver status information

### 7. platform_utils.py - Cross-Platform Support

#### detect_platform()
**Purpose**: Determine operating system and architecture.

**Returns**: Dictionary with platform information

#### find_chromium_executable()
**Purpose**: Locate Chromium/Chrome installation across platforms.

**Search Paths**:
- Windows: Program Files, Program Files (x86), AppData paths
- Linux: /usr/bin, /usr/local/bin, snap installations
- macOS: Applications folder and Homebrew paths

#### setup_virtual_display()
**Purpose**: Configure headless display for screenshot capture.

**Returns**: PyVirtualDisplay instance for Unix systems

## Main Workflow (EyeWitness.py)

### 1. Command Line Interface
**Entry Point**: `main()` function

**Key Arguments**:
- `-f, --file`: Input file with URLs
- `-x, --xml`: Nmap/Nessus XML input
- `--single`: Single URL mode
- `-d, --out`: Output directory
- `--timeout`: Page load timeout
- `--threads`: Number of worker processes
- `--resume`: Resume interrupted scan

### 2. Processing Pipeline

#### Phase 1: Input Processing
```python
def create_targets(cli_options):
    # Parse input files (text, XML) to create target list
    # Return list of URLs for processing
```

#### Phase 2: Multi-threaded Capture
```python
def capture_screenshots(targets, cli_options):
    # Create process pool for parallel execution
    # Each worker captures screenshots using Selenium
    # Store results in SQLite database for persistence
```

#### Phase 3: Report Generation
```python
def generate_report(cli_options):
    # Load completed targets from database
    # Categorize and group similar services
    # Generate HTML reports with navigation
```

## Data Flow

```
Input Sources (URLs/XML) 
    ↓
Target Parser (helpers.py)
    ↓
HTTPTableObject Creation (objects.py)
    ↓
Multi-threaded Screenshot Capture (selenium_module.py)
    ↓
Database Storage (db_manager.py)
    ↓
Report Generation (reporting.py)
    ↓
HTML Reports + Screenshots
```

## Key Configuration Options

### Database Configuration
- **File**: `{output_dir}/EyeWitness.db`
- **Engine**: SQLite with pickle serialization
- **Schema**: http, ua, opts tables
- **Resume**: Tracks incomplete targets for resumption

### Selenium Configuration
- **Browser**: Chromium/Chrome (required)
- **Mode**: Headless with new headless mode (default)
- **Timeouts**: Configurable page load and screenshot timeouts
- **User Agents**: Custom UA string support
- **Performance**: Memory optimization and background throttling disabled
- **Security**: Certificate error handling and automation detection disabled

### Report Configuration
- **Format**: HTML with Bootstrap CSS
- **Pagination**: 25 results per page (configurable)
- **Categories**: 25+ predefined service types
- **Grouping**: 70% similarity threshold for page title clustering
- **Export**: CSV data export capability

## Extension Points for Developers

### 1. Adding New Input Formats
**Location**: `helpers.py`
**Function**: `create_targets_from_file()`
**Process**: Add new parsing logic for additional file formats

### 2. Custom Service Categories
**Location**: `categories.txt` and `reporting.py`
**Process**: Add new categories and update categorization logic

### 3. Additional Signature Detection
**Location**: `signatures.txt` and `helpers.py`
**Function**: `default_creds_category()`
**Process**: Add new application signatures and detection rules

### 4. Enhanced Screenshot Capture
**Location**: `selenium_module.py`
**Function**: `capture_host()`
**Process**: Modify screenshot logic, add new data extraction

### 5. Custom Report Templates
**Location**: `reporting.py`
**Functions**: `create_report()`, `create_table_string()`
**Process**: Modify HTML templates and styling

## Dependencies and Requirements

### Core Python Dependencies
```
rapidfuzz>=3.0.0      # Fast string matching for clustering
selenium>=4.29.0      # Modern web browser automation  
netaddr>=0.10.0       # Network address manipulation
pyvirtualdisplay>=3.0 # Virtual display support (Unix)
```

### System Requirements
- **Chromium/Chrome Browser**: Required for Selenium WebDriver
- **ChromeDriver**: WebDriver executable (installed via package manager)
- **Xvfb**: Virtual display server (Linux headless environments)
- **Python 3.7+**: Minimum Python version requirement

## Security Considerations

### Legitimate Security Tool
- **Purpose**: Authorized security assessments only
- **No Malicious Code**: Clean, transparent implementation
- **Standard Practices**: Follows security tool development patterns

### Safe Usage Guidelines
- Only use on authorized targets
- Respect rate limiting and target resources
- Follow responsible disclosure for findings
- Maintain scan logs for audit purposes

## Performance Optimization

### Multi-threading Architecture
- **Process Pool**: Configurable worker thread count
- **Shared Queue**: Efficient work distribution
- **Database Per Worker**: Parallel database writes
- **Progress Tracking**: Real-time status updates

### Resource Management
- **Memory Optimization**: Efficient object lifecycle management
- **Disk Space**: Screenshot compression and cleanup
- **Network**: Configurable timeouts and retry logic
- **CPU**: Balanced parallel processing

## Troubleshooting Common Issues

### Chromium/ChromeDriver Issues
- **Linux Solution**: `sudo apt install chromium-browser chromium-chromedriver`
- **Windows Solution**: Run `setup.ps1` script as Administrator
- **macOS Solution**: `brew install --cask google-chrome`

### Headless Display Issues (Linux)
- **Solution**: Install Xvfb: `sudo apt install xvfb`
- **Verification**: Check `platform_utils.py` virtual display setup
- **Alternative**: Use optimized headless mode (no display server needed)

### Permission Issues
- **Solution**: Run setup scripts with appropriate privileges
- **Alternative**: Manual dependency installation per requirements.txt

### Database Corruption
- **Solution**: Delete EyeWitness.db file to reset scan state
- **Prevention**: Avoid forceful termination during database writes

This reference provides comprehensive information for developers to understand, modify, and extend EyeWitness functionality without requiring assistance from the original authors.