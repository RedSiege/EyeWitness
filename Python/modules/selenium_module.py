#!/usr/bin/env python3
"""
Chromium-based selenium module for EyeWitness
Cross-platform support for Windows, Linux, and macOS.
"""

import atexit
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
    print('[*] Run: pip list | grep selenium  to verify installation')
    # Platform-aware install hint
    import platform as _platform
    if _platform.system().lower() == 'windows':
        print('[*] Try: pip install selenium')
        print('[*] Or activate the virtual env: eyewitness-venv\\Scripts\\activate.bat')
    else:
        print('[*] Try: pip install selenium')
        print('[*] Or: sudo apt install python3-selenium  (Debian/Ubuntu)')
    sys.exit()

from modules.helpers import do_delay
from modules.platform_utils import platform_mgr
from modules.security_headers import collect_http_headers

# ── Platform-specific environment setup ──────────────────────────────────────
# Only apply Linux/headless-server env vars when actually on Linux.
# Windows has a native display and does NOT need these, and setting
# CHROME_NO_SANDBOX on Windows can silently destabilise the driver.
if platform_mgr.is_linux:
    if not os.environ.get('DISPLAY'):
        os.environ['DISPLAY'] = ':99'   # used by Xvfb / virtual display
    os.environ['CHROME_HEADLESS'] = '1'
    os.environ['CHROME_NO_SANDBOX'] = '1'


# ── Driver factory ────────────────────────────────────────────────────────────

def create_driver(cli_parsed, user_agent=None):
    """Creates a Chromium WebDriver optimised for headless operation.

    Works on Windows, Linux (including Docker/headless servers), and macOS.

    Args:
        cli_parsed: Parsed CLI arguments object.
        user_agent (str, optional): Override User-Agent string.

    Returns:
        WebDriver: A configured Selenium Chrome WebDriver instance.
    """
    try:
        options = ChromeOptions()

        # ── Headless mode ─────────────────────────────────────────────────────
        if not getattr(cli_parsed, 'show_selenium', False):
            options.add_argument('--headless=new')   # Chrome 112+ new headless

        # ── Platform-conditional stability flags ──────────────────────────────
        # --no-sandbox, --disable-dev-shm-usage and --no-zygote are Linux
        # process-model / container flags.  Passing them on Windows causes
        # ChromeDriver to complain and can crash the browser session.
        if platform_mgr.is_linux:
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')   # Linux shm fix
            options.add_argument('--no-zygote')

        # Flags that are safe on every platform
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--disable-features=VizDisplayCompositor')

        # Memory / performance
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-backgrounding-occluded-windows')

        # Window size
        width  = getattr(cli_parsed, 'width',  1920)
        height = getattr(cli_parsed, 'height', 1080)
        options.add_argument(f'--window-size={width},{height}')

        # User-Agent
        if user_agent:
            options.add_argument(f'--user-agent={user_agent}')
        elif getattr(cli_parsed, 'user_agent', None):
            options.add_argument(f'--user-agent={cli_parsed.user_agent}')

        # Reduce automation fingerprint
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.accept_insecure_certs = True

        # ── Chrome binary location ────────────────────────────────────────────
        # platform_utils.py already knows the right paths for every OS;
        # we just need to pass them through to Selenium so it never relies
        # on an ambiguous PATH lookup that fails silently on Windows.
        chrome_binary = platform_mgr.find_chromium_executable()
        if chrome_binary:
            options.binary_location = chrome_binary
            print(f'[*] Using Chrome binary: {chrome_binary}')

        # ── Windows: temporary user-data-dir ─────────────────────────────────
        # On Windows the default Chrome profile is often locked by a running
        # browser, or is a managed/work/synced profile that blocks automation.
        # A fresh temp directory avoids all of those problems.
        if platform_mgr.is_windows:
            temp_profile = tempfile.mkdtemp(prefix='ew_chrome_')
            options.add_argument(f'--user-data-dir={temp_profile}')
            # Clean up the temp directory when Python exits
            atexit.register(shutil.rmtree, temp_profile, True)
            print(f'[*] Using temporary Chrome profile: {temp_profile}')

        # ── Proxy ─────────────────────────────────────────────────────────────
        if getattr(cli_parsed, 'proxy_ip', None) and getattr(cli_parsed, 'proxy_port', None):
            proxy_type = getattr(cli_parsed, 'proxy_type', 'http')
            options.add_argument(
                f'--proxy-server={proxy_type}://{cli_parsed.proxy_ip}:{cli_parsed.proxy_port}'
            )

        # ── Temp dir (cross-platform) ─────────────────────────────────────────
        temp_dir = tempfile.gettempdir()
        os.environ['TMPDIR'] = temp_dir
        os.environ['TMP']    = temp_dir
        os.environ['TEMP']   = temp_dir

        # ── ChromeDriver service ──────────────────────────────────────────────
        service_kwargs = {}
        chromedriver_path = find_chromedriver()
        if chromedriver_path:
            service_kwargs['executable_path'] = chromedriver_path
            print(f'[*] Using ChromeDriver: {chromedriver_path}')
        else:
            # Selenium >=4.6 ships Selenium Manager which can auto-download
            # chromedriver – no explicit path needed in that case.
            print('[*] ChromeDriver not found in known locations; '
                  'relying on Selenium Manager auto-detection.')

        service = ChromeService(**service_kwargs)
        driver  = webdriver.Chrome(service=service, options=options)

        # Final setup
        driver.set_page_load_timeout(cli_parsed.timeout)
        driver.set_window_size(width, height)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        print('[+] Chrome driver initialised successfully (headless mode)')
        return driver

    except Exception as e:
        print(f'[!] Chrome WebDriver initialisation error: {e}')
        _print_driver_troubleshooting(e)
        sys.exit(1)


