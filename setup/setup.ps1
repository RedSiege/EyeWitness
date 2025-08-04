# EyeWitness Windows Setup Script
# PowerShell script for automatic Windows installation

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SkipFirefox,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
EyeWitness Windows Setup Script

Usage: .\setup.ps1 [options]

Options:
  -Force        Force reinstall even if components exist
  -SkipFirefox  Skip Firefox installation (assume already installed)
  -Help         Show this help message

Examples:
  .\setup.ps1                    # Standard installation
  .\setup.ps1 -Force             # Force reinstall everything
  .\setup.ps1 -SkipFirefox       # Skip Firefox installation

Requirements:
  - PowerShell 5.0+ (Windows 10/11 default)
  - Administrator privileges
  - Internet connection
"@
    exit 0
}

# Color output functions
function Write-Success { 
    param($Message) 
    Write-Host "[+] $Message" -ForegroundColor Green 
}
function Write-ErrorMsg { 
    param($Message) 
    Write-Host "[-] $Message" -ForegroundColor Red 
}
function Write-WarningMsg { 
    param($Message) 
    Write-Host "[!] $Message" -ForegroundColor Yellow 
}
function Write-InfoMsg { 
    param($Message) 
    Write-Host "[*] $Message" -ForegroundColor Cyan 
}

Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║                    EyeWitness Windows Setup                  ║
║                                                              ║
║  This script will install the required dependencies for     ║
║  EyeWitness to run on Windows including:                    ║
║                                                              ║
║  • Python dependencies                                      ║
║  • Firefox browser (if not present)                         ║
║  • Geckodriver for browser automation                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# Check if running as administrator
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-ErrorMsg "This script requires Administrator privileges."
    Write-InfoMsg "Please run PowerShell as Administrator and try again."
    Write-InfoMsg "Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

Write-Success "Running with Administrator privileges"

# Check PowerShell version
$psVersion = $PSVersionTable.PSVersion.Major
if ($psVersion -lt 5) {
    Write-ErrorMsgMsg "PowerShell 5.0 or higher is required. Current version: $psVersion"
    Write-InfoMsgMsg "Please update PowerShell: https://aka.ms/pscore6"
    exit 1
}

Write-Success "PowerShell version $psVersion is supported"

# Check Python installation
Write-InfoMsg "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        if ($majorVersion -ge 3 -and $minorVersion -ge 7) {
            Write-Success "Python $pythonVersion found"
        } else {
            Write-WarningMsg "Python $pythonVersion found, but 3.7+ recommended"
        }
    }
} catch {
    Write-ErrorMsg "Python not found or not in PATH"
    Write-InfoMsg "Please install Python 3.7+ from https://python.org"
    Write-InfoMsg "Make sure to check 'Add to PATH' during installation"
    exit 1
}

# Check pip installation
Write-InfoMsg "Checking pip installation..."
try {
    $pipVersion = python -m pip --version 2>&1
    Write-Success "pip found: $pipVersion"
} catch {
    Write-ErrorMsg "pip not found"
    Write-InfoMsg "Please ensure pip is installed with Python"
    exit 1
}

# Install/update pip packages
Write-InfoMsg "Installing Python dependencies..."
$requirementsFile = Join-Path $PSScriptRoot "requirements.txt"

if (-not (Test-Path $requirementsFile)) {
    Write-ErrorMsg "requirements.txt not found at: $requirementsFile"
    exit 1
}

try {
    # Upgrade pip first
    python -m pip install --upgrade pip --quiet
    Write-Success "pip updated"
    
    # Install packages
    python -m pip install -r $requirementsFile --quiet
    Write-Success "Python dependencies installed"
} catch {
    Write-ErrorMsg "Failed to install Python dependencies"
    Write-InfoMsg "Try running: python -m pip install -r requirements.txt"
    exit 1
}

