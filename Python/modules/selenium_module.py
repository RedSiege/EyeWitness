import http.client
import os
import socket
import sys
import urllib.request
import urllib.error
import ssl
from pathlib import Path

try:
    from ssl import CertificateError as sslerr
except:
    from ssl import SSLError as sslerr

try:
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.common.exceptions import NoAlertPresentException
    from selenium.common.exceptions import TimeoutException
    from selenium.common.exceptions import UnexpectedAlertPresentException
    from selenium.common.exceptions import WebDriverException
    # DesiredCapabilities is deprecated - capabilities now handled via Options
except ImportError:
    print('[*] Selenium not found.')
    print('[*] Please run the script in the setup directory!')
    sys.exit()

from modules.helpers import do_delay
from modules.platform_utils import platform_mgr

# Platform-specific Selenium Manager configuration
if platform_mgr.is_linux:
    # On Linux, disable Selenium Manager to prevent network requests
    os.environ['SE_MANAGER_PATH'] = ''  # Disable Selenium Manager entirely
    os.environ['SE_OFFLINE'] = '1'      # Force offline mode
    os.environ['WDM_LOG_LEVEL'] = '0'   # Keep WebDriverManager quiet too


def create_driver(cli_parsed, user_agent=None):
    """Creates a selenium FirefoxDriver

    Args:
        cli_parsed (ArgumentParser): Command Line Object
        user_agent (String, optional): Optional user-agent string

    Returns:
        FirefoxDriver: Selenium Firefox Webdriver
    """
    profile = webdriver.FirefoxProfile()
    # Load our custom firefox addon to handle basic auth.
    extension_path = Path(__file__).parent.parent / 'bin' / 'dismissauth.xpi'
    profile.add_extension(str(extension_path))
    profile.accept_untrusted_certs = True

    # This user agent case covers a user provided one
    if cli_parsed.user_agent is not None:
        profile.set_preference(
            'general.useragent.override', cli_parsed.user_agent)

    # This user agent case should only be hit when cycling
    if user_agent is not None:
        profile.set_preference('general.useragent.override', user_agent)

    # Set up our proxy information directly in the firefox profile
    if cli_parsed.proxy_ip is not None and cli_parsed.proxy_port is not None:
        profile.set_preference('network.proxy.type', 1)
        if "socks" in cli_parsed.proxy_type:
            profile.set_preference('network.proxy.socks', cli_parsed.proxy_ip)
            profile.set_preference('network.proxy.socks_port', cli_parsed.proxy_port)
        else:
            profile.set_preference('network.proxy.http', cli_parsed.proxy_ip)
            profile.set_preference(
                'network.proxy.http_port', cli_parsed.proxy_port)
            profile.set_preference('network.proxy.ssl', cli_parsed.proxy_ip)
            profile.set_preference('network.proxy.ssl_port', cli_parsed.proxy_port)

    profile.set_preference('app.update.enabled', False)
    profile.set_preference('browser.search.update', False)
    profile.set_preference('extensions.update.enabled', False)

    try:
        # Modern Selenium 4+ approach - migrate from deprecated DesiredCapabilities
        options = Options()
        options.add_argument("--headless")
        
        # Migrate acceptInsecureCerts from capabilities to options
        options.accept_insecure_certs = True
        
        # Set up Firefox profile preferences through options
        options.profile = profile
        profile.update_preferences()
        
        # Cross-platform Firefox detection and service setup
        firefox_binary = platform_mgr.find_firefox_executable()
        if firefox_binary:
            options.binary_location = firefox_binary
        
        # Configure geckodriver service to avoid automatic driver management issues
        service_kwargs = {}
        if hasattr(cli_parsed, 'selenium_log_path') and cli_parsed.selenium_log_path:
            service_kwargs['log_path'] = cli_parsed.selenium_log_path
        
        # Find local geckodriver to avoid GitHub API requests
        try:
            from modules.driver_manager import driver_mgr
            local_driver = driver_mgr.find_geckodriver()
            if local_driver:
                service_kwargs['executable_path'] = local_driver
            else:
                # Try system PATH
                import shutil
                system_driver = shutil.which('geckodriver')
                if system_driver:
                    service_kwargs['executable_path'] = system_driver
        except:
            pass  # safe fallback to automatic detection
        
        service = FirefoxService(**service_kwargs)
        
        # Firefox driver initialization (Selenium Manager disabled via environment vars)
        driver = webdriver.Firefox(service=service, options=options)
        driver.set_page_load_timeout(cli_parsed.timeout)
        driver.set_window_size(cli_parsed.width, cli_parsed.height)
        return driver
    except Exception as e:
        if 'Failed to find firefox binary' in str(e) or 'geckodriver' in str(e).lower():
            print('[*] Firefox/geckodriver missing.')
            if platform_mgr.is_windows:
                print('[*] Install Firefox and run: .\\setup\\setup.ps1')
            else:
                print('[*] Install Firefox and run: ./setup/setup.sh')
        else:
            print('[*] WebDriver error: {}'.format(e))
        sys.exit()


