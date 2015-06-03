#!/usr/bin/env python

import argparse
import glob
import os
import re
import sys
import time
import webbrowser
import shutil

from distutils.util import strtobool
from modules.helpers import create_folders_css
from modules.helpers import create_table_head
from modules.helpers import create_web_index_head
from modules.helpers import default_creds_category
from modules.helpers import do_jitter
from modules.helpers import get_ua_values
from modules.helpers import sort_data_and_write
from modules.helpers import target_creator
from modules.helpers import title_screen
from modules.helpers import vnc_rdp_header
from modules.helpers import vnc_rdp_table_head
from modules import objects
from modules import phantomjs_module
from modules import selenium_module
from modules import vnc_module
from modules import rdp_module
from multiprocessing.managers import SyncManager
from multiprocessing import Pool
from multiprocessing import Process
from multiprocessing import Lock
from multiprocessing import Manager
from multiprocessing import TimeoutError
try:
    from pyvirtualdisplay import Display
except ImportError:
    print '[*] pyvirtualdisplay not found.'
    print '[*] Please run the script in the setup directory!'
    sys.exit()


multi_counter = 0
multi_total = 0


def create_cli_parser():
    parser = argparse.ArgumentParser(
        add_help=False, description="EyeWitness is a tool used to capture\
        screenshots from a list of URLs")
    parser.add_argument('-h', '-?', '--h', '-help',
                        '--help', action="store_true", help=argparse.SUPPRESS)

    protocols = parser.add_argument_group('Protocols')
    protocols.add_argument('--web', default=False, action='store_true',
                           help='HTTP Screenshot using Selenium')
    protocols.add_argument('--headless', default=False, action='store_true',
                           help='HTTP Screenshot using PhantomJS Headless')
    protocols.add_argument('--rdp', default=False, action='store_true',
                           help='Screenshot RDP Services')
    protocols.add_argument('--vnc', default=False, action='store_true',
                           help='Screenshot Authless VNC services')
    protocols.add_argument('--all-protocols', default=False,
                           action='store_true',
                           help='Screenshot all supported protocols, \
                           using Selenium for HTTP')

    input_options = parser.add_argument_group('Input Options')
    input_options.add_argument('-f', metavar='Filename', default=None,
                               help='Line seperated file containing URLs to \
                            capture, Nmap XML output, or a .nessus file')
    input_options.add_argument('--single', metavar='Single URL', default=None,
                               help='Single URL/Host to capture')
    input_options.add_argument('--createtargets', metavar='targetfilename.txt',
                               default=None, help='Parses a .nessus or Nmap XML \
                            file into a line-seperated list of URLs')
    input_options.add_argument('--no-dns', default=False, action='store_true',
                               help='Skip DNS resolution when connecting to \
                            websites')

    timing_options = parser.add_argument_group('Timing Options')
    timing_options.add_argument('-t', metavar='Timeout', default=7, type=int,
                                help='Maximum number of seconds to wait while\
                                 requesting a web page (Default: 7)')
    timing_options.add_argument('--jitter', metavar='# of Seconds', default=0,
                                type=int, help='Randomize URLs and add a random\
                                 delay between requests')
    timing_options.add_argument('--threads', metavar='# of Threads', default=10,
                                type=int, help='Number of threads to use while using\
                                file based input')

    report_options = parser.add_argument_group('Report Output Options')
    report_options.add_argument('-d', metavar='Directory Name',
                                default=None,
                                help='Directory name for report output')
    report_options.add_argument('--results', metavar='Hosts Per Page',
                                default=25, type=int, help='Number of Hosts per\
                                 page of the report')
    report_options.add_argument('--no-prompt', default=False,
                                action='store_true',
                                help='Don\'t prompt to open the report')

    http_options = parser.add_argument_group('Web Options')
    http_options.add_argument('--user-agent', metavar='User Agent',
                              default=None, help='User Agent to use for all\
                               requests')
    http_options.add_argument('--cycle', metavar='User Agent Type',
                              default=None, help='User Agent Type (Browser, \
                                Mobile, Crawler, Scanner, Misc, All')
    http_options.add_argument('--difference', metavar='Difference Threshold',
                              default=50, type=int, help='Difference threshold\
                               when determining if user agent requests are\
                                close \"enough\" (Default: 50)')
    http_options.add_argument('--proxy-ip', metavar='127.0.0.1', default=None,
                              help='IP of web proxy to go through')
    http_options.add_argument('--proxy-port', metavar='8080', default=None,
                              type=int, help='Port of web proxy to go through')
    http_options.add_argument('--show-selenium', default=False,
                              action='store_true', help='Show display for selenium')

    args = parser.parse_args()
    args.date = time.strftime('%m/%d/%Y')
    args.time = time.strftime('%H:%M:%S')

    local_path = os.path.dirname(os.path.realpath(__file__))

    if args.h:
        parser.print_help()
        sys.exit()

    if args.d is not None:
        if args.d.startswith('/') or re.match(
                '^[A-Za-z]:\\\\', args.d) is not None:
            args.d = args.d.rstrip('/')
            args.d = args.d.rstrip('\\')
        else:
            args.d = os.path.join(os.getcwd(), args.d)

        if not os.access(os.path.dirname(args.d), os.W_OK):
            print '[*] Error: Please provide a valid folder name/path'
            parser.print_help()
            sys.exit()
        else:
            if os.path.isdir(args.d):
                overwrite_dir = raw_input(('Directory Exists! Do you want to '
                                           'overwrite? [y/n] '))
                overwrite_dir = overwrite_dir.lower().strip()
                if overwrite_dir == 'n':
                    print('Quitting...Restart and provide the proper '
                          'directory to write to!')
                    sys.exit()
                elif overwrite_dir == 'y':
                    shutil.rmtree(args.d)
                    pass
                else:
                    print('Quitting since you didn\'t provide '
                          'a valid response...')
                    sys.exit()

    else:
        output_folder = args.date.replace(
            '/', '') + '_' + args.time.replace(':', '')
        args.d = os.path.join(os.getcwd(), output_folder)

    args.log_file_path = os.path.join(args.d, 'logfile.log')

    if args.f is None and args.single is None:
        print("[*] Error: You didn't specify a file! I need a file containing "
              "URLs!")
        parser.print_help()
        sys.exit()

    if not any((args.web, args.vnc, args.rdp, args.all_protocols, args.headless)):
        print "[*] Error: You didn't give me an action to perform."
        print "[*] Error: Please use --web, --rdp, or --vnc!\n"
        parser.print_help()
        sys.exit()

    if args.all_protocols:
        args.web = True
        args.vnc = True
        args.rdp = True

    return args