# Check Firefox installation
if (-not $SkipFirefox) {
    Write-InfoMsg "Checking Firefox installation..."
    
    $firefoxPaths = @(
        "C:\Program Files\Mozilla Firefox\firefox.exe",
        "C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        "$env:USERPROFILE\AppData\Local\Mozilla Firefox\firefox.exe"
    )
    
    $firefoxFound = $false
    foreach ($path in $firefoxPaths) {
        if (Test-Path $path) {
            Write-Success "Firefox found at: $path"
            $firefoxFound = $true
            break
        }
    }
    
    if (-not $firefoxFound -or $Force) {
        Write-InfoMsg "Installing Firefox..."
        
        # Check if Chocolatey is available
        if (Get-Command choco -ErrorAction SilentlyContinue) {
            try {
                choco install firefox -y --quiet
                Write-Success "Firefox installed via Chocolatey"
                $firefoxFound = $true
            } catch {
                Write-WarningMsg "Chocolatey installation failed, trying direct download"
            }
        }
        
        if (-not $firefoxFound) {
            Write-InfoMsg "Downloading Firefox installer..."
            $firefoxUrl = "https://download.mozilla.org/?product=firefox-latest&os=win64&lang=en-US"
            $installerPath = "$env:TEMP\FirefoxInstaller.exe"
            
            try {
                Invoke-WebRequest -Uri $firefoxUrl -OutFile $installerPath -UseBasicParsing
                Write-Success "Firefox downloaded"
                
                Write-InfoMsg "Installing Firefox (this may take a moment)..."
                Start-Process -FilePath $installerPath -ArgumentList "/S" -Wait -NoNewWindow
                Write-Success "Firefox installation completed"
                
                # Clean up installer
                Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
            } catch {
                Write-WarningMsg "Automatic Firefox installation failed"
                Write-InfoMsg "Please manually install Firefox from: https://firefox.com"
            }
        }
    }
} else {
    Write-InfoMsg "Skipping Firefox installation (--SkipFirefox specified)"
}

# Install Geckodriver
Write-InfoMsg "Setting up Geckodriver..."

# Determine architecture
$arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
$geckodriverName = "geckodriver.exe"

try {
    # Get latest geckodriver release info
    Write-InfoMsg "Getting latest Geckodriver version..."
    $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
    $version = $releases.tag_name
    
    # Find the appropriate download
    $asset = $releases.assets | Where-Object { $_.name -like "*$arch*" } | Select-Object -First 1
    
    if (-not $asset) {
        Write-ErrorMsg "Could not find Geckodriver for architecture: $arch"
        exit 1
    }
    
    Write-Success "Found Geckodriver $version for $arch"
    
    # Download geckodriver
    $zipPath = "$env:TEMP\geckodriver-$version-$arch.zip"
    Write-InfoMsg "Downloading Geckodriver..."
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -UseBasicParsing
    Write-Success "Geckodriver downloaded"
    
    # Extract geckodriver
    $extractPath = "$env:TEMP\geckodriver-extract"
    if (Test-Path $extractPath) {
        Remove-Item $extractPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $extractPath -Force | Out-Null
    
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
    Write-Success "Geckodriver extracted"
    
    # Install to System32 (in PATH)
    $destPath = "C:\Windows\System32\$geckodriverName"
    $sourcePath = Join-Path $extractPath $geckodriverName
    
    if (Test-Path $sourcePath) {
        Copy-Item $sourcePath $destPath -Force
        Write-Success "Geckodriver installed to: $destPath"
    } else {
        Write-ErrorMsg "Geckodriver executable not found in downloaded archive"
    }
    
    # Clean up temporary files
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    Remove-Item $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    
} catch {
    Write-WarningMsg "Automatic Geckodriver installation failed: $_"
    Write-InfoMsg "You can manually install from: https://github.com/mozilla/geckodriver/releases"
    Write-InfoMsg "Download the $arch version and place geckodriver.exe in your PATH"
}

# Verify installation
Write-InfoMsg "Verifying installation..."

# Test Python imports
try {
    python -c "import selenium; import rapidfuzz; import netaddr; print('Python packages OK')" 2>$null
    Write-Success "Python packages verified"
} catch {
    Write-WarningMsg "Some Python packages may not be properly installed"
}

# Test Geckodriver
try {
    $geckodriverVersion = & geckodriver --version 2>$null | Select-String "geckodriver" | Select-Object -First 1
    if ($geckodriverVersion) {
        Write-Success "Geckodriver verified: $geckodriverVersion"
    } else {
        Write-WarningMsg "Geckodriver not found in PATH"
    }
} catch {
    Write-WarningMsg "Geckodriver verification failed"
}

# Test Firefox
try {
    # Quick test that Firefox can be found
    python -c @"
from modules.platform_utils import PlatformManager
pm = PlatformManager()
firefox = pm.find_firefox_executable()
if firefox:
    print(f'Firefox found: {firefox}')
else:
    print('Firefox not found')
"@ 2>$null | Tee-Object -Variable firefoxTest
    
    if ($firefoxTest -match "Firefox found:") {
        Write-Success $firefoxTest
    } else {
        Write-WarningMsg "Firefox may not be properly installed"
    }
} catch {
    Write-WarningMsg "Firefox verification failed"
}

Write-Host ""
Write-Host "[+] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Test it: python ..\EyeWitness.py --single https://example.com -d test"
Write-Host "If it breaks, check firefox/geckodriver installation"

Write-Success "Windows setup completed successfully!"