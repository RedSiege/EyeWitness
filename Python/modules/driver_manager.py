#!/usr/bin/env python3
# gecko driver auto-download stuff

import os
import sys
import shutil
import zipfile
import tarfile
import tempfile
import requests
from pathlib import Path

from modules.platform_utils import platform_mgr


class DriverManager:
    # downloads and manages geckodriver automatically
    
    def __init__(self):
        self.platform_mgr = platform_mgr
        self.driver_name = f"geckodriver{self.platform_mgr.get_geckodriver_suffix()}"
        self.github_api_url = "https://api.github.com/repos/mozilla/geckodriver/releases/latest"
        
    def find_geckodriver(self):
        """Find geckodriver executable in system PATH or common locations"""
        # First check if it's in PATH
        driver_path = shutil.which('geckodriver')
        if driver_path:
            return driver_path
        
        # Check common installation locations
        common_paths = self._get_common_driver_paths()
        for path in common_paths:
            full_path = Path(path) / self.driver_name
            if full_path.exists() and full_path.is_file():
                return str(full_path)
        
        return None
    
    def _get_common_driver_paths(self):
        """Get common geckodriver installation paths for current platform"""
        if self.platform_mgr.is_windows:
            return [
                "C:\\Windows\\System32",
                "C:\\Windows",
                str(Path.home() / "AppData" / "Local" / "bin"),
                str(Path.cwd()),
                "C:\\Program Files\\Mozilla Firefox",
                "C:\\Program Files (x86)\\Mozilla Firefox"
            ]
        elif self.platform_mgr.is_linux:
            return [
                "/usr/local/bin",
                "/usr/bin",
                "/bin",
                str(Path.home() / ".local" / "bin"),
                str(Path.cwd()),
                "/opt/geckodriver"
            ]
        elif self.platform_mgr.is_mac:
            return [
                "/usr/local/bin",
                "/usr/bin",
                "/bin",
                str(Path.home() / ".local" / "bin"),
                str(Path.cwd()),
                "/Applications/Firefox.app/Contents/MacOS"
            ]
        return []
    
    def get_latest_version(self):
        """Get the latest geckodriver version from GitHub API"""
        try:
            response = requests.get(self.github_api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('tag_name', '').lstrip('v')
        except Exception as e:
            print(f"[*] Warning: Could not fetch latest geckodriver version: {e}")
            return None
    
    def get_installed_version(self):
        """Get the version of currently installed geckodriver"""
        driver_path = self.find_geckodriver()
        if not driver_path:
            return None
        
        try:
            import subprocess
            result = subprocess.run(
                [driver_path, '--version'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                # Parse version from output like "geckodriver 0.33.0 (abc123)"
                output = result.stdout.strip()
                if 'geckodriver' in output:
                    parts = output.split()
                    if len(parts) >= 2:
                        return parts[1]
            return None
        except Exception:
            return None
    
    def download_geckodriver(self, version=None, install_path=None):
        """Download and install geckodriver for current platform"""
        if version is None:
            version = self.get_latest_version()
            if not version:
                print("[*] Error: Could not determine geckodriver version to download")
                return False
        
        # Get platform-specific download info
        platform_suffix, archive_type = self.platform_mgr.get_geckodriver_download_info()
        if not platform_suffix:
            print(f"[*] Error: Unsupported platform: {self.platform_mgr.system}")
            return False
        
        # Construct download URL
        filename = f"geckodriver-v{version}-{platform_suffix}"
        download_url = f"https://github.com/mozilla/geckodriver/releases/download/v{version}/{filename}"
        
        print(f"[*] Downloading geckodriver v{version} for {self.platform_mgr.system}...")
        
        try:
            # Download the archive
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{archive_type}') as tmp_file:
                response = requests.get(download_url, stream=True, timeout=30)
                response.raise_for_status()
                
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                
                tmp_file_path = tmp_file.name
            
            # Extract the archive
            extracted_path = self._extract_archive(tmp_file_path, archive_type)
            if not extracted_path:
                return False
            
            # Install to appropriate location
            success = self._install_driver(extracted_path, install_path)
            
            # Cleanup
            os.unlink(tmp_file_path)
            if extracted_path != tmp_file_path:
                shutil.rmtree(os.path.dirname(extracted_path), ignore_errors=True)
            
            if success:
                print(f"[*] Successfully installed geckodriver v{version}")
            return success
            
        except Exception as e:
            print(f"[*] Error downloading geckodriver: {e}")
            return False
    
    def _extract_archive(self, archive_path, archive_type):
        """Extract geckodriver from archive"""
        try:
            extract_dir = tempfile.mkdtemp()
            
            if archive_type == 'zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif archive_type == 'tar.gz':
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                print(f"[*] Error: Unsupported archive type: {archive_type}")
                return None
            
            # Find the geckodriver executable
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.startswith('geckodriver'):
                        return os.path.join(root, file)
            
            print("[*] Error: geckodriver executable not found in archive")
            return None
            
        except Exception as e:
            print(f"[*] Error extracting archive: {e}")
            return None
    
    def _install_driver(self, driver_path, install_path=None):
        """Install geckodriver to system location"""
        if install_path is None:
            # Choose default install location based on platform
            if self.platform_mgr.is_windows:
                if self.platform_mgr.is_admin:
                    install_path = "C:\\Windows\\System32"
                else:
                    install_path = str(Path.home() / "AppData" / "Local" / "bin")
                    os.makedirs(install_path, exist_ok=True)
            else:
                if self.platform_mgr.is_admin:
                    install_path = "/usr/local/bin"
                else:
                    install_path = str(Path.home() / ".local" / "bin")
                    os.makedirs(install_path, exist_ok=True)
        
        try:
            dest_path = Path(install_path) / self.driver_name
            shutil.copy2(driver_path, dest_path)
            
            # Make executable on Unix systems
            if not self.platform_mgr.is_windows:
                os.chmod(dest_path, 0o755)
            
            print(f"[*] Installed geckodriver to: {dest_path}")
            return True
            
        except PermissionError:
            print(f"[*] Error: Permission denied installing to {install_path}")
            if not self.platform_mgr.is_admin:
                print("[*] Try running with administrator/sudo privileges")
            return False
        except Exception as e:
            print(f"[*] Error installing geckodriver: {e}")
            return False
    
    def update_geckodriver(self):
        """Update geckodriver to latest version if newer version available"""
        current_version = self.get_installed_version()
        latest_version = self.get_latest_version()
        
        if not latest_version:
            print("[*] Could not check for geckodriver updates")
            return False
        
        if not current_version:
            print(f"[*] Installing geckodriver v{latest_version} (not currently installed)")
            return self.download_geckodriver(latest_version)
        
        if current_version == latest_version:
            print(f"[*] geckodriver v{current_version} is already up to date")
            return True
        
        print(f"[*] Updating geckodriver from v{current_version} to v{latest_version}")
        return self.download_geckodriver(latest_version)
    
    def validate_installation(self):
        """Validate geckodriver installation and return status"""
        driver_path = self.find_geckodriver()
        version = self.get_installed_version()
        
        status = {
            'installed': driver_path is not None,
            'path': driver_path,
            'version': version,
            'in_path': shutil.which('geckodriver') is not None,
            'executable': False,
            'issues': []
        }
        
        if driver_path:
            try:
                # Test if executable works
                import subprocess
                result = subprocess.run(
                    [driver_path, '--version'], 
                    capture_output=True, 
                    timeout=5
                )
                status['executable'] = result.returncode == 0
            except Exception:
                status['executable'] = False
        
        # Identify issues
        if not status['installed']:
            status['issues'].append('geckodriver not found - install with setup script or download manually')
        elif not status['executable']:
            status['issues'].append('geckodriver found but not executable - check permissions')
        elif not status['in_path']:
            status['issues'].append('geckodriver found but not in PATH - may cause issues')
        
        return status
    
    def print_status(self):
        """Print geckodriver installation status"""
        status = self.validate_installation()
        
        print("Geckodriver Status:")
        print(f"  Installed: {'Yes' if status['installed'] else 'No'}")
        if status['path']:
            print(f"  Path: {status['path']}")
        if status['version']:
            print(f"  Version: {status['version']}")
        print(f"  In PATH: {'Yes' if status['in_path'] else 'No'}")
        print(f"  Executable: {'Yes' if status['executable'] else 'No'}")
        
        if status['issues']:
            print("  Issues:")
            for issue in status['issues']:
                print(f"    - {issue}")


# Global driver manager instance
driver_mgr = DriverManager()


if __name__ == "__main__":
    # Command-line interface for driver management
    import argparse
    
    parser = argparse.ArgumentParser(description="EyeWitness Driver Manager")
    parser.add_argument('--status', action='store_true', help='Show geckodriver status')
    parser.add_argument('--install', action='store_true', help='Install/update geckodriver')
    parser.add_argument('--version', help='Install specific geckodriver version')
    parser.add_argument('--path', help='Install to specific path')
    
    args = parser.parse_args()
    
    if args.status:
        driver_mgr.print_status()
    elif args.install:
        success = driver_mgr.download_geckodriver(args.version, args.path)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()