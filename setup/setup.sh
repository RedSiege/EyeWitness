#!/bin/bash
# EyeWitness Setup Script - Virtual Environment Edition
# Production-ready cross-platform installation using Python virtual environments

set -euo pipefail  # Exit on any error, undefined variable, or pipe failure

# Color output functions
print_success() { echo -e "\033[32m[+] $1\033[0m"; }
print_error() { echo -e "\033[31m[-] $1\033[0m"; }
print_warning() { echo -e "\033[33m[!] $1\033[0m"; }
print_info() { echo -e "\033[36m[*] $1\033[0m"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/eyewitness-venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# Cleanup function for failed installations
cleanup_on_failure() {
    print_warning "Installation failed. Cleaning up..."
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
        print_info "Removed incomplete virtual environment"
    fi
}

# Set trap for cleanup on failure
trap cleanup_on_failure ERR

# Header
echo
print_info "╔══════════════════════════════════════════════════════════════╗"
print_info "║              EyeWitness Setup (Virtual Environment)         ║"
print_info "║                                                              ║"
print_info "║  Production-ready installation using Python virtual         ║"
print_info "║  environments to avoid PEP 668 and system conflicts         ║"
print_info "╚══════════════════════════════════════════════════════════════╝"
echo

# Check root privileges
if [ "$EUID" -ne 0 ]; then
    print_error "This script requires root privileges for system package installation"
    print_info "Please run: sudo $0"
    exit 1
fi
print_success "Running with root privileges"

# Detect system
print_info "Detecting system information..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID="$ID"
    OS_VERSION="$VERSION_ID"
else
    print_error "Cannot detect OS. /etc/os-release not found"
    exit 1
fi

ARCH=$(uname -m)
print_info "Detected OS: $OS_ID $OS_VERSION"
print_info "Detected Architecture: $ARCH"

# Check Python installation
print_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.7 or higher"
    case $OS_ID in
        ubuntu|debian|kali)
            print_info "Install with: apt update && apt install python3 python3-venv python3-pip"
            ;;
        centos|rhel|fedora)
            print_info "Install with: yum install python3 python3-venv python3-pip"
            ;;
        arch|manjaro)
            print_info "Install with: pacman -S python python-pip"
            ;;
    esac
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
print_success "Python $PYTHON_VERSION found"

# Verify Python version compatibility
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    print_error "Python 3.7+ required. Current version: $PYTHON_VERSION"
    exit 1
fi

# Install system dependencies
install_system_deps() {
    print_info "Installing system dependencies..."
    
    case $OS_ID in
        ubuntu|debian|kali|linuxmint)
            apt-get update
            # Core system packages
            apt-get install -y wget curl jq cmake xvfb python3-venv python3-dev
            
            # Browser and driver
            print_info "Installing Chromium browser and ChromeDriver..."
            apt-get install -y chromium-browser chromium-chromedriver || \
            apt-get install -y chromium chromium-driver || {
                print_warning "Package manager chromium installation failed, trying alternative names..."
                apt-get install -y chromium-browser || apt-get install -y chromium || {
                    print_error "Could not install Chromium via package manager"
                    print_info "Please install Chromium manually: sudo apt install chromium-browser"
                    exit 1
                }
            }
            ;;
            
        centos|rhel|rocky|fedora)
            if command -v dnf &> /dev/null; then
                PKG_MANAGER="dnf"
            else
                PKG_MANAGER="yum"
            fi
            
            $PKG_MANAGER install -y wget curl jq cmake python3-venv python3-devel xorg-x11-server-Xvfb
            $PKG_MANAGER install -y chromium chromedriver || {
                print_warning "ChromeDriver may need manual installation on $OS_ID"
            }
            ;;
            
        arch|manjaro)
            pacman -Syu --noconfirm
            pacman -S --noconfirm wget curl jq cmake python xvfb-run chromium
            print_info "Note: Install chromedriver from AUR if needed: yay -S chromedriver"
            ;;
            
        alpine)
            apk update
            apk add wget curl jq cmake python3 xvfb py3-pip python3-dev chromium chromium-chromedriver
            ;;
            
        *)
            print_error "Unsupported operating system: $OS_ID"
            print_info "Supported: Ubuntu, Debian, Kali, CentOS, RHEL, Fedora, Arch, Alpine"
            exit 1
            ;;
    esac
    
    print_success "System dependencies installed"
}

# Verify system dependencies
verify_system_deps() {
    print_info "Verifying system dependencies..."
    
    local missing=0
    
    # Check for browser
    local browser_found=false
    for browser in chromium-browser chromium google-chrome; do
        if command -v "$browser" &> /dev/null; then
            print_success "Browser found: $browser"
            browser_found=true
            break
        fi
    done
    
    if [ "$browser_found" = false ]; then
        print_error "No Chromium/Chrome browser found"
        missing=$((missing + 1))
    fi
    
    # Check for ChromeDriver
    local driver_found=false
    for driver in chromedriver chromium-chromedriver; do
        if command -v "$driver" &> /dev/null; then
            print_success "ChromeDriver found: $driver"
            driver_found=true
            break
        fi
    done
    
    if [ "$driver_found" = false ]; then
        print_error "ChromeDriver not found"
        missing=$((missing + 1))
    fi
    
    # Check for Xvfb (virtual display)
    if ! command -v Xvfb &> /dev/null; then
        print_error "Xvfb not found (required for headless operation)"
        missing=$((missing + 1))
    else
        print_success "Xvfb found (virtual display support)"
    fi
    
    if [ $missing -gt 0 ]; then
        print_error "$missing system dependencies missing"
        return 1
    fi
    
    print_success "All system dependencies verified"
}

