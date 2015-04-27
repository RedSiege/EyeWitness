from selenium import webdriver
from objects import HTTPTableObject
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import UnexpectedAlertPresentException
import os
import urllib2
import socket
import httplib
import re
import sys

title_regex = re.compile("<title(.*)>(.*)</title>", re.IGNORECASE + re.DOTALL)


def create_driver(cli_parsed, user_agent=None):
    profile = webdriver.FirefoxProfile()

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
            sys.exit()


def capture_host(cli_parsed, http_object, driver):
    global title_regex

    try:
        alert = driver.switch_to.alert
        alert.dismiss()
    except NoAlertPresentException:
        pass
    driver.get(http_object.remote_system)

    try:
        headers = dict(urllib2.urlopen(http_object.remote_system).info())
    except urllib2.HTTPError:
        headers = {'Error': 'Error when grabbing web server headers...'}
    except urllib2.URLError:
        headers = {'Error': 'SSL Handshake Error...'}
    except (socket.error, httplib.BadStatusLine):
        headers = {'Error': 'Potential timeout connecting to server'}

    try:
        driver.save_screenshot(http_object.screenshot_path)
    except WebDriverException:
        print '[*] Error saving web page screenshot \
            for ' + http_object.remote_system
    try:
        tag = title_regex.search(driver.page_source.encode('utf-8'))
        if tag is not None:
            http_object.page_title = tag.group(1).strip()
        else:
            http_object.page_title = 'Unknown'

        http_object.headers = headers

        with open(http_object.source_path, 'w') as f:
            f.write(driver.page_source.encode('utf-8'))
    except UnexpectedAlertPresentException:
        with open(http_object.source_path, 'w') as f:
            f.write('Cannot render webpage')
        http_object.headers = {'Cannot Render Web Page': 'n/a'}

    return http_object


def initialize_module(cli_parsed):
    driver = create_driver(cli_parsed)
    os.makedirs(cli_parsed.d)
    os.makedirs(os.path.join(cli_parsed.d, 'screens'))
    os.makedirs(os.path.join(cli_parsed.d, 'source'))
    return driver
