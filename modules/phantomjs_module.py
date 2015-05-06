import os
import re
import urllib2

from helpers import create_web_index_head
from helpers import get_ua_values
from helpers import target_creator
from objects import HTTPTableObject
from objects import UAObject
from selenium import webdriver
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

    log_path = os.path.join(cli_parsed.d, 'ghostdriver.log')

    try:
        driver = webdriver.PhantomJS(
            desired_capabilities=capabilities, service_args=service_args,
            service_log_path=log_path)
        # This is the default width from the firefox driver
        driver.set_window_size(1200, 675)
        return driver
    except Exception as e:
        print str(e)


def capture_host(cli_parsed, http_object, driver):
    global title_regex

    try:
        driver.get(http_object.remote_system)
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
    except Exception as e:
        print str(e)

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

    return http_object


def single_mode(cli_parsed):
    http_object = HTTPTableObject()
    http_object.remote_system = cli_parsed.single
    http_object.set_paths(
        cli_parsed.d, 'baseline' if cli_parsed.cycle is not None else None)

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)

    if cli_parsed.cycle is not None:
        print 'Making baseline request for {0}'.format(http_object.remote_system)
    else:
        print 'Attempting to screenshot {0}'.format(http_object.remote_system)
    driver = create_driver(cli_parsed)
    result = capture_host(cli_parsed, http_object, driver)
    driver.quit()
    if cli_parsed.cycle is not None and result.error_state is None:
        ua_dict = get_ua_values(cli_parsed.cycle)
        for browser_key, user_agent_value in ua_dict.iteritems():
            print 'Now making web request with: {0}'.format(browser_key)
            ua_object = UAObject(browser_key, user_agent_value)
            ua_object.copy_data(result)
            driver = create_driver(cli_parsed, user_agent_value)
            ua_object = capture_host(cli_parsed, ua_object, driver)
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

        http_object = HTTPTableObject()
        http_object.remote_system = url
        http_object.set_paths(cli_parsed.d)
        if cli_parsed.cycle is not None:
            print 'Making baseline request for {0}'.format(http_object.remote_system)
        else:
            print 'Attempting to screenshot {0}'.format(http_object.remote_system)
        result = capture_host(
            cli_parsed, http_object, driver)
        data[url] = result

    if cli_parsed.cycle is not None:
        ua_dict = get_ua_values(cli_parsed.cycle)
        for browser_key, user_agent_value in ua_dict.iteritems():
            driver = create_driver(cli_parsed, user_agent_value)
            for url in url_list:
                result = data[url]
                if result.error_state is None:
                    print 'Now making web request with: {0} for {1}'.format(
                        browser_key, result.remote_system)
                    ua_object = UAObject(browser_key, user_agent_value)
                    ua_object.copy_data(result)
                    ua_object = capture_host(cli_parsed, ua_object, driver)
                    result.add_ua_data(ua_object)
            driver.quit()

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)

    html = u""
    for key, value in data.items():
        html += value.create_table_html()

    with open(os.path.join(cli_parsed.d, 'report.html'), 'w') as f:
        f.write(web_index_head)
        f.write(html)

    driver.quit()
