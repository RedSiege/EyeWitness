import httplib
import os
import socket
import ssl
import sys
import urllib2

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

    try:
        driver = webdriver.Firefox(profile)
        driver.set_page_load_timeout(cli_parsed.t)
        return driver
    except Exception as e:
        if 'Failed to find firefox binary' in str(e):
            print 'Firefox not found!'
            print 'You can fix this by installing Firefox/Iceweasel\
             or using phantomjs/ghost'
        else:
            print 'Unknown Error when creating selenium driver. Exiting'
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

    # Dismiss any alerts present on the page
    # Will not work for basic auth dialogs!
    try:
        alert = driver.switch_to_alert()
        alert.dismiss()
        alert.accept()
    except NoAlertPresentException:
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

    try:
        alert = driver.switch_to_alert()
        alert.dismiss()
        alert.accept()
    except NoAlertPresentException:
        pass

    # Selenium does not return headers, so make a request using urllib to get them
    try:
        headers = dict(urllib2.urlopen(http_object.remote_system).info())
    except urllib2.HTTPError as e:
        responsecode = e.code
        if responsecode == 404:
            http_object.category = 'notfound'
        if responsecode == 403 or responsecode == 401:
            http_object.category = 'unauth'
        headers = dict(e.headers)
    except urllib2.URLError:
        headers = {'Error': 'SSL Handshake Error...'}
    except (socket.error, httplib.BadStatusLine):
        headers = {'Error': 'Potential timeout connecting to server'}
    except ssl.CertificateError:
        headers = {'Error': 'Invalid SSL Certificate'}
        http_object.ssl_error = True

    # Save our screenshot to the specified directory
    try:
        driver.save_screenshot(http_object.screenshot_path)
    except WebDriverException:
        print('[*] Error saving web page screenshot'
              ' for ' + http_object.remote_system)

    try:
        http_object.page_title = 'Unknown' if driver.title == '' else driver.title.encode('utf-8')
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
