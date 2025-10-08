#!/usr/bin/env python3
# Platform detection stuff - got tired of hardcoding paths everywhere

import platform
import os
import sys
import shutil
import subprocess
from pathlib import Path


class PlatformManager:
    # Handles OS differences so we don't have to check platform.system() everywhere
    
    def __init__(self):
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.is_windows = self.system == 'windows'
        self.is_linux = self.system == 'linux' 
        self.is_mac = self.system == 'darwin'
        self.is_unix = self.is_linux or self.is_mac
        self.is_docker = self._check_docker_environment()
        
        self.has_display = self._check_display_available()
        self.is_admin = self._check_admin_privileges()
        
    def _check_display_available(self):
        if self.is_windows:
            return True  # windows always has display
        else:
            return os.environ.get('DISPLAY') is not None
    
    def _check_admin_privileges(self):
        try:
            if self.is_windows:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except (AttributeError, OSError):
            return False
    
    def _check_docker_environment(self):
        """Check if running inside Docker container"""
        # Multiple ways to detect Docker environment
        docker_indicators = [
            # Check for .dockerenv file
            os.path.exists("/.dockerenv"),
            # Check if cgroup contains docker
            self._check_cgroup_docker(),
            # Check environment variables set by Docker
            os.environ.get("DOCKER_CONTAINER") == "1",
            # Check for common Docker networking
            self._check_docker_networking()
        ]
        return any(docker_indicators)

    def _check_cgroup_docker(self):
        """Check if cgroup indicates Docker"""
        try:
            with open("/proc/1/cgroup", "r") as f:
                content = f.read()
                return "docker" in content.lower() or "containerd" in content.lower()
        except (IOError, OSError):
            return False

    def _check_docker_networking(self):
        """Check for Docker-specific networking indicators"""
        try:
            # Docker often uses these hostname patterns
            hostname = os.environ.get("HOSTNAME", "")
            return len(hostname) == 12 and hostname.isalnum()
        except:
            return False

    def clear_screen(self):
        os.system('cls' if self.is_windows else 'clear')
    
    def get_chromium_paths(self):
        # common chromium install locations
        if self.is_windows:
            paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            # also check user dirs
            home = Path.home()
            paths.extend([
                str(home / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"),
                str(home / "AppData" / "Local" / "Chromium" / "Application" / "chrome.exe")
            ])
            return paths
        elif self.is_linux:
            return [
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/usr/bin/google-chrome",
                "/opt/google/chrome/chrome",
                "/snap/bin/chromium",
                "/usr/local/bin/chromium"
            ]
        elif self.is_mac:
            return [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                str(Path.home() / "Applications" / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome")
            ]
        return []
    
    def find_chromium_executable(self):
        # check PATH first
        for name in ['chromium-browser', 'chromium', 'google-chrome']:
            path = shutil.which(name)
            if path:
                return path
        
        # fallback to hardcoded paths
        for path in self.get_chromium_paths():
            if Path(path).exists():
                return path
        
        return None
    
    def get_chromedriver_paths(self):
        # common chromedriver install locations
        if self.is_windows:
            return [
                r"C:\Program Files\ChromeDriver\chromedriver.exe",
                r"C:\Program Files (x86)\ChromeDriver\chromedriver.exe",
                str(Path.home() / "AppData" / "Local" / "ChromeDriver" / "chromedriver.exe")
            ]
        elif self.is_linux:
            return [
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver",
                "/snap/bin/chromium.chromedriver",
                "/usr/lib/chromium-browser/chromedriver"
            ]
        elif self.is_mac:
            return [
                "/usr/local/bin/chromedriver",
                "/opt/homebrew/bin/chromedriver",
                str(Path.home() / "Applications" / "chromedriver")
            ]
        return []
    
    def needs_virtual_display(self):
        # windows has native headless, unix needs xvfb if no display
        return not self.is_windows and not self.has_display
    
    def can_use_virtual_display(self) -> bool:
        """Check if virtual display can be used on this platform"""
        if self.is_windows:
            return False  # Not supported on Windows
        
        try:
            # Check if pyvirtualdisplay is available
            import pyvirtualdisplay
            # Check if Xvfb is available
            return shutil.which('Xvfb') is not None
        except ImportError:
            return False
    
    def get_system_install_commands(self) -> dict:
        """Get system package installation commands for current platform"""
        if self.is_windows:
            return {
                'chrome': 'choco install googlechrome -y',
                'python': 'choco install python -y',
                'git': 'choco install git -y'
            }
        elif self.is_linux:
            # Detect Linux distribution
            if shutil.which('apt-get'):  # Debian/Ubuntu
                return {
                    'chromium': 'sudo apt-get install -y chromium-browser chromium-chromedriver',
                    'xvfb': 'sudo apt-get install -y xvfb',
                    'python': 'sudo apt-get install -y python3 python3-pip python3-dev',
                    'tools': 'sudo apt-get install -y wget curl jq cmake'
                }
            elif shutil.which('yum'):  # CentOS/RHEL/Fedora
                return {
                    'chromium': 'sudo yum install -y chromium chromedriver',
                    'xvfb': 'sudo yum install -y xorg-x11-server-Xvfb',
                    'python': 'sudo yum install -y python3 python3-pip python3-devel',
                    'tools': 'sudo yum install -y wget curl jq cmake'
                }
            elif shutil.which('pacman'):  # Arch
                return {
                    'chromium': 'sudo pacman -S chromium --noconfirm',
                    'xvfb': 'sudo pacman -S xorg-server-xvfb --noconfirm',
                    'python': 'sudo pacman -S python python-pip --noconfirm',
                    'tools': 'sudo pacman -S wget curl jq cmake --noconfirm'
                }
        elif self.is_mac:
            return {
                'chrome': 'brew install --cask google-chrome',
                'python': 'brew install python',
                'tools': 'brew install wget curl jq cmake'
            }
        
        return {}
    
    def get_requirements_file(self) -> str:
        """Get appropriate requirements file for current platform"""
        if self.is_windows:
            return 'requirements-windows.txt'
        else:
            return 'requirements-unix.txt'
    
    def validate_environment(self) -> dict:
        """Validate the current environment and return status"""
        status = {
            'platform': self.system,
            'python_version': sys.version,
            'chromium_found': self.find_chromium_executable() is not None,
            'virtual_display_available': self.can_use_virtual_display(),
            'virtual_display_needed': self.needs_virtual_display(),
            'admin_privileges': self.is_admin,
            'issues': []
        }
        
        # Check for common issues
        if not status['chromium_found']:
            status['issues'].append('Chromium not found - install Chromium browser')
        
        if self.needs_virtual_display() and not self.can_use_virtual_display():
            status['issues'].append('Virtual display needed but not available - install xvfb and pyvirtualdisplay')
        
        return status
    
    def print_environment_info(self) -> None:
        """Print detailed environment information"""
        print(f"Platform: {self.system.title()} ({self.machine})")
        print(f"Python: {sys.version}")
        print(f"Admin privileges: {self.is_admin}")
        print(f"Display available: {self.has_display}")
        print(f"Virtual display needed: {self.needs_virtual_display()}")
        print(f"Virtual display available: {self.can_use_virtual_display()}")
        
        chromium = self.find_chromium_executable()
        print(f"Chromium: {chromium if chromium else 'Not found'}")
        
        validation = self.validate_environment()
        if validation['issues']:
            print("\nIssues found:")
            for issue in validation['issues']:
                print(f"  - {issue}")


def setup_virtual_display(platform_mgr: PlatformManager, show_selenium: bool = False):
    """Setup virtual display with proper cross-platform and Docker handling"""
    if not platform_mgr.needs_virtual_display() or show_selenium:
        return None
    
    # Docker-specific handling: If we're in Docker and DISPLAY is already set,
    # assume Xvfb is already running from the entrypoint script
    if platform_mgr.is_docker:
        display_env = os.environ.get('DISPLAY')
        if display_env:
            print(f'[*] Docker environment detected with DISPLAY={display_env}')
            print('[*] Using existing virtual display from Docker entrypoint')
            return None  # Don't start our own display
        else:
            print('[*] Docker environment detected but no DISPLAY set')
            print('[*] Will attempt to start virtual display')
    
    if not platform_mgr.can_use_virtual_display():
        if platform_mgr.is_windows:
            # Windows doesn't need virtual display
            return None
        else:
            print('[*] Warning: Virtual display needed but not available')
            print('[*] Install with: sudo apt-get install xvfb (Debian/Ubuntu)')
            print('[*] Or run with --show-selenium flag')
            return None
    
    try:
        from pyvirtualdisplay import Display
        # In Docker, if we get here, try to use a different display number
        # to avoid conflicts with existing Xvfb
        display_num = ':1' if platform_mgr.is_docker else ':0'
        display = Display(visible=0, size=(1920, 1080), display=display_num)
        display.start()
        print(f'[*] Started virtual display on {display_num}')
        return display
    except ImportError:
        print('[*] Warning: pyvirtualdisplay package not found')
        print('[*] Install with: pip install pyvirtualdisplay')
        return None
    except Exception as e:
        print(f'[*] Warning: Could not start virtual display: {e}')
        if platform_mgr.is_docker:
            print('[*] Docker: Assuming existing Xvfb is available')
        print('[*] Continuing in headless mode...')
        return None


# Global platform manager instance
platform_mgr = PlatformManager()


if __name__ == "__main__":
    # Testing/diagnostic mode
    print("EyeWitness Platform Detection")
    print("=" * 40)
    platform_mgr.print_environment_info()