def single_mode(cli_parsed):
    display = None
    if cli_parsed.web:
        create_driver = selenium_module.create_driver
        capture_host = selenium_module.capture_host
        if not cli_parsed.show_selenium:
            display = Display(visible=0, size=(1920, 1080))
            display.start()
    elif cli_parsed.headless:
        create_driver = phantomjs_module.create_driver
        capture_host = phantomjs_module.capture_host

    url = cli_parsed.single
    http_object = objects.HTTPTableObject()
    http_object.remote_system = url
    http_object.set_paths(
        cli_parsed.d, 'baseline' if cli_parsed.cycle is not None else None)

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)

    if cli_parsed.cycle is not None:
        print 'Making baseline request for {0}'.format(http_object.remote_system)
    else:
        print 'Attempting to screenshot {0}'.format(http_object.remote_system)
    driver = create_driver(cli_parsed)
    result = capture_host(cli_parsed, http_object, driver)

    result = default_creds_category(result)
    if cli_parsed.cycle is not None and result.error_state is None:
        ua_dict = get_ua_values(cli_parsed.cycle)
        for browser_key, user_agent_value in ua_dict.iteritems():
            print 'Now making web request with: {0} for {1}'.format(
                browser_key, result.remote_system)
            ua_object = objects.UAObject(browser_key, user_agent_value)
            ua_object.copy_data(result)
            driver = create_driver(cli_parsed, user_agent_value)
            ua_object = capture_host(cli_parsed, ua_object, driver)
            ua_object = default_creds_category(ua_object)
            result.add_ua_data(ua_object)
    if display is not None:
        display.stop()
    html = result.create_table_html()
    with open(os.path.join(cli_parsed.d, 'report.html'), 'w') as f:
        f.write(web_index_head)
        f.write(create_table_head())
        f.write(html)
        f.write("</table><br>")


