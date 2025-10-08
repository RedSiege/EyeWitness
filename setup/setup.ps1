# EyeWitness Windows Setup Script - Virtual Environment Edition
# Production-ready PowerShell script using Python virtual environments

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SkipChrome,
    [switch]$Help
)

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $ProjectRoot "eyewitness-venv"
$RequirementsFile = Join-Path $ScriptDir "requirements.txt"

if ($Help) {
    Write-Host @"
EyeWitness Windows Setup Script (Virtual Environment Edition)

Usage: .\setup.ps1 [options]

Options:
  -Force        Force reinstall (recreate virtual environment)
  -SkipChrome   Skip Chrome installation (assume already installed)
  -Help         Show this help message

Examples:
  .\setup.ps1                    # Standard installation with venv
  .\setup.ps1 -Force             # Force recreate virtual environment
  .\setup.ps1 -SkipChrome        # Skip Chrome, create venv only

Features:
  - Creates isolated Python virtual environment
  - Avoids system Python package conflicts
  - Production-ready error handling and rollback
  - Cross-platform consistent approach

Requirements:
  - PowerShell 5.0+ (Windows 10/11 default)
  - Administrator privileges
  - Python 3.7+ with venv support
  - Internet connection

Virtual Environment Benefits:
  - No system package conflicts
  - Easy to remove/recreate
  - Consistent across all platforms
  - No PEP 668 issues
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

# Cleanup function for failed installations
function Cleanup-OnFailure {
    Write-WarningMsg "Installation failed. Cleaning up..."
    if (Test-Path $VenvDir) {
        Remove-Item -Path $VenvDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-InfoMsg "Removed incomplete virtual environment"
    }
}

# Header
Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║            EyeWitness Windows Setup (Virtual Environment)   ║
║                                                              ║
║  Production-ready installation using Python virtual         ║
║  environments for consistent, isolated package management   ║
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

# Check Python installation and version
Write-InfoMsg "Checking Python installation..."
try {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "Python command not found"
    }
    
    $pythonVersion = & python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        $patchVersion = [int]$matches[3]
        
        if ($majorVersion -ge 3 -and $minorVersion -ge 7) {
            Write-Success "Python $pythonVersion found"
        } else {
            Write-ErrorMsg "Python 3.7+ required. Found: $pythonVersion"
            Write-InfoMsg "Please install Python 3.7+ from https://python.org"
            exit 1
        }
    } else {
        throw "Could not parse Python version"
    }
} catch {
    Write-ErrorMsg "Python not found or not in PATH"
    Write-InfoMsg "Please install Python 3.7+ from https://python.org"
    Write-InfoMsg "Make sure to check 'Add to PATH' during installation"
    exit 1
}

# Check venv module availability
Write-InfoMsg "Checking Python venv module..."
try {
    & python -m venv --help > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "venv module not available"
    }
    Write-Success "Python venv module available"
} catch {
    Write-ErrorMsg "Python venv module not available"
    Write-InfoMsg "Please ensure Python was installed with venv support"
    Write-InfoMsg "Reinstall Python from https://python.org with default options"
    exit 1
}

# Check pip installation
Write-InfoMsg "Checking pip availability..."
try {
    $pipVersion = & python -m pip --version 2>&1
    Write-Success "pip found: $pipVersion"
} catch {
    Write-ErrorMsg "pip not found"
    Write-InfoMsg "Please ensure pip is installed with Python"
    exit 1
}

