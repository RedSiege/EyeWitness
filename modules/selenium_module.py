import httplib
import os
import re
import socket
import sys
import threading
import urllib2

from helpers import create_web_index_head
from helpers import target_creator
from helpers import get_ua_values
from objects import HTTPTableObject, UAObject
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import WebDriverException

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
        else:
            print 'Unknown Error when creating selenium driver. Exiting'
        sys.exit()


def capture_host(cli_parsed, http_object, driver):
    global title_regex
    new_driver = False
    try:
        alert = driver.switch_to_alert()
        alert.dismiss()
    except NoAlertPresentException:
        pass

    try:
        driver.get(http_object.remote_system)
    except KeyboardInterrupt:
        print '[*] Skipping: {0}'.format(http_object.remote_system)
        http_object.error_state = 'Skipped'
        http_object.page_title = 'Page Skipped by User'
    except TimeoutException:
        print '[*] Hit timeout limit when conecting to {0}, retrying'.format(http_object.remote_system)
        driver.quit()
        driver = create_driver(cli_parsed)
        new_driver = True
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
            driver = create_driver(cli_parsed)
        except KeyboardInterrupt:
            print '[*] Skipping: {0}'.format(http_object.remote_system)
            http_object.error_state = 'Skipped'
            http_object.page_title = 'Page Skipped by User'

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
            http_object.page_title = tag.group(2).strip()
        else:
            http_object.page_title = 'Unknown'

        http_object.headers = headers
        http_object.source_code = driver.page_source.encode('utf-8')

        with open(http_object.source_path, 'w') as f:
            f.write(driver.page_source.encode('utf-8'))
    except UnexpectedAlertPresentException:
        with open(http_object.source_path, 'w') as f:
            f.write('Cannot render webpage')
        http_object.headers = {'Cannot Render Web Page': 'n/a'}

    return http_object, driver, new_driver


def single_mode(cli_parsed):
    http_object = HTTPTableObject()
    http_object.remote_system = cli_parsed.single
    suffix = 'baseline' if cli_parsed.cycle else None
    http_object.set_paths(
        cli_parsed.d, 'baseline' if cli_parsed.cycle else None)

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)
    if cli_parsed.cycle is not None:
        print 'Making baseline request for {0}'.format(http_object.remote_system)
    else:
        print 'Attempting to screenshot {0}'.format(http_object.remote_system)
    driver = create_driver(cli_parsed)

    result, driver, new_driver = capture_host(cli_parsed, http_object, driver)
    driver.quit()

    if cli_parsed.cycle is not None:
        ua_dict = get_ua_values(cli_parsed.cycle)
        for browser_key, user_agent_value in ua_dict.iteritems():
            print 'Now making web request with: {0}'.format(browser_key)
            ua_object = UAObject(browser_key, user_agent_value)
            ua_object.copy_data(result)
            driver = create_driver(cli_parsed, user_agent_value)
            ua_object, driver, new_driver = capture_host(cli_parsed, ua_object, driver)
            result.add_ua_data(ua_object)
            driver.quit()

    html = result.create_table_html()
    with open(os.path.join(cli_parsed.d, 'report.html'), 'w') as f:
        f.write(web_index_head)
        f.write(html)


def multi_mode(cli_parsed):
    page_counter = 0
    url_counter = 0
    counter = 0
    data = {}

    driver = create_driver(cli_parsed)

    url_list, rdp_list, vnc_List = target_creator(cli_parsed)

    for url in url_list:
        counter += 1

        if counter == 250:
            driver.quit()
            driver = create_driver(cli_parsed)
            counter = 0

        http_object = HTTPTableObject()
        http_object.remote_system = url
        http_object.set_paths(cli_parsed.d)

        result, driver, new_driver = capture_host(
            cli_parsed, http_object, driver)
        if new_driver:
            counter = 0
        data[url] = result

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)

    html = u""
    for key, value in data.items():
        html += value.create_table_html()

    with open(os.path.join(cli_parsed.d, 'report.html'), 'w') as f:
        f.write(web_index_head)
        f.write(html)

    driver.quit()