def worker_thread(cli_parsed, targets, data, lock, counter, user_agent=None):
    try:
        if cli_parsed.web:
            create_driver = selenium_module.create_driver
            capture_host = selenium_module.capture_host
        elif cli_parsed.headless:
            create_driver = phantomjs_module.create_driver
            capture_host = phantomjs_module.capture_host
        with lock:
            driver = create_driver(cli_parsed, user_agent)
        while True:
            http_object = targets.get()
            if http_object is None:
                break

            if cli_parsed.cycle is not None:
                if user_agent is None:
                    print 'Making baseline request for {0}'.format(http_object.remote_system)
                else:
                    browser_key, user_agent_str = user_agent
                    print 'Now making web request with: {0} for {1}'.format(
                        browser_key, http_object.remote_system)
            else:
                print 'Attempting to screenshot {0}'.format(http_object.remote_system)
            if user_agent is not None:
                if http_object.error_state is None:
                    ua_object = objects.UAObject(browser_key, user_agent_str)
                    ua_object.copy_data(http_object)
                    ua_object, driver = capture_host(cli_parsed, ua_object, driver)
                    if ua_object.category is None:
                        ua_object = default_creds_category(ua_object)
                    http_object.add_ua_data(ua_object)
                    data.put(http_object)
                else:
                    data.put(http_object)
            else:
                http_object, driver = capture_host(cli_parsed, http_object, driver)
                if http_object.category is None:
                    http_object = default_creds_category(http_object)
                data.put(http_object)
            counter[0].value += 1
            if counter[0].value % 15 == 0:
                print '\x1b[32m[*] Completed {0} out of {1} hosts\x1b[0m'.format(counter[0].value, counter[1])
            do_jitter(cli_parsed)
    except KeyboardInterrupt:
        print 'kbinterrupt'

    driver.quit()


def single_vnc_rdp(cli_parsed, engine, url=None, q=None):
    if url is None:
        url = cli_parsed.single
    if engine == 'vnc':
        capture_host = vnc_module.capture_host

        if ':' in url:
            ip, port = url.split(':')
            port = int(port)
        else:
            ip, port = url, 5900

        obj = objects.VNCRDPTableObject('vnc')
    else:
        capture_host = rdp_module.capture_host

        if ':' in url:
            ip, port = url.split(':')
            port = int(port)
        else:
            ip, port = url, 3389

        obj = objects.VNCRDPTableObject('rdp')

    obj.remote_system = ip
    obj.port = port
    obj.set_paths(cli_parsed.d)

    capture_host(cli_parsed, obj)

    if q is None:
        html = obj.create_table_html()
        with open(os.path.join(cli_parsed.d, engine + '_report.html'), 'w') as f:
            f.write(vnc_rdp_header(cli_parsed.date, cli_parsed.time))
            f.write(vnc_rdp_table_head())
            f.write(html)
            f.write("</table><br>")
    else:
        q.put(obj)


