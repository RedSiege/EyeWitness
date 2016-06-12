import httplib
import os
import socket
import time
import urllib2
import sys
import ssl

try:
    from ssl import CertificateError as sslerr
except:
    from ssl import SSLError as sslerr
try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
except ImportError:
    print '[*] selenium not found.'
    print '[*] Please run the script in the setup directory!'
    sys.exit()


def create_driver(cli_parsed, user_agent=None):
    """Creates a phantomjs webdriver instance

    Args:
        cli_parsed (ArgumentParser): CLI Options
        user_agent (String, optional): User Agent String

    Returns:
        webdriver: PhantomJS Webdriver
    """
    capabilities = DesiredCapabilities.PHANTOMJS

    if cli_parsed.vhost_name:
        capabilities['phantomjs.page.customHeaders.Host'] = cli_parsed.vhost_name

    service_args = []
    phantomjs_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'bin', 'phantomjs')

    # Set up our user agent if necessary
    if cli_parsed.user_agent is not None:
        capabilities[
            'phantomjs.page.settings.userAgent'] = cli_parsed.user_agent

    # This block is for UA cycling
    if user_agent is not None:
        capabilities['phantomjs.page.settings.userAgent'] = user_agent

    # Set up proxy settings
    if cli_parsed.proxy_ip is not None and cli_parsed.proxy_port is not None:
        service_args.append(
            '--proxy={0}:{1}'.format(cli_parsed.proxy_ip, cli_parsed.proxy_port))

    # PhantomJS resource timeout
    capabilities[
        'phantomjs.page.settings.resourceTimeout'] = cli_parsed.timeout * 1000
    # Basic auth settings
    capabilities['phantomjs.page.settings.userName'] = 'none'
    capabilities['phantomjs.page.settings.password'] = 'none'
    # Flags to ignore SSL problems and get screenshots
    service_args.append('--ignore-ssl-errors=true')
    service_args.append('--web-security=no')
    service_args.append('--ssl-protocol=any')

    log_path = os.path.join(cli_parsed.d, 'ghostdriver.log')
    driver = None
    while driver is None:
        try:
            driver = webdriver.PhantomJS(
                desired_capabilities=capabilities, service_args=service_args,
                service_log_path=log_path, executable_path=phantomjs_path)
            # This is the default size from the firefox driver
            driver.set_window_size(1200, 675)
            driver.set_page_load_timeout(cli_parsed.timeout)
            return driver
        except WebDriverException:
            # print 'WebDriverException, retrying'
            time.sleep(2.5)
            continue
        except Exception as e:
            print str(e)

    return driver


def capture_host(cli_parsed, http_object, driver, ua=None):
    """Captures a single host and populates the HTTP Object

    Args:
        cli_parsed (ArgumentParser): CLI Object
        http_object (HTTPTableObject): HTTP Object representing a URL
        driver (Webdriver): Webdriver
        ua (TYPE, String): Optional User Agent String

    Returns:
        HTTPTableObject: Filled out HTTP Object
    """
    try:
        driver.get(http_object.remote_system)
    except KeyboardInterrupt:
        if cli_parsed.single is not None:
            print '[*] Skipping: {0}'.format(http_object.remote_system)
        http_object.error_state = 'Skipped'
        http_object.page_title = 'Page Skipped by User'
        return http_object, driver
    except TimeoutException:
        print '[*] Hit timeout limit when connecting to {0}, retrying'.format(http_object.remote_system)
        http_object.error_state = 'Timeout'
    except httplib.BadStatusLine:
        print '[*] Bad status line when connecting to {0}'.format(http_object.remote_system)
        http_object.error_state = 'BadStatus'
        return http_object, driver
    except WebDriverException:
        print '[*] WebDriverError when connecting to {0}'.format(http_object.remote_system)
        http_object.error_state = 'BadStatus'
        return http_object, driver

    # Retry block for a timeout
    if http_object.error_state == 'Timeout':
        http_object.error_state = None
        try:
            driver.get(http_object.remote_system)
        except TimeoutException:
            print '[*] Hit timeout limit when connecting to {0}'.format(http_object.remote_system)
            http_object.error_state = 'Timeout'
            http_object.page_title = 'Timeout Limit Reached'
            return http_object, driver
        except KeyboardInterrupt:
            print '[*] Skipping: {0}'.format(http_object.remote_system)
            http_object.error_state = 'Skipped'
            http_object.page_title = 'Page Skipped by User'
            return http_object, driver
        except httplib.BadStatusLine:
            print '[*] Bad status line when connecting to {0}'.format(http_object.remote_system)
            http_object.error_state = 'BadStatus'
            return http_object, driver
        except WebDriverException:
            print '[*] WebDriverError when connecting to {0}'.format(http_object.remote_system)
            http_object.error_state = 'BadStatus'
            return http_object, driver

    # Get our headers using urllib2
    context = None
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    except:
        context = None
        pass

    try:
        tempua = driver.execute_script("return navigator.userAgent")
    except:
        tempua = ''
    try:
        req = urllib2.Request(http_object.remote_system, headers={'User-Agent': tempua})
        if context is None:
            opened = urllib2.urlopen(req)
        else:
            opened = urllib2.urlopen(req, context=context)
        headers = dict(opened.info())
        headers['Response Code'] = str(opened.getcode())
    except urllib2.HTTPError as e:
        responsecode = e.code
        if responsecode == 404:
            http_object.category = 'notfound'
        if responsecode == 403 or responsecode == 401:
            http_object.category = 'unauth'
        headers = dict(e.headers)
        headers['Response Code'] = str(e.code)
    except urllib2.URLError as e:
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
        else:
            http_object.error_state = 'BadStatus'
            return http_object, driver
    except httplib.BadStatusLine:
        http_object.error_state = 'BadStatus'
        return http_object, driver
    except sslerr:
        headers = {'Error': 'Invalid SSL Certificate'}
        http_object.ssl_error = True

    try:
        driver.save_screenshot(http_object.screenshot_path)
    except Exception as e:
        print driver.remote_system

    try:
        http_object.page_title = 'Unknown' if driver.title == '' else driver.title.encode(
            'utf-8')
    except Exception:
        http_object.page_title = 'Unable to Display'

    http_object.headers = headers
    http_object.source_code = driver.page_source.encode('utf-8')

    with open(http_object.source_path, 'w') as f:
        f.write(http_object.source_code)
    return http_object, driver