def capture_host(cli_parsed, http_object, driver, ua=None):
    """Screenshots a single host, saves information, and returns
    a complete HTTP Object

    Args:
        cli_parsed (ArgumentParser): Command Line Object
        http_object (HTTPTableObject): Object containing data relating to current URL
        driver (FirefoxDriver): webdriver instance
        ua (String, optional): Optional user agent string

    Returns:
        HTTPTableObject: Complete http_object
    """

    # Attempt to take the screenshot
    try:
        # If cookie is presented we need to avoid cookie-averse error. To do so, we need to get the page twice.
        driver.get(http_object.remote_system)
        if cli_parsed.cookies is not None:
            for cookie in cli_parsed.cookies:
                driver.add_cookie(cookie)
            driver.get(http_object.remote_system)
    except KeyboardInterrupt:
        print('[*] Skipping: {0}'.format(http_object.remote_system))
        http_object.error_state = 'Skipped'
        http_object.page_title = 'Page Skipped by User'
    except TimeoutException:
        print('[*] Hit timeout limit when connecting to {0}, retrying'.format(http_object.remote_system))
        driver.quit()
        driver = create_driver(cli_parsed, ua)
        http_object.error_state = 'Timeout'
    except http.client.BadStatusLine:
        print('[*] Bad status line when connecting to {0}'.format(http_object.remote_system))
        http_object.error_state = 'BadStatus'
        return http_object, driver
    except WebDriverException:
        print('[*] WebDriverError when connecting to {0}'.format(http_object.remote_system))
        http_object.error_state = 'BadStatus'
        return http_object, driver

    # Dismiss any alerts present on the page
    # Will not work for basic auth dialogs!
    try:
        alert = driver.switch_to.alert
        alert.dismiss()
    except Exception as e:
        pass

    # If we hit a timeout earlier, retry once
    if http_object.error_state == 'Timeout':
        retry_counter = 0
        return_status = False
        while retry_counter < cli_parsed.max_retries:
            http_object.error_state = None
            try:
                driver.get(http_object.remote_system)
                if cli_parsed.cookies is not None:
                    for cookie in cli_parsed.cookies:
                        driver.add_cookie(cookie)
                    driver.get(http_object.remote_system)
                break
            except TimeoutException:
                # Another timeout results in an error state and a return
                print('[*] Hit timeout limit when connecting to {0}'.format(http_object.remote_system))
                http_object.error_state = 'Timeout'
                http_object.page_title = 'Timeout Limit Reached'
                http_object.headers = {}
                driver.quit()
                driver = create_driver(cli_parsed, ua)
                return_status = True
            except KeyboardInterrupt:
                print('[*] Skipping: {0}'.format(http_object.remote_system))
                http_object.error_state = 'Skipped'
                http_object.page_title = 'Page Skipped by User'
                break
            except http.client.BadStatusLine:
                print('[*] Bad status line when connecting to {0}'.format(http_object.remote_system))
                http_object.error_state = 'BadStatus'
                return_status = True
                break
            except WebDriverException:
                print('[*] WebDriverError when connecting to {0}'.format(http_object.remote_system))
                http_object.error_state = 'BadStatus'
                return_status = True
                break
            retry_counter += 1

        # Determine if I need to return the objects
        if return_status:
            return http_object, driver

        try:
            alert = driver.switch_to.alert
            alert.dismiss()
        except Exception as e:
            pass

    do_delay(cli_parsed)

    # Save our screenshot to the specified directory
    try:
        driver.save_screenshot(http_object.screenshot_path)
    except WebDriverException as e:
        print('[*] Error saving web page screenshot'
              ' for ' + http_object.remote_system)

    # Get our headers using urllib
    context = None
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    except:
        context = None
        pass

    if cli_parsed.user_agent:
        tempua = cli_parsed.user_agent
    else:
        try:
            tempua = driver.execute_script("return navigator.userAgent")
        except:
            tempua = ''
    try:
        req = urllib.request.Request(http_object.remote_system, headers={'User-Agent': tempua})
        if cli_parsed.proxy_ip is not None:
            req.set_proxy(str(cli_parsed.proxy_ip) + ':' + str(cli_parsed.proxy_port), 'http')
            req.set_proxy(str(cli_parsed.proxy_ip) + ':' + str(cli_parsed.proxy_port), 'https')
        if context is None:
            opened = urllib.request.urlopen(req, timeout=cli_parsed.timeout)
        else:
            opened = urllib.request.urlopen(req,timeout=cli_parsed.timeout, context=context)
        headers = dict(opened.info())
        headers['Response Code'] = str(opened.getcode())
    except urllib.error.HTTPError as e:
        responsecode = e.code
        if responsecode == 404:
            http_object.category = 'notfound'
        elif responsecode == 403 or responsecode == 401:
            http_object.category = 'unauth'
        elif responsecode == 500:
            http_object.category = 'inerror'
        elif responsecode == 400:
            http_object.category = 'badreq'
        headers = dict(e.headers)
        headers['Response Code'] = str(e.code)
    except urllib.error.URLError as e:
        if '104' in str(e.reason):
            headers = {'Error': 'Connection Reset'}
            http_object.error_state = 'ConnReset'
            return http_object, driver
        elif '111' in str(e.reason):
            headers = {'Error': 'Connection Refused'}
            http_object.error_state = 'ConnRefuse'
            return http_object, driver
        elif 'Errno 1' in str(e.reason) and 'SSL23' in str(e.reason):
            headers = {'Error': 'SSL Handshake Error'}
            http_object.error_state = 'SSLHandshake'
            return http_object, driver
        elif 'Errno 8' in str(e.reason) and 'EOF occurred' in str(e.reason):
            headers = {'Error': 'SSL Handshake Error'}
            http_object.error_state = 'SSLHandshake'
            return http_object, driver
        else:
            headers = {'Error': 'HTTP Error...'}
            http_object.error_state = 'BadStatus'
            return http_object, driver
    except socket.error as e:
        if e.errno == 104:
            headers = {'Error': 'Connection Reset'}
            http_object.error_state = 'ConnReset'
            return http_object, driver
        elif e.errno == 10054:
            headers = {'Error': 'Connection Reset'}
            http_object.error_state = 'ConnReset'
            return http_object, driver
        elif 'timed out' in str(e):
            headers = {'Error': 'Timed Out'}
            http_object.error_state = 'Timeout'
            print('[*] Socket Timeout when connecting to {0}'.format(http_object.remote_system))
            return http_object, driver
        else:
            http_object.error_state = 'BadStatus'
            return http_object, driver
    except http.client.BadStatusLine:
        http_object.error_state = 'BadStatus'
        return http_object, driver
    except sslerr:
        headers = {'Error': 'Invalid SSL Certificate'}
        http_object.ssl_error = True
    except TypeError:
        headers = {'Error': 'Communication Error'}
        http_object.error_state = 'BadStatus'
        return http_object, driver
    except Exception:
        headers = {'Error': 'Communication Error'}
        http_object.error_state = 'BadStatus'
        return http_object, driver

    try:
        http_object.page_title = 'Unknown' if driver.title == '' else driver.title.encode(
            'utf-8')
    except Exception:
        http_object.page_title = 'Unable to Display'
    # Save page source to the object and to a file. Also set the title in the object
    try:
        http_object.headers = headers
        http_object.source_code = driver.page_source.encode('utf-8')
        with open(http_object.source_path, 'w') as f:
            f.write(http_object.source_code.decode())
    except UnexpectedAlertPresentException:
        with open(http_object.source_path, 'w') as f:
            f.write('Cannot render webpage')
        http_object.headers = {'Cannot Render Web Page': 'n/a'}
    except IOError:
        print("[*] ERROR: URL too long, surpasses max file length.")
        print("[*] ERROR: Skipping: " + http_object.remote_system)
    except WebDriverException:
        print("[*] ERROR: Skipping source code capture for: " + http_object.remote_system)
    except Exception: 
         print("[*] ERROR: Skipping source code capture for: " + http_object.remote_system)

    return http_object, driver
