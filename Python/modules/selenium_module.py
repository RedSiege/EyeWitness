#!/usr/bin/env python3
"""
Chromium-based selenium module for EyeWitness
Simplified single-browser approach using Chrome/Chromium headless
"""

import http.client
import os
import socket
import sys
import urllib.request
import urllib.error
import ssl
import shutil
import tempfile
from pathlib import Path

try:
    from ssl import CertificateError as sslerr
except ImportError:
    from ssl import SSLError as sslerr

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.common.exceptions import NoAlertPresentException
    from selenium.common.exceptions import TimeoutException
    from selenium.common.exceptions import UnexpectedAlertPresentException
    from selenium.common.exceptions import WebDriverException
except ImportError:
    print('[*] Selenium not found.')
    print('[*] Run pip list to verify installation')
    print('[*] Try: sudo apt install python3-selenium')
    sys.exit()

from modules.helpers import do_delay
from modules.platform_utils import platform_mgr

# Platform-specific environment configuration for headless operation
if platform_mgr.is_linux:
    # Optimize for headless Linux servers
    os.environ['DISPLAY'] = ':99'  # Virtual display
    os.environ['CHROME_HEADLESS'] = '1'
    os.environ['CHROME_NO_SANDBOX'] = '1'


def create_driver(cli_parsed, user_agent=None):
    """Creates a Chromium WebDriver optimized for headless operation
    
    Args:
        cli_parsed (ArgumentParser): Command Line Object
        user_agent (String, optional): Optional user-agent string
        
    Returns:
        ChromeDriver: Selenium Chrome Webdriver
    """
    try:
        options = ChromeOptions()
        
        # Essential headless configuration
        options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Memory and performance optimization
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--no-zygote')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-backgrounding-occluded-windows')
        
        # Window size configuration
        width = getattr(cli_parsed, 'width', 1920)
        height = getattr(cli_parsed, 'height', 1080)
        options.add_argument(f'--window-size={width},{height}')
        
        # User agent configuration
        if user_agent:
            options.add_argument(f'--user-agent={user_agent}')
        elif hasattr(cli_parsed, 'user_agent') and cli_parsed.user_agent:
            options.add_argument(f'--user-agent={cli_parsed.user_agent}')
        
        # Disable automation detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Security and certificate handling
        options.accept_insecure_certs = True
        
        # Setup Chrome service
        service_kwargs = {}
        
        # Find chromedriver automatically
        chromedriver_path = find_chromedriver()
        if chromedriver_path:
            service_kwargs['executable_path'] = chromedriver_path
        
        # Configure temp directory for better compatibility
        temp_dir = tempfile.gettempdir()
        os.environ['TMPDIR'] = temp_dir
        os.environ['TMP'] = temp_dir
        os.environ['TEMP'] = temp_dir
        
        service = ChromeService(**service_kwargs)
        
        # Create Chrome driver
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set timeouts and window size
        driver.set_page_load_timeout(cli_parsed.timeout)
        driver.set_window_size(width, height)
        
        # Remove automation indicators
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f'[+] Chrome driver initialized successfully (headless mode)')
        return driver
        
    except Exception as e:
        from modules.troubleshooting import get_error_guidance
        print(f'[!] Chrome WebDriver initialization error: {e}')
        print('[*] Troubleshooting tips:')
        print('    - Ensure Chromium is installed: sudo apt install chromium-browser')
        print('    - Install chromedriver: sudo apt install chromium-chromedriver')
        print('    - Run the setup script: sudo ./setup/setup.sh')
        
        # Special handling for common Chrome errors
        error_str = str(e).lower()
        if 'chromedriver' in error_str:
            print('\n[!] ChromeDriver not found or incompatible')
            print('[*] Quick fix: sudo apt install chromium-chromedriver')
        elif 'chrome' in error_str or 'chromium' in error_str:
            print('\n[!] Chrome/Chromium browser not found')
            print('[*] Quick fix: sudo apt install chromium-browser')
            
        sys.exit(1)


def find_chromedriver():
    """Find chromedriver executable in various locations"""
    # Common chromedriver locations
    possible_paths = [
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver',
        '/snap/bin/chromium.chromedriver',
        shutil.which('chromedriver'),
        shutil.which('chromium-chromedriver'),
    ]
    
    for path in possible_paths:
        if path and Path(path).exists():
            return path
    
    return None


def capture_host(cli_parsed, http_object, driver, ua=None):
    """Screenshots a single host using Chrome and returns updated HTTP Object
    
    Args:
        cli_parsed (ArgumentParser): Command Line Object  
        http_object (HTTPObject): HTTP Object
        driver (WebDriver): Selenium WebDriver
        ua (str, optional): User agent string
        
    Returns:
        tuple: (HTTPObject, WebDriver) Updated objects
    """
    return_status = False
    
    try:
        driver.get(http_object.remote_system)
        
        # Handle page load timeout
        try:
            # Wait for page to load
            driver.implicitly_wait(3)
        except TimeoutException:
            pass  # Continue with screenshot anyway
            
        # Capture screenshot
        http_object.source = driver.page_source.encode('utf-8')
        http_object.page_title = driver.title
        
        # Take screenshot
        screenshot_path = Path(cli_parsed.d) / 'screens' / f'{http_object.remote_system.replace(":", "_").replace("/", "_")}.png'
        driver.save_screenshot(str(screenshot_path))
        http_object.screenshot_path = str(screenshot_path)
        
        print(f'[+] Captured: {http_object.remote_system}')
        
    except TimeoutException:
        print(f'[*] Timeout connecting to {http_object.remote_system}')
        driver.quit()
        driver = create_driver(cli_parsed, ua)
        http_object.error_state = 'Timeout'
        
    except Exception as e:
        print(f'[*] Error capturing {http_object.remote_system}: {e}')
        http_object.error_state = 'Error'
        
        # Recreate driver if it becomes unusable
        try:
            driver.get('about:blank')
        except:
            driver.quit()
            driver = create_driver(cli_parsed, ua)
    
    return http_object, driver


def check_browsers_available():
    """Check if Chrome/Chromium is available"""
    browsers = []
    
    # Check for Chrome/Chromium binaries
    for browser in ['google-chrome', 'chromium-browser', 'chromium']:
        if shutil.which(browser):
            browsers.append(browser)
    
    # Check for chromedriver
    chromedriver_available = find_chromedriver() is not None
    
    return {
        'browsers': browsers,
        'chromedriver': chromedriver_available,
        'ready': len(browsers) > 0 and chromedriver_available
    }


def get_browser_info():
    """Get information about the browser setup"""
    status = check_browsers_available()
    
    print(f"[*] Browser Status:")
    print(f"    Available browsers: {', '.join(status['browsers']) if status['browsers'] else 'None'}")
    print(f"    ChromeDriver: {'Available' if status['chromedriver'] else 'Missing'}")
    print(f"    Ready for screenshots: {'Yes' if status['ready'] else 'No'}")
    
    if not status['ready']:
        print("[*] Run setup script to install: sudo ./setup/setup.sh")
    
    return status