# Chrome installation function
function Install-Chrome {
    if ($SkipChrome) {
        Write-InfoMsg "Skipping Chrome installation as requested"
        return
    }
    
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
            
            # Clean up installer
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

# ChromeDriver installation function
function Install-ChromeDriver {
    Write-InfoMsg "Checking ChromeDriver installation..."

    $chromeDriverPaths = @(
        "${env:ProgramFiles}\ChromeDriver\chromedriver.exe",
        "${env:ProgramFiles(x86)}\ChromeDriver\chromedriver.exe",
        (Get-Command chromedriver -ErrorAction SilentlyContinue).Source
    )

    $chromeDriverFound = $false
    foreach ($path in $chromeDriverPaths) {
        if ($path -and (Test-Path $path) -and (-not $Force)) {
            $chromeDriverFound = $true
            Write-Success "ChromeDriver found at: $path"
            break
        }
    }

    if (-not $chromeDriverFound -or $Force) {
        Write-InfoMsg "Installing ChromeDriver..."
        
        try {
            # Create ChromeDriver directory
            $chromeDriverDir = "${env:ProgramFiles}\ChromeDriver"
            $chromeDriverExe = Join-Path $chromeDriverDir "chromedriver.exe"
            
            if (-not (Test-Path $chromeDriverDir)) {
                New-Item -ItemType Directory -Path $chromeDriverDir -Force | Out-Null
            }
            
            # Download latest ChromeDriver (simplified approach for stability)
            $tempZip = Join-Path ([System.IO.Path]::GetTempPath()) "chromedriver.zip"
            
            # Use Chrome for Testing API for latest stable version
            try {
                Write-InfoMsg "Downloading latest stable ChromeDriver..."
                $latestVersionUrl = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
                $versionData = Invoke-RestMethod -Uri $latestVersionUrl
                $stableVersion = $versionData.channels.Stable.version
                $downloadUrl = $versionData.channels.Stable.downloads.chromedriver | Where-Object { $_.platform -eq "win64" } | Select-Object -ExpandProperty url -First 1
                
                if ($downloadUrl) {
                    Write-InfoMsg "Downloading ChromeDriver version $stableVersion..."
                    Invoke-WebRequest -Uri $downloadUrl -OutFile $tempZip -UseBasicParsing
                } else {
                    throw "Could not find Win64 ChromeDriver download URL"
                }
            } catch {
                Write-WarningMsg "Failed to get latest version, trying fallback method..."
                # Fallback to a known stable version
                $fallbackUrl = "https://storage.googleapis.com/chrome-for-testing-public/119.0.6045.105/win64/chromedriver-win64.zip"
                Invoke-WebRequest -Uri $fallbackUrl -OutFile $tempZip -UseBasicParsing
            }
            
            # Extract ChromeDriver
            Write-InfoMsg "Extracting ChromeDriver..."
            Expand-Archive -Path $tempZip -DestinationPath $chromeDriverDir -Force
            
            # Move chromedriver.exe to correct location if needed
            $extractedDriver = Get-ChildItem -Path $chromeDriverDir -Name "chromedriver.exe" -Recurse | Select-Object -First 1
            if ($extractedDriver) {
                $extractedPath = Join-Path $chromeDriverDir $extractedDriver
                if ($extractedPath -ne $chromeDriverExe) {
                    Move-Item -Path $extractedPath -Destination $chromeDriverExe -Force
                }
            }
            
            # Clean up any extra directories
            Get-ChildItem -Path $chromeDriverDir -Directory | Remove-Item -Recurse -Force
            
            # Clean up temp file
            Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
            
            # Add to PATH if not already there
            $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
            if ($currentPath -notlike "*$chromeDriverDir*") {
                [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$chromeDriverDir", "Machine")
                Write-Success "ChromeDriver added to system PATH"
            }
            
            Write-Success "ChromeDriver installed successfully"
            
        } catch {
            Write-WarningMsg "Failed to install ChromeDriver: $_"
            Write-InfoMsg "Please download ChromeDriver manually from:"
            Write-InfoMsg "https://googlechromelabs.github.io/chrome-for-testing/"
            Write-InfoMsg "Extract chromedriver.exe to a directory in your PATH"
        }
    }
}

# Virtual environment creation function
function Create-VirtualEnv {
    Write-InfoMsg "Creating Python virtual environment..."
    
    try {
        # Remove existing venv if it exists and Force is specified
        if ((Test-Path $VenvDir) -and $Force) {
            Write-WarningMsg "Existing virtual environment found. Removing due to -Force..."
            Remove-Item -Path $VenvDir -Recurse -Force
        } elseif (Test-Path $VenvDir) {
            Write-WarningMsg "Existing virtual environment found. Use -Force to recreate."
            Write-InfoMsg "Using existing virtual environment at: $VenvDir"
            return
        }
        
        # Create new virtual environment
        & python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment"
        }
        Write-Success "Virtual environment created at: $VenvDir"
        
        # Test activation
        $activateScript = Join-Path $VenvDir "Scripts\activate.bat"
        if (-not (Test-Path $activateScript)) {
            throw "Virtual environment activation script not found"
        }
        Write-Success "Virtual environment activation script verified"
        
    } catch {
        Write-ErrorMsg "Failed to create virtual environment: $_"
        Cleanup-OnFailure
        exit 1
    }
}

# Python dependencies installation function
function Install-PythonDeps {
    Write-InfoMsg "Installing Python dependencies in virtual environment..."
    
    try {
        if (-not (Test-Path $RequirementsFile)) {
            Write-ErrorMsg "Requirements file not found: $RequirementsFile"
            exit 1
        }
        
        # Activate virtual environment and install packages
        $venvPython = Join-Path $VenvDir "Scripts\python.exe"
        $venvPip = Join-Path $VenvDir "Scripts\pip.exe"
        
        if (-not (Test-Path $venvPython)) {
            throw "Virtual environment Python not found"
        }
        
        # Upgrade pip in virtual environment
        Write-InfoMsg "Upgrading pip in virtual environment..."
        & $venvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to upgrade pip"
        }
        Write-Success "pip upgraded in virtual environment"
        
        # Install from requirements.txt
        Write-InfoMsg "Installing packages from requirements.txt..."
        & $venvPython -m pip install -r $RequirementsFile
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install requirements"
        }
        Write-Success "Python dependencies installed"
        
        # Verify critical imports
        Write-InfoMsg "Verifying Python package installations..."
        
        & $venvPython -c "import selenium; print('✓ selenium')"
        if ($LASTEXITCODE -ne 0) { throw "selenium import failed" }
        
        & $venvPython -c "import netaddr; print('✓ netaddr')"  
        if ($LASTEXITCODE -ne 0) { throw "netaddr import failed" }
        
        & $venvPython -c "import psutil; print('✓ psutil')"
        if ($LASTEXITCODE -ne 0) { throw "psutil import failed" }
        
        & $venvPython -c "import argcomplete; print('✓ argcomplete')"
        if ($LASTEXITCODE -ne 0) { throw "argcomplete import failed" }
        
        # Note: pyvirtualdisplay is not needed on Windows
        Write-Success "All Python packages verified"
        
    } catch {
        Write-ErrorMsg "Failed to install Python dependencies: $_"
        Cleanup-OnFailure
        exit 1
    }
}


