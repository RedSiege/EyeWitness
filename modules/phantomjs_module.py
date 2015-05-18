import os
import re
import urllib2
import httplib
import socket
import ssl
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

title_regex = re.compile("<title(.*)>(.*)</title>", re.IGNORECASE + re.DOTALL)


def create_driver(cli_parsed, user_agent=None):
    capabilities = DesiredCapabilities.PHANTOMJS
    service_args = []

    if cli_parsed.user_agent is not None:
        capabilities[
            'phantomjs.page.settings.userAgent'] = cli_parsed.user_agent

    if user_agent is not None:
        capabilities['phantomjs.page.settings.userAgent'] = user_agent

    if cli_parsed.proxy_ip is not None and cli_parsed.proxy_port is not None:
        service_args.append(
            '--proxy={0}:{1}'.format(cli_parsed.proxy_ip, cli_parsed.proxy_port))
        service_args.append('--proxy-type=socks5')

    capabilities[
        'phantomjs.page.settings.resourceTimeout'] = cli_parsed.t * 1000
    capabilities['phantomjs.page.settings.userName'] = 'none'
    capabilities['phantomjs.page.settings.password'] = 'none'
    service_args.append('--ignore-ssl-errors=true')
    service_args.append('--web-security=no')

    log_path = os.path.join(cli_parsed.d, 'ghostdriver.log')

    try:
        driver = webdriver.PhantomJS(
            desired_capabilities=capabilities, service_args=service_args,
            service_log_path=log_path)
        # This is the default width from the firefox driver
        driver.set_window_size(1200, 675)
        driver.set_page_load_timeout(cli_parsed.t)
        return driver
    except WebDriverException:
        time.sleep(200)
        driver = webdriver.PhantomJS(
            desired_capabilities=capabilities, service_args=service_args,
            service_log_path=log_path)
        # This is the default width from the firefox driver
        driver.set_window_size(1200, 675)
        driver.set_page_load_timeout(cli_parsed.t)
        return driver
    except Exception as e:
        print str(e)


def capture_host(cli_parsed, http_object, driver, ua=None):
    global title_regex

    try:
        driver.get(http_object.remote_system)
    except KeyboardInterrupt:
        if cli_parsed.single is not None:
            print '[*] Skipping: {0}'.format(http_object.remote_system)
        http_object.error_state = 'Skipped'
        http_object.page_title = 'Page Skipped by User'
        driver.quit()
        return http_object
    except TimeoutException:
        print '[*] Hit timeout limit when conecting to {0}, retrying'.format(http_object.remote_system)
        http_object.error_state = 'Timeout'

    if http_object.error_state == 'Timeout':
        http_object.error_state = None
        try:
            driver.get(http_object.remote_system)
        except TimeoutException:
            print '[*] Hit timeout limit when conecting to {0}'.format(http_object.remote_system)
            http_object.error_state = 'Timeout'
            http_object.page_title = 'Timeout Limit Reached'
            http_object.headers = {}
            driver.quit()
            return http_object
        except KeyboardInterrupt:
            print '[*] Skipping: {0}'.format(http_object.remote_system)
            http_object.error_state = 'Skipped'
            http_object.page_title = 'Page Skipped by User'
            driver.quit()
            return http_object

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
    except Exception as e:
        print str(e)

    # tag = title_regex.search(driver.page_source.encode('utf-8'))
    # if tag is not None:
    #     http_object.page_title = tag.group(2).strip()
    # else:
    #     http_object.page_title = 'Unknown'
    http_object.page_title = 'Unknown' if driver.title == '' else driver.title

    http_object.headers = headers
    http_object.source_code = driver.page_source.encode('utf-8')

    with open(http_object.source_path, 'w') as f:
        f.write(driver.page_source.encode('utf-8'))
    driver.quit()
    return http_object
