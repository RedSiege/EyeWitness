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
    
    def clear_screen(self):
        os.system('cls' if self.is_windows else 'clear')
    
    def get_firefox_paths(self):
        # common firefox install locations
        if self.is_windows:
            paths = [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
            ]
            # also check user dirs
            home = Path.home()
            paths.extend([
                str(home / "AppData" / "Local" / "Mozilla Firefox" / "firefox.exe"),
                str(home / "AppData" / "Roaming" / "Mozilla Firefox" / "firefox.exe")
            ])
            return paths
        elif self.is_linux:
            return [
                "/usr/bin/firefox",
                "/usr/bin/firefox-esr", 
                "/opt/firefox/firefox",
                "/snap/bin/firefox",
                "/usr/local/bin/firefox"
            ]
        elif self.is_mac:
            return [
                "/Applications/Firefox.app/Contents/MacOS/firefox",
                str(Path.home() / "Applications" / "Firefox.app" / "Contents" / "MacOS" / "firefox")
            ]
        return []
    
    def find_firefox_executable(self):
        # check PATH first
        for name in ['firefox', 'firefox-esr']:
            path = shutil.which(name)
            if path:
                # Check if it's a snap package (problematic for Selenium)
                if '/snap/' in path or path.startswith('/snap'):
                    print('[!] Warning: Firefox is installed as a snap package')
                    print('[!] Snap Firefox often causes issues with Selenium/Geckodriver')
                    print('[*] Run: sudo /opt/tools/EyeWitness/setup/fix-firefox-snap.sh')
                    # Still return it, but user is warned
                return path
        
        # fallback to hardcoded paths
        for path in self.get_firefox_paths():
            if Path(path).exists():
                return path
        
        return None
    
    def get_geckodriver_suffix(self):
        return '.exe' if self.is_windows else ''
    
    def get_geckodriver_download_info(self):
        # figure out which geckodriver to download
        if self.is_windows:
            arch = 'win64' if 'amd64' in self.machine or 'x86_64' in self.machine else 'win32'
            return f'{arch}.zip', 'zip'
        elif self.is_linux:
            if 'aarch64' in self.machine or 'arm64' in self.machine:
                arch = 'linux-aarch64'
            elif 'x86_64' in self.machine:
                arch = 'linux64'
            else:
                arch = 'linux32'
            return f'{arch}.tar.gz', 'tar.gz'
        elif self.is_mac:
            arch = 'macos-aarch64' if 'arm64' in self.machine else 'macos'
            return f'{arch}.tar.gz', 'tar.gz'
        
        return None, None
    
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
                'firefox': 'choco install firefox -y',
                'python': 'choco install python -y',
                'git': 'choco install git -y'
            }
        elif self.is_linux:
            # Detect Linux distribution
            if shutil.which('apt-get'):  # Debian/Ubuntu
                return {
                    'firefox': 'sudo apt-get install -y firefox-esr',
                    'xvfb': 'sudo apt-get install -y xvfb',
                    'python': 'sudo apt-get install -y python3 python3-pip python3-dev',
                    'tools': 'sudo apt-get install -y wget curl jq cmake'
                }
            elif shutil.which('yum'):  # CentOS/RHEL/Fedora
                return {
                    'firefox': 'sudo yum install -y firefox',
                    'xvfb': 'sudo yum install -y xorg-x11-server-Xvfb',
                    'python': 'sudo yum install -y python3 python3-pip python3-devel',
                    'tools': 'sudo yum install -y wget curl jq cmake'
                }
            elif shutil.which('pacman'):  # Arch
                return {
                    'firefox': 'sudo pacman -S firefox --noconfirm',
                    'xvfb': 'sudo pacman -S xorg-server-xvfb --noconfirm',
                    'python': 'sudo pacman -S python python-pip --noconfirm',
                    'tools': 'sudo pacman -S wget curl jq cmake --noconfirm'
                }
        elif self.is_mac:
            return {
                'firefox': 'brew install --cask firefox',
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
            'firefox_found': self.find_firefox_executable() is not None,
            'virtual_display_available': self.can_use_virtual_display(),
            'virtual_display_needed': self.needs_virtual_display(),
            'admin_privileges': self.is_admin,
            'issues': []
        }
        
        # Check for common issues
        if not status['firefox_found']:
            status['issues'].append('Firefox not found - install Firefox browser')
        
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
        
        firefox = self.find_firefox_executable()
        print(f"Firefox: {firefox if firefox else 'Not found'}")
        
        validation = self.validate_environment()
        if validation['issues']:
            print("\nIssues found:")
            for issue in validation['issues']:
                print(f"  - {issue}")


def setup_virtual_display(platform_mgr: PlatformManager, show_selenium: bool = False):
    """Setup virtual display with proper cross-platform handling"""
    if not platform_mgr.needs_virtual_display() or show_selenium:
        return None
    
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
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        return display
    except ImportError:
        print('[*] Warning: pyvirtualdisplay package not found')
        print('[*] Install with: pip install pyvirtualdisplay')
        return None
    except Exception as e:
        print(f'[*] Warning: Could not start virtual display: {e}')
        print('[*] Continuing in headless mode...')
        return None


# Global platform manager instance
platform_mgr = PlatformManager()


if __name__ == "__main__":
    # Testing/diagnostic mode
    print("EyeWitness Platform Detection")
    print("=" * 40)
    platform_mgr.print_environment_info()