def _print_driver_troubleshooting(exc):
    """Print platform-appropriate troubleshooting hints after a driver error."""
    error_str = str(exc).lower()

    if platform_mgr.is_windows:
        print('\n[*] Windows troubleshooting:')
        print('    1. Verify Chrome is installed:')
        print('       C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
        print('    2. Download the matching ChromeDriver from:')
        print('       https://chromedriver.chromium.org/downloads')
        print('       or: https://googlechromelabs.github.io/chrome-for-testing/')
        print('    3. Place chromedriver.exe in one of:')
        print('       C:\\Program Files\\ChromeDriver\\chromedriver.exe')
        print('       (or add its folder to your system PATH)')
        print('    4. Alternatively, upgrade Selenium for auto-management:')
        print('       pip install --upgrade selenium')
        print('    5. Run setup script as Administrator:')
        print('       .\\setup\\setup.ps1')
        if 'chromedriver' in error_str or 'executable' in error_str:
            print('\n[!] ChromeDriver not found or version mismatch')
            print('[*] Check your Chrome version at chrome://version')
            print('[*] Download the matching chromedriver.exe')
        elif 'chrome' in error_str:
            print('\n[!] Chrome browser not found at expected location')
            print('[*] Install Google Chrome: https://www.google.com/chrome/')
    elif platform_mgr.is_mac:
        print('\n[*] macOS troubleshooting:')
        print('    - Install Chrome: brew install --cask google-chrome')
        print('    - Install chromedriver: brew install chromedriver')
        print('    - Allow chromedriver in System Preferences > Security')
        print('    - Or run the setup script: ./setup/setup.sh')
    else:
        # Linux / container
        print('\n[*] Linux troubleshooting:')
        print('    - Install Chromium: sudo apt install chromium-browser')
        print('    - Install ChromeDriver: sudo apt install chromium-chromedriver')
        print('    - Or run the setup script: sudo ./setup/setup.sh')
        if 'chromedriver' in error_str:
            print('\n[!] ChromeDriver not found or incompatible')
            print('[*] Quick fix: sudo apt install chromium-chromedriver')
        elif 'chrome' in error_str or 'chromium' in error_str:
            print('\n[!] Chrome/Chromium browser not found')
            print('[*] Quick fix: sudo apt install chromium-browser')


# ── ChromeDriver discovery ────────────────────────────────────────────────────

def find_chromedriver():
    """Find the chromedriver executable, searching PATH then known OS locations.

    Delegates to platform_utils.PlatformManager for the OS-specific path list
    so that Windows, Linux, and macOS paths are all handled correctly.

    Returns:
        str | None: Absolute path to chromedriver, or None if not found.
    """
    # 1. Check PATH first (works on all platforms; honours user customisation)
    for name in ['chromedriver', 'chromedriver.exe', 'chromium-chromedriver']:
        found = shutil.which(name)
        if found:
            return found

    # 2. Fall back to the platform-specific hardcoded locations
    for path in platform_mgr.get_chromedriver_paths():
        if path and Path(path).exists():
            return path

    return None


# ── Host capture ──────────────────────────────────────────────────────────────

def capture_host(cli_parsed, http_object, driver, ua=None):
    """Screenshot a single host and return the updated HTTP object.

    Collects HTTP headers via urllib first, then uses Selenium for the
    screenshot.

    Args:
        cli_parsed: Parsed CLI arguments.
        http_object: HTTPTableObject for the target URL.
        driver: Active Selenium WebDriver.
        ua (str, optional): Override User-Agent.

    Returns:
        tuple: (http_object, driver)
    """
    # ── Step 1: Collect HTTP headers ─────────────────────────────────────────
    print(f'[*] Collecting headers for {http_object.remote_system}')

    proxy_config = None
    if getattr(cli_parsed, 'proxy_ip', None):
        proxy_config = {
            'ip':   cli_parsed.proxy_ip,
            'port': getattr(cli_parsed, 'proxy_port', 8080),
        }

    headers, header_error = collect_http_headers(
        url=http_object.remote_system,
        timeout=getattr(cli_parsed, 'timeout', 7),
        user_agent=ua or getattr(cli_parsed, 'user_agent', None),
        proxy=proxy_config,
    )

    if headers:
        http_object.http_headers = headers
        http_object.headers = {
            k: (v[:150] + '...' if len(v) > 150 else v)
            for k, v in headers.items()
        }
        print(f'[+] Headers collected: {len(headers)} headers')
    else:
        msg = header_error or 'No headers received'
        print(f'[!] Header collection failed for {http_object.remote_system}: {msg}')
        http_object.headers = {'Header Collection': f'Failed – {msg}'}

    # ── Step 2: Selenium screenshot ───────────────────────────────────────────
    try:
        print(f'[*] Taking screenshot of {http_object.remote_system}')
        driver.get(http_object.remote_system)

        try:
            driver.implicitly_wait(3)
        except TimeoutException:
            pass

        http_object.source_code = driver.page_source.encode('utf-8')
        http_object.page_title  = driver.title

        # Persist page source
        try:
            src_bytes = http_object.source_code
            if isinstance(src_bytes, str):
                src_bytes = src_bytes.encode('utf-8')

            if getattr(http_object, 'source_path', None):
                dest = Path(http_object.source_path)
            else:
                file_name = http_object.remote_system.replace('://', '.')
                for ch in [':', '/', '?', '=', '%', '+']:
                    file_name = file_name.replace(ch, '.')
                dest = Path(cli_parsed.d) / 'source' / f'{file_name}.txt'

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src_bytes)
            http_object.source_path = str(dest)
        except Exception as exc:
            print(f'[!] Warning: failed to write page source for '
                  f'{http_object.remote_system}: {exc}')

        # Screenshot filename (safe for all OS path rules)
        import re
        safe_name = re.sub(r'^https?://', '', http_object.remote_system)
        safe_name = re.sub(r'[^a-zA-Z0-9\-\.]', '_', safe_name)[:200]
        screenshot_path = Path(cli_parsed.d) / 'screens' / f'{safe_name}.png'
        driver.save_screenshot(str(screenshot_path))
        http_object.screenshot_path = str(screenshot_path)

        print(f'[+] Captured screenshot: {http_object.remote_system}')

    except TimeoutException:
        print(f'[*] Timeout connecting to {http_object.remote_system}')
        driver.quit()
        driver = create_driver(cli_parsed, ua)
        http_object.error_state = 'Timeout'

    except Exception as exc:
        error_msg = str(exc).lower()

        if 'net::err_connection_reset' in error_msg:
            print(f'[*] Connection reset by {http_object.remote_system}')
            http_object.error_state = 'Connection Reset'
        elif 'net::err_connection_refused' in error_msg:
            print(f'[*] Connection refused by {http_object.remote_system}')
            http_object.error_state = 'Connection Refused'
        elif 'net::err_timed_out' in error_msg or 'timeout' in error_msg:
            print(f'[*] Timeout connecting to {http_object.remote_system}')
            http_object.error_state = 'Timeout'
        elif 'net::err_name_not_resolved' in error_msg:
            print(f'[*] DNS resolution failed for {http_object.remote_system}')
            http_object.error_state = 'DNS Failed'
        elif 'net::err_cert_' in error_msg or 'certificate' in error_msg:
            print(f'[*] SSL/Certificate error for {http_object.remote_system}')
            http_object.error_state = 'SSL Error'
        elif 'chrome not reachable' in error_msg or 'session deleted' in error_msg:
            print(f'[*] Chrome driver crashed – restarting')
            http_object.error_state = 'Driver Crashed'
            try:
                driver.quit()
            except Exception:
                pass
            driver = create_driver(cli_parsed, ua)
            return http_object, driver
        else:
            print(f'[*] Error capturing {http_object.remote_system}: {exc}')
            http_object.error_state = 'Error'

        # Check whether the driver is still alive
        try:
            driver.get('about:blank')
        except Exception:
            print('[*] Chrome driver became unresponsive – restarting')
            try:
                driver.quit()
            except Exception:
                pass
            driver = create_driver(cli_parsed, ua)

    return http_object, driver


