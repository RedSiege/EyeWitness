import httplib
import os
import re
import socket
import sys
import threading
import urllib2

from helpers import create_web_index_head
from helpers import get_ua_values
from helpers import target_creator
from helpers import write_report
from fuzzywuzzy import fuzz
from multiprocessing import Manager
from multiprocessing import Pool
from multiprocessing import Process
from multiprocessing import Queue
from objects import HTTPTableObject
from objects import UAObject
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import WebDriverException
import time

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


def capture_host(cli_parsed, http_object, driver, ua=None):
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
        driver = create_driver(cli_parsed, ua)
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
            return http_object, driver
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

    return http_object, driver


def single_mode(cli_parsed, url=None, q=None):
    if url is None:
        url = cli_parsed.single
    http_object = HTTPTableObject()
    http_object.remote_system = url
    suffix = 'baseline' if cli_parsed.cycle else None
    http_object.set_paths(
        cli_parsed.d, 'baseline' if cli_parsed.cycle else None)

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)
    if cli_parsed.cycle is not None:
        print 'Making baseline request for {0}'.format(http_object.remote_system)
    else:
        print 'Attempting to screenshot {0}'.format(http_object.remote_system)
    driver = create_driver(cli_parsed)

    result, driver = capture_host(cli_parsed, http_object, driver)
    driver.quit()

    if cli_parsed.cycle is not None:
        ua_dict = get_ua_values(cli_parsed.cycle)
        for browser_key, user_agent_value in ua_dict.iteritems():
            print 'Now making web request with: {0}'.format(browser_key)
            ua_object = UAObject(browser_key, user_agent_value)
            ua_object.copy_data(result)
            driver = create_driver(cli_parsed, user_agent_value)
            ua_object, driver = capture_host(
                cli_parsed, ua_object, driver)
            result.add_ua_data(ua_object)
            driver.quit()

    if q is None:
        html = result.create_table_html()
        with open(os.path.join(cli_parsed.d, 'report.html'), 'w') as f:
            f.write(web_index_head)
            f.write(html)
    else:
        q.put(result)


def multi_mode(cli_parsed):
    p = Pool(cli_parsed.threads)
    m = Manager()
    data = m.Queue()
    threads = []

    url_list, rdp_list, vnc_List = target_creator(cli_parsed)
    for url in url_list:
        threads.append(p.apply_async(single_mode, [cli_parsed, url, data]))

    p.close()
    try:
        while not all([r.ready() for r in threads]):
            time.sleep(1)
    except KeyboardInterrupt:
        p.terminate()
        p.join()

    results = []
    while not data.empty():
        results.append(data.get())

    grouped = []
    errors = [x for x in results if x.error_state is not None]
    results[:] = [x for x in results if x.error_state is None]
    while len(results) > 0:
        test = results.pop(0)
        temp = [x for x in results if fuzz.token_sort_ratio(
            test.page_title, x.page_title) >= 70]
        temp.append(test)
        temp = sorted(temp, key=lambda (k): k.page_title)
        grouped.extend(temp)
        results[:] = [x for x in results if fuzz.token_sort_ratio(
            test.page_title, x.page_title) < 70]
    grouped.extend(errors)
    errors = sorted(errors, key=lambda (k): k.error_state)
    write_report(grouped, cli_parsed)