# Create virtual environment
create_virtual_env() {
    print_info "Creating Python virtual environment..."
    
    # Remove existing venv if it exists
    if [ -d "$VENV_DIR" ]; then
        print_warning "Existing virtual environment found. Removing..."
        rm -rf "$VENV_DIR"
    fi
    
    # Create new virtual environment
    python3 -m venv "$VENV_DIR"
    print_success "Virtual environment created at: $VENV_DIR"
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    print_success "Virtual environment activated"
    
    # Upgrade pip in virtual environment
    pip install --upgrade pip
    print_success "pip upgraded in virtual environment"
}

# Install Python dependencies
install_python_deps() {
    print_info "Installing Python dependencies in virtual environment..."
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_error "Requirements file not found: $REQUIREMENTS_FILE"
        exit 1
    fi
    
    # Install from requirements.txt
    pip install -r "$REQUIREMENTS_FILE"
    print_success "Python dependencies installed"
    
    # Verify critical imports
    print_info "Verifying Python package installations..."
    python -c "import selenium; print('✓ selenium')" || {
        print_error "selenium import failed"
        exit 1
    }
    python -c "import netaddr; print('✓ netaddr')" || {
        print_error "netaddr import failed"
        exit 1
    }
    python -c "import psutil; print('✓ psutil')" || {
        print_error "psutil import failed"
        exit 1
    }
    
    # Test Linux-specific package
    if [ "$OS_ID" != "windows" ]; then
        python -c "import pyvirtualdisplay; print('✓ pyvirtualdisplay')" || {
            print_error "pyvirtualdisplay import failed"
            exit 1
        }
    fi
    
    print_success "All Python packages verified"
}

# Create activation helper scripts
create_helpers() {
    print_info "Creating helper scripts..."
    
    # Create activation script
    cat > "$PROJECT_ROOT/activate-eyewitness.sh" << 'EOF'
#!/bin/bash
# EyeWitness Virtual Environment Activation Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/eyewitness-venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run setup/setup.sh first"
    exit 1
fi

echo "Activating EyeWitness virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Virtual environment activated!"
echo "Run EyeWitness with: python Python/EyeWitness.py [options]"
echo "Deactivate with: deactivate"
EOF
    
    chmod +x "$PROJECT_ROOT/activate-eyewitness.sh"
    print_success "Created activation script: activate-eyewitness.sh"
    
    # Create direct run script
    cat > "$PROJECT_ROOT/eyewitness.sh" << 'EOF'
#!/bin/bash
# EyeWitness Direct Execution Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/eyewitness-venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run setup/setup.sh first"
    exit 1
fi

# Activate venv and run EyeWitness
source "$VENV_DIR/bin/activate"
python "$SCRIPT_DIR/Python/EyeWitness.py" "$@"
EOF
    
    chmod +x "$PROJECT_ROOT/eyewitness.sh"
    print_success "Created direct execution script: eyewitness.sh"
}

# Test installation
test_installation() {
    print_info "Testing EyeWitness installation..."
    
    # Test basic functionality
    cd "$PROJECT_ROOT"
    source "$VENV_DIR/bin/activate"
    
    # Test help output
    python Python/EyeWitness.py --help &> /dev/null || {
        print_error "EyeWitness help command failed"
        return 1
    }
    
    print_success "EyeWitness installation test passed"
}

# Main installation flow
main() {
    print_info "Starting EyeWitness installation..."
    
    # Install system dependencies
    install_system_deps
    
    # Verify system dependencies
    if ! verify_system_deps; then
        print_error "System dependency verification failed"
        exit 1
    fi
    
    # Create virtual environment
    create_virtual_env
    
    # Install Python dependencies
    install_python_deps
    
    # Create helper scripts
    create_helpers
    
    # Test installation
    if ! test_installation; then
        print_error "Installation test failed"
        exit 1
    fi
    
    # Success message
    echo
    print_success "✓ EyeWitness installation completed successfully!"
    echo
    print_info "USAGE OPTIONS:"
    print_info "1. Activate environment: source activate-eyewitness.sh"
    print_info "2. Direct execution: ./eyewitness.sh [options]"
    print_info "3. Manual activation: source eyewitness-venv/bin/activate"
    echo
    print_info "TEST INSTALLATION:"
    print_info "./eyewitness.sh --single https://example.com"
    echo
    print_info "Virtual environment located at: $VENV_DIR"
    print_info "Visit https://www.redsiege.com for more Red Siege tools"
    echo
}

# Disable trap for successful completion
trap - ERR

# Execute main function
main "$@"