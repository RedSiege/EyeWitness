#!/usr/bin/env python3
"""Chrome/Chromium driver support for EyeWitness"""

import os
import shutil
import sys
from pathlib import Path

def create_chrome_driver(cli_parsed, user_agent=None):
    """Creates a selenium ChromeDriver
    
    Args:
        cli_parsed (ArgumentParser): Command Line Object
        user_agent (String, optional): Optional user-agent string
        
    Returns:
        ChromeDriver: Selenium Chrome Webdriver
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    
    try:
        options = ChromeOptions()
        
        # Essential headless options
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')
        
        # Window size
        width = getattr(cli_parsed, 'width', 1920)
        height = getattr(cli_parsed, 'height', 1080)
        options.add_argument(f'--window-size={width},{height}')
        
        # User agent
        if user_agent:
            options.add_argument(f'--user-agent={user_agent}')
        elif hasattr(cli_parsed, 'user_agent') and cli_parsed.user_agent:
            options.add_argument(f'--user-agent={cli_parsed.user_agent}')
        
        # Disable automation indicators
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Find chromedriver
        service_kwargs = {}
        
        # Try to find chromedriver in PATH
        chromedriver_path = shutil.which('chromedriver')
        if chromedriver_path:
            service_kwargs['executable_path'] = chromedriver_path
        
        service = ChromeService(**service_kwargs)
        
        # Create driver
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(cli_parsed.timeout)
        
        # Remove automation indicators
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        print(f'[!] Chrome WebDriver initialization error: {e}')
        print('[*] Troubleshooting tips:')
        print('    - Ensure Chrome/Chromium is installed: sudo apt install chromium-browser')
        print('    - Install chromedriver: sudo apt install chromium-chromedriver')
        print('    - Or download from: https://chromedriver.chromium.org/')
        return None


def detect_available_browsers():
    """Detect which browsers are available on the system"""
    browsers = {}
    
    # Check for Chrome/Chromium
    for browser in ['google-chrome', 'chromium-browser', 'chromium']:
        if shutil.which(browser):
            browsers['chrome'] = browser
            break
    
    # Check for Firefox
    for browser in ['firefox', 'firefox-esr']:
        if shutil.which(browser):
            browsers['firefox'] = browser
            break
    
    # Check for drivers
    drivers = {}
    if shutil.which('chromedriver'):
        drivers['chrome'] = 'chromedriver'
    if shutil.which('geckodriver'):
        drivers['firefox'] = 'geckodriver'
    
    return browsers, drivers


def get_preferred_browser():
    """Get the preferred browser based on what's available and reliable"""
    browsers, drivers = detect_available_browsers()
    
    # Prefer Chrome/Chromium if available (more reliable, easier install)
    if 'chrome' in browsers and 'chrome' in drivers:
        return 'chrome'
    
    # Fall back to Firefox if Chrome not available
    if 'firefox' in browsers and 'firefox' in drivers:
        return 'firefox'
    
    return None