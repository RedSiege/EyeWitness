import httplib
import os
import re
import socket
import ssl
import sys
import urllib2

from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import WebDriverException

title_regex = re.compile("<title(.*)>(.*)</title>", re.IGNORECASE + re.DOTALL)


def create_driver(cli_parsed, user_agent=None):
    profile = webdriver.FirefoxProfile()
    profile.set_preference('network.http.phishy-userpass-length', 255)
    extension_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'bin', 'dismissauth.xpi')
    profile.add_extension(extension_path)

    if cli_parsed.user_agent is not None:
        profile.set_preference(
            'general.useragent.override', cli_parsed.user_agent)

    if user_agent is not None:
        profile.set_preference('general.useragent.override', user_agent)

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
    global title_regex

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

    try:
        alert = driver.switch_to_alert()
        alert.dismiss()
        alert.accept()
    except NoAlertPresentException:
        pass

    if http_object.error_state == 'Timeout':
        http_object.error_state = None
        try:
            driver.get(http_object.remote_system)
        except TimeoutException:
            print '[*] Hit timeout limit when connecting to {0}'.format(http_object.remote_system)
            http_object.error_state = 'Timeout'
            http_object.page_title = 'Timeout Limit Reached'
            http_object.headers = {}
            driver.quit()
            return http_object
        except KeyboardInterrupt:
            print '[*] Skipping: {0}'.format(http_object.remote_system)
            http_object.error_state = 'Skipped'
            http_object.page_title = 'Page Skipped by User'

    try:
        alert = driver.switch_to_alert()
        alert.dismiss()
        alert.accept()
    except NoAlertPresentException:
        pass

    try:
        headers = dict(urllib2.urlopen(http_object.remote_system).info())
    except urllib2.HTTPError:
        headers = {'Error': 'Error when grabbing web server headers...'}
    except urllib2.URLError:
        headers = {'Error': 'SSL Handshake Error...'}
    except (socket.error, httplib.BadStatusLine):
        headers = {'Error': 'Potential timeout connecting to server'}
    except ssl.CertificateError:
        headers = {'Error': 'Invalid SSL Certificate'}
        http_object.ssl_error = True

    try:
        driver.save_screenshot(http_object.screenshot_path)
    except WebDriverException:
        print('[*] Error saving web page screenshot'
              ' for ' + http_object.remote_system)
    try:
        http_object.page_title = 'Unknown' if driver.title == '' else driver.title.encode(
            'utf-8')
        http_object.headers = headers
        http_object.source_code = driver.page_source.encode('utf-8')

        with open(http_object.source_path, 'w') as f:
            f.write(driver.page_source.encode('utf-8'))
    except UnexpectedAlertPresentException:
        with open(http_object.source_path, 'w') as f:
            f.write('Cannot render webpage')
        http_object.headers = {'Cannot Render Web Page': 'n/a'}

    driver.quit()
    return http_object
