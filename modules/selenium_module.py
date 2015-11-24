import httplib
import os
import socket
import sys
import urllib2
import ssl
import time

try:
    from ssl import CertificateError as sslerr
except:
    from ssl import SSLError as sslerr

try:
    from selenium import webdriver
    from selenium.common.exceptions import NoAlertPresentException
    from selenium.common.exceptions import TimeoutException
    from selenium.common.exceptions import UnexpectedAlertPresentException
    from selenium.common.exceptions import WebDriverException
except ImportError:
    print '[*] Selenium not found.'
    print '[*] Please run the script in the setup directory!'
    sys.exit()


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
    extension_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'bin', 'dismissauth.xpi')
    profile.add_extension(extension_path)

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
        profile.set_preference('network.proxy.http', cli_parsed.proxy_ip)
        profile.set_preference(
            'network.proxy.http_port', cli_parsed.proxy_port)
        profile.set_preference('network.proxy.ssl', cli_parsed.proxy_ip)
        profile.set_preference('network.proxy.ssl_port', cli_parsed.proxy_port)

    profile.set_preference('app.update.enabled', False)
    profile.set_preference('browser.search.update', False)
    profile.set_preference('extensions.update.enabled', False)
    profile.set_preference('capability.policy.default.Window.alert', 'noAccess');
    profile.set_preference('capability.policy.default.Window.confirm', 'noAccess');
    profile.set_preference('capability.policy.default.Window.prompt', 'noAccess');

    try:
        driver = webdriver.Firefox(profile)
        driver.set_page_load_timeout(cli_parsed.timeout)
        return driver
    except Exception as e:
        if 'Failed to find firefox binary' in str(e):
            print 'Firefox not found!'
            print 'You can fix this by installing Firefox/Iceweasel\
             or using phantomjs/ghost'
        else:
            print e
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
        driver.get(http_object.remote_system)
    except KeyboardInterrupt:
        print '[*] Skipping: {0}'.format(http_object.remote_system)
        http_object.error_state = 'Skipped'
        http_object.page_title = 'Page Skipped by User'
    except TimeoutException:
        print '[*] Hit timeout limit when connecting to {0}, retrying'.format(http_object.remote_system)
        driver.quit()
        driver = create_driver(cli_parsed, ua)
        http_object.error_state = 'Timeout'
    except httplib.BadStatusLine:
        print '[*] Bad status line when connecting to {0}'.format(http_object.remote_system)
        http_object.error_state = 'BadStatus'
        return http_object, driver
    except WebDriverException:
        print '[*] WebDriverError when connecting to {0}'.format(http_object.remote_system)
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
        http_object.error_state = None
        try:
            driver.get(http_object.remote_system)
        except TimeoutException:
            # Another timeout results in an error state and a return
            print '[*] Hit timeout limit when connecting to {0}'.format(http_object.remote_system)
            http_object.error_state = 'Timeout'
            http_object.page_title = 'Timeout Limit Reached'
            http_object.headers = {}
            driver.quit()
            driver = create_driver(cli_parsed, ua)
            return http_object, driver
        except KeyboardInterrupt:
            print '[*] Skipping: {0}'.format(http_object.remote_system)
            http_object.error_state = 'Skipped'
            http_object.page_title = 'Page Skipped by User'
        except httplib.BadStatusLine:
            print '[*] Bad status line when connecting to {0}'.format(http_object.remote_system)
            http_object.error_state = 'BadStatus'
            return http_object, driver
        except WebDriverException:
            print '[*] WebDriverError when connecting to {0}'.format(http_object.remote_system)
            http_object.error_state = 'BadStatus'
            return http_object, driver

        try:
            alert = driver.switch_to.alert
            alert.dismiss()
        except Exception as e:
            pass
    # Save our screenshot to the specified directory
    try:
        driver.save_screenshot(http_object.screenshot_path)
    except WebDriverException as e:
        print('[*] Error saving web page screenshot'
              ' for ' + http_object.remote_system)
    

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
        http_object.page_title = 'Unknown' if driver.title == '' else driver.title.encode(
            'utf-8')
    except Exception:
        http_object.page_title = 'Unable to Display'
    # Save page source to the object and to a file. Also set the title in the object
    try:
        http_object.headers = headers
        http_object.source_code = driver.page_source.encode('utf-8')
        with open(http_object.source_path, 'w') as f:
            f.write(http_object.source_code)
    except UnexpectedAlertPresentException:
        with open(http_object.source_path, 'w') as f:
            f.write('Cannot render webpage')
        http_object.headers = {'Cannot Render Web Page': 'n/a'}

    return http_object, driver