# Installation verification function
function Test-Installation {
    Write-InfoMsg "Testing EyeWitness installation..."
    
    try {
        $venvPython = Join-Path $VenvDir "Scripts\python.exe"
        $eyewitnessScript = Join-Path $ProjectRoot "Python\EyeWitness.py"
        
        if (-not (Test-Path $eyewitnessScript)) {
            throw "EyeWitness.py not found"
        }
        
        # Test help command
        & $venvPython $eyewitnessScript --help > $null 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "EyeWitness help command failed"
        }
        
        Write-Success "EyeWitness installation test passed"
        return $true
    } catch {
        Write-ErrorMsg "Installation test failed: $_"
        return $false
    }
}

# System verification function
function Test-SystemDeps {
    Write-InfoMsg "Verifying system dependencies..."
    
    $errors = 0
    
    # Check Chrome
    $chromePaths = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
    )
    
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
        $cdVersion = & chromedriver --version 2>&1
        Write-Success "ChromeDriver verified: $cdVersion"
    } catch {
        Write-ErrorMsg "ChromeDriver not found in PATH"
        $errors++
    }
    
    return ($errors -eq 0)
}

# Main installation flow
function Main {
    Write-InfoMsg "Starting EyeWitness installation..."
    
    try {
        # Install Chrome
        Install-Chrome
        
        # Install ChromeDriver  
        Install-ChromeDriver
        
        # Create virtual environment
        Create-VirtualEnv
        
        # Install Python dependencies
        Install-PythonDeps
        
        
        # Test installation
        if (-not (Test-Installation)) {
            throw "Installation test failed"
        }
        
        # Verify system dependencies
        $systemOk = Test-SystemDeps
        
        # Success message
        Write-Host ""
        Write-Success "✓ EyeWitness installation completed successfully!"
        Write-Host ""
        Write-InfoMsg "USAGE:"
        Write-InfoMsg "1. Activate virtual environment: .\eyewitness-venv\Scripts\activate.bat"
        Write-InfoMsg "2. Run EyeWitness: python Python\EyeWitness.py [options]"
        Write-InfoMsg "3. Deactivate when done: deactivate"
        Write-Host ""
        Write-InfoMsg "TEST INSTALLATION:"
        Write-InfoMsg ".\eyewitness-venv\Scripts\activate.bat"
        Write-InfoMsg "python Python\EyeWitness.py --single https://example.com"
        Write-Host ""
        Write-InfoMsg "Virtual environment located at: $VenvDir"
        Write-InfoMsg "Visit https://www.redsiege.com for more Red Siege tools"
        
        if (-not $systemOk) {
            Write-Host ""
            Write-WarningMsg "Some system dependencies had issues - check messages above"
        }
        
    } catch {
        Write-ErrorMsg "Installation failed: $_"
        Cleanup-OnFailure
        exit 1
    }
}

# Execute main installation
Main