# ── Browser availability helpers ──────────────────────────────────────────────

def check_browsers_available():
    """Check whether a usable Chrome/Chromium binary and ChromeDriver exist.

    Returns:
        dict: {browsers: list[str], chromedriver: bool, ready: bool}
    """
    browsers = []

    # Ask platform_mgr for the canonical browser path first
    chromium_exe = platform_mgr.find_chromium_executable()
    if chromium_exe:
        browsers.append(chromium_exe)

    # Also sweep PATH for well-known binary names (platform-aware)
    if platform_mgr.is_windows:
        path_names = ['chrome', 'chrome.exe']
    elif platform_mgr.is_mac:
        path_names = ['google-chrome', 'chromium']
    else:
        path_names = ['google-chrome', 'chromium-browser', 'chromium']

    for name in path_names:
        found = shutil.which(name)
        if found and found not in browsers:
            browsers.append(found)

    # Sweep the hardcoded OS paths from platform_mgr
    for path in platform_mgr.get_chromium_paths():
        if Path(path).exists() and path not in browsers:
            browsers.append(path)

    chromedriver_available = find_chromedriver() is not None

    return {
        'browsers':    browsers,
        'chromedriver': chromedriver_available,
        'ready':       bool(browsers) and chromedriver_available,
    }


def get_browser_info():
    """Print a human-readable summary of the browser setup."""
    status = check_browsers_available()

    print('[*] Browser status:')
    if status['browsers']:
        for b in status['browsers']:
            print(f'    Browser  : {b}')
    else:
        print('    Browser  : None found')
    print(f"    ChromeDriver: {'Available' if status['chromedriver'] else 'Missing'}")
    print(f"    Ready for screenshots: {'Yes' if status['ready'] else 'No'}")

    if not status['ready']:
        if platform_mgr.is_windows:
            print('[*] Install Chrome and ChromeDriver, then re-run the setup script:')
            print('    .\\setup\\setup.ps1')
        else:
            print('[*] Run setup script to install: sudo ./setup/setup.sh')

    return status
