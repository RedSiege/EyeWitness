# EyeWitness Windows Setup Script - Chromium Edition
# PowerShell script for automatic Windows installation with Chrome/Chromium

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SkipChrome,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
EyeWitness Windows Setup Script (Chromium Edition)

Usage: .\setup.ps1 [options]

Options:
  -Force        Force reinstall even if components exist
  -SkipChrome   Skip Chrome installation (assume already installed)
  -Help         Show this help message

Examples:
  .\setup.ps1                    # Standard installation
  .\setup.ps1 -Force             # Force reinstall everything
  .\setup.ps1 -SkipChrome        # Skip Chrome installation

Requirements:
  - PowerShell 5.0+ (Windows 10/11 default)
  - Administrator privileges
  - Internet connection

Dependencies installed:
  - Python packages (selenium, etc.)
  - Google Chrome browser
  - ChromeDriver for automation
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
║                EyeWitness Windows Setup (Chromium)          ║
║                                                              ║
║  This script will install the required dependencies for     ║
║  EyeWitness to run on Windows including:                    ║
║                                                              ║
║  • Python dependencies (selenium, etc.)                     ║
║  • Google Chrome browser (if not present)                   ║
║  • ChromeDriver for browser automation                      ║
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
    Write-ErrorMsg "PowerShell 5.0 or higher is required. Current version: $psVersion"
    Write-InfoMsg "Please update PowerShell: https://aka.ms/pscore6"
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
    Write-WarningMsg "requirements.txt not found, installing essential packages directly"
    $packages = @("selenium", "netaddr", "psutil", "pyvirtualdisplay", "argcomplete")
} else {
    $packages = @()
}

try {
    # Upgrade pip first
    python -m pip install --upgrade pip --quiet
    Write-Success "pip updated"
    
    # Install packages
    if ($packages.Count -gt 0) {
        foreach ($package in $packages) {
            python -m pip install $package --quiet
            Write-Success "Installed $package"
        }
    } else {
        python -m pip install -r $requirementsFile --quiet
        Write-Success "Python dependencies installed from requirements.txt"
    }
} catch {
    Write-ErrorMsg "Failed to install Python dependencies"
    Write-InfoMsg "Try running manually: python -m pip install selenium netaddr psutil"
    exit 1
}

# Check Chrome installation
if (-not $SkipChrome) {
    Write-InfoMsg "Checking Chrome installation..."
    
    $chromePaths = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles}\Chromium\Application\chrome.exe"
    )
    
    $chromeFound = $false
    $chromePath = $null
    
    foreach ($path in $chromePaths) {
        if (Test-Path $path) {
            $chromeFound = $true
            $chromePath = $path
            Write-Success "Chrome found at: $path"
            break
        }
    }
    
    if (-not $chromeFound -or $Force) {
        Write-InfoMsg "Installing Google Chrome..."
        
        # Download Chrome installer
        $tempDir = [System.IO.Path]::GetTempPath()
        $chromeInstaller = Join-Path $tempDir "ChromeSetup.exe"
        
        try {
            Write-InfoMsg "Downloading Chrome installer..."
            $chromeUrl = "https://dl.google.com/chrome/install/ChromeStandaloneSetup64.exe"
            Invoke-WebRequest -Uri $chromeUrl -OutFile $chromeInstaller -UseBasicParsing
            Write-Success "Chrome installer downloaded"
            
            Write-InfoMsg "Installing Chrome (this may take a moment)..."
            Start-Process -FilePath $chromeInstaller -ArgumentList "/silent", "/install" -Wait
            
            # Clean up
            Remove-Item $chromeInstaller -Force -ErrorAction SilentlyContinue
            
            # Verify installation
            Start-Sleep -Seconds 3
            $chromeFound = $false
            foreach ($path in $chromePaths) {
                if (Test-Path $path) {
                    $chromeFound = $true
                    Write-Success "Chrome successfully installed at: $path"
                    break
                }
            }
            
            if (-not $chromeFound) {
                Write-WarningMsg "Chrome installation may have failed"
                Write-InfoMsg "Please install Chrome manually from: https://www.google.com/chrome/"
            }
            
        } catch {
            Write-ErrorMsg "Failed to download/install Chrome: $_"
            Write-InfoMsg "Please install Chrome manually from: https://www.google.com/chrome/"
        }
    }
}

# Install ChromeDriver
Write-InfoMsg "Checking ChromeDriver installation..."