def multi_mode(cli_parsed):
    m = Manager()
    data = m.Queue()
    targets = m.Queue()
    lock = m.Lock()
    multi_counter = m.Value('i', 0)
    threads = []
    display = None

    url_list, rdp_list, vnc_list = target_creator(cli_parsed)
    multi_total = len(url_list)

    if any((cli_parsed.web, cli_parsed.headless)):
        print 'Starting Web Requests'
        multi_total = len(url_list)
        if multi_total < cli_parsed.threads:
            num_threads = multi_total
        else:
            num_threads = cli_parsed.threads
        if cli_parsed.web and not cli_parsed.show_selenium:
            display = Display(visible=0, size=(1920, 1080))
            display.start()
        for url in url_list:
            http_object = objects.HTTPTableObject()
            http_object.remote_system = url
            http_object.set_paths(cli_parsed.d, 'baseline' if cli_parsed.cycle is not None else None)
            targets.put(http_object)
        for i in xrange(cli_parsed.threads):
            targets.put(None)
        try:
            workers = [Process(target=worker_thread, args=(cli_parsed, targets, data, lock, (multi_counter, multi_total))) for i in xrange(num_threads)]
            for w in workers:
                w.start()
            for w in workers:
                w.join()
            if cli_parsed.cycle is not None:
                ua_dict = get_ua_values(cli_parsed.cycle)
                for ua_value in ua_dict.iteritems():
                    multi_counter.value = 0
                    while not targets.empty():
                        targets.get()
                    while not data.empty():
                        targets.put(data.get())
                    for i in xrange(cli_parsed.threads):
                        targets.put(None)
                    workers = [Process(target=worker_thread, args=(cli_parsed, targets, data, lock, (multi_counter, multi_total), ua_value)) for i in xrange(cli_parsed.threads)]
                    for w in workers:
                        w.start()
                    for w in workers:
                        w.join()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print str(e)

    p = Pool(cli_parsed.threads)
    if any((cli_parsed.vnc, cli_parsed.rdp)):
        print 'Staring VNC/RDP Requests'
        multi_total = len(vnc_list) + len(rdp_list)
        multi_counter.value = 0
        if cli_parsed.vnc:
            for vnc in vnc_list:
                threads.append(
                    p.apply_async(single_vnc_rdp, [cli_parsed, 'vnc', vnc, data], callback=multi_callback))

        if cli_parsed.rdp:
            for rdp in rdp_list:
                threads.append(
                    p.apply_async(single_vnc_rdp, [cli_parsed, 'rdp', rdp, data], callback=multi_callback))

    p.close()
    try:
        while not all([r.ready() for r in threads]):
            time.sleep(1)
    except KeyboardInterrupt:
        p.terminate()
        p.join()
    if display is not None:
        display.stop()
    results = []
    while not data.empty():
        results.append(data.get())
    m.shutdown()
    sort_data_and_write(cli_parsed, results)


def open_file_input():
    print 'Would you like to open the report now? [y/n]',
    while True:
        try:
            return strtobool(raw_input().lower())
        except ValueError:
            print "Please respond with y or n",


if __name__ == "__main__":
    title_screen()
    cli_parsed = create_cli_parser()
    start_time = time.time()

    if cli_parsed.createtargets:
        target_creator(cli_parsed)
        sys.exit()

    create_folders_css(cli_parsed)

    if cli_parsed.single:
        if any((cli_parsed.web, cli_parsed.headless)):
            single_mode(cli_parsed)
        elif cli_parsed.rdp:
            single_vnc_rdp(cli_parsed, 'rdp')
        elif cli_parsed.vnc:
            single_vnc_rdp(cli_parsed, 'vnc')
        print(
            '\n[*] Done! Check out the report in the {0} folder!').format(cli_parsed.d)
        if not cli_parsed.no_prompt:
            open_file = open_file_input()
            if open_file:
                files = glob.glob(os.path.join(cli_parsed.d, '*report.html'))
                for f in files:
                    webbrowser.open(f)
        sys.exit()

    if cli_parsed.f is not None:
        multi_mode(cli_parsed)

    print 'Finished in {0} seconds'.format(time.time() - start_time)

    print('\n[*] Done! Report written in the {0} folder!').format(
        cli_parsed.d)

    if not cli_parsed.no_prompt:
        open_file = open_file_input()
        if open_file:
            files = glob.glob(os.path.join(cli_parsed.d, '*report.html'))
            for f in files:
                webbrowser.open(f)