$chromeDriverPaths = @(
    "${env:ProgramFiles}\ChromeDriver\chromedriver.exe",
    "${env:ProgramFiles(x86)}\ChromeDriver\chromedriver.exe",
    ".\chromedriver.exe",
    "${env:PATH}" -split ";" | ForEach-Object { Join-Path $_ "chromedriver.exe" }
)

$chromeDriverFound = $false
foreach ($path in $chromeDriverPaths) {
    if ((Test-Path $path) -and (-not $Force)) {
        $chromeDriverFound = $true
        Write-Success "ChromeDriver found at: $path"
        break
    }
}

if (-not $chromeDriverFound -or $Force) {
    Write-InfoMsg "Installing ChromeDriver..."
    
    try {
        # Get Chrome version
        $chromeVersion = $null
        foreach ($path in $chromePaths) {
            if (Test-Path $path) {
                $versionInfo = (Get-Item $path).VersionInfo.FileVersion
                if ($versionInfo -match "(\d+\.\d+\.\d+)") {
                    $chromeVersion = $matches[1]
                    break
                }
            }
        }
        
        if (-not $chromeVersion) {
            Write-WarningMsg "Could not determine Chrome version, using latest ChromeDriver"
            $chromeDriverUrl = "https://chromedriver.chromium.org/downloads"
        }
        
        # Download and install ChromeDriver
        $chromeDriverDir = "${env:ProgramFiles}\ChromeDriver"
        $chromeDriverExe = Join-Path $chromeDriverDir "chromedriver.exe"
        
        # Create directory
        if (-not (Test-Path $chromeDriverDir)) {
            New-Item -ItemType Directory -Path $chromeDriverDir -Force | Out-Null
        }
        
        # For simplicity, download the latest stable version
        $tempZip = Join-Path ([System.IO.Path]::GetTempPath()) "chromedriver.zip"
        $chromeDriverDownloadUrl = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
        
        try {
            # Get latest version
            $latestVersion = Invoke-WebRequest -Uri $chromeDriverDownloadUrl -UseBasicParsing | Select-Object -ExpandProperty Content
            $downloadUrl = "https://chromedriver.storage.googleapis.com/$latestVersion/chromedriver_win32.zip"
            
            Write-InfoMsg "Downloading ChromeDriver $latestVersion..."
            Invoke-WebRequest -Uri $downloadUrl -OutFile $tempZip -UseBasicParsing
            
            # Extract
            Expand-Archive -Path $tempZip -DestinationPath $chromeDriverDir -Force
            Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
            
            # Add to PATH if not already there
            $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
            if ($currentPath -notlike "*$chromeDriverDir*") {
                [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$chromeDriverDir", "Machine")
                Write-Success "ChromeDriver added to system PATH"
            }
            
            Write-Success "ChromeDriver installed successfully"
            
        } catch {
            Write-WarningMsg "Failed to auto-install ChromeDriver: $_"
            Write-InfoMsg "Please download ChromeDriver manually from: https://chromedriver.chromium.org/"
            Write-InfoMsg "Extract chromedriver.exe to a directory in your PATH"
        }
        
    } catch {
        Write-WarningMsg "ChromeDriver installation encountered issues: $_"
        Write-InfoMsg "You may need to install ChromeDriver manually"
    }
}

# Final verification
Write-InfoMsg "Verifying installation..."

$errors = 0

# Check Python
try {
    python -c "import selenium; print('✓ Selenium available')"
    Write-Success "Python selenium module verified"
} catch {
    Write-ErrorMsg "Python selenium module not available"
    $errors++
}

# Check Chrome
$chromeFound = $false
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        Write-Success "Chrome browser verified: $path"
        $chromeFound = $true
        break
    }
}
if (-not $chromeFound) {
    Write-ErrorMsg "Chrome browser not found"
    $errors++
}

# Check ChromeDriver
try {
    $cdVersion = chromedriver --version 2>&1
    Write-Success "ChromeDriver verified: $cdVersion"
} catch {
    Write-ErrorMsg "ChromeDriver not found in PATH"
    $errors++
}

Write-Host "`n" -NoNewline

if ($errors -eq 0) {
    Write-Success "✓ All dependencies verified - EyeWitness is ready to run!"
    Write-Host ""
    Write-InfoMsg "Test installation with:"
    Write-Host "  cd Python && python EyeWitness.py --single https://example.com" -ForegroundColor White
} else {
    Write-ErrorMsg "✗ $errors error(s) found - please resolve before using EyeWitness"
    Write-InfoMsg "Re-run this script or install missing components manually"
}

Write-Host ""
Write-InfoMsg "EyeWitness setup completed!"
Write-InfoMsg "Visit https://www.redsiege.com for more Red Siege tools"