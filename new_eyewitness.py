#!/usr/bin/env python

import argparse
import logging
import netaddr
import os
import re
import sys
import time

from fuzzywuzzy import fuzz
from pyvirtualdisplay import Display
from helpers import create_folders_css
from helpers import create_table_head
from helpers import create_web_index_head
from helpers import default_creds_category
from helpers import get_ua_values
from helpers import sort_data_and_write
from helpers import target_creator
from helpers import title_screen
from helpers import do_jitter
from modules import ghost_module
from modules import objects
from modules import phantomjs_module
from modules import selenium_module
from multiprocessing import Manager
from multiprocessing import Pool
from multiprocessing import Process
from multiprocessing import Queue


multi_counter = 0
multi_total = 0
display = None


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
    protocols.add_argument('--engine', default=None,
                           metavar='Screenshot Engine to use',
                           help=('Which engine to use for screenshotting \
                            (selenium, phantomjs, ghost'))

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
            args.d = args.d.rstrip('/', '\\')
        else:
            args.d = os.path.join(local_path, args.d)

        if not os.access(os.path.dirname(args.d), os.W_OK):
            print '[*] Error: Please provide a valid folder name/path'
            parser.print_help()
            sys.exit()
        else:
            if os.path.isdir(args.d):
                overwrite_dir = raw_input('Directory Exists! Do you want to\
                 overwrite? [y/n]')
                overwrite_dir = overwrite_dir.lower().strip()
                if overwrite_dir == 'n':
                    print 'Quitting...Restart and provide the proper\
                     directory to write to!'
                    sys.exit()
                elif overwrite_dir == 'y':
                    pass
                else:
                    print 'Quitting since you didn\'t provide \
                    a valid response...'
                    sys.exit()

    else:
        output_folder = args.date.replace(
            '/', '') + '_' + args.time.replace(':', '')
        args.d = os.path.join(local_path, output_folder)

    args.log_file_path = os.path.join(args.d, 'logfile.log')

    if args.f is None and args.single is None:
        print "[*] Error: You didn't specify a file! I need a file containing\
         URLs!"
        parser.print_help()
        sys.exit()

    if not any((args.engine, args.web, args.vnc, args.rdp, args.all_protocols, args.headless)):
        print "[*] Error: You didn't give me an action to perform."
        print "[*] Error: Please use --web, --rdp, or --vnc!\n"
        parser.print_help()
        sys.exit()

    if args.all_protocols:
        args.web = True
        args.vnc = True
        args.rdp = True

    return args


def single_mode(cli_parsed, url=None, q=None):
    display = None
    if cli_parsed.engine == 'selenium':
        create_driver = selenium_module.create_driver
        capture_host = selenium_module.capture_host
        display = Display(visible=0, size=(1920, 1080))
        display.start()
    elif cli_parsed.engine == 'phantomjs':
        create_driver = phantomjs_module.create_driver
        capture_host = phantomjs_module.capture_host
    else:
        print '[*] No valid engine provided! Choose phantomjs or selenium!'
        sys.exit(0)

    if url is None:
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

    result = default_creds_category(cli_parsed, result)
    if cli_parsed.cycle is not None and result.error_state is None:
        ua_dict = get_ua_values(cli_parsed.cycle)
        for browser_key, user_agent_value in ua_dict.iteritems():
            print 'Now making web request with: {0} for {1}'.format(
                browser_key, result.remote_system)
            ua_object = objects.UAObject(browser_key, user_agent_value)
            ua_object.copy_data(result)
            driver = create_driver(cli_parsed, user_agent_value)
            ua_object = capture_host(cli_parsed, ua_object, driver)
            ua_object = default_creds_category(cli_parsed, ua_object)
            result.add_ua_data(ua_object)
    if display is not None:
        display.stop()
    if q is None:
        html = result.create_table_html()
        print(
            '\n[*] Done! Check out the report in the {0} folder!').format(cli_parsed.d)
        with open(os.path.join(cli_parsed.d, 'report.html'), 'w') as f:
            f.write(web_index_head)
            f.write(create_table_head())
            f.write(html)
            f.write("</table><br>")
    else:
        q.put(result)
        do_jitter(cli_parsed)


def multi_mode(cli_parsed):
    global multi_total
    p = Pool(cli_parsed.threads)
    m = Manager()
    data = m.Queue()
    threads = []

    url_list, rdp_list, vnc_List = target_creator(cli_parsed)
    multi_total = len(url_list)
    for url in url_list:
        threads.append(
            p.apply_async(single_mode, [cli_parsed, url, data], callback=multi_callback))

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

    sort_data_and_write(cli_parsed, results)


def multi_callback(x):
    global multi_counter
    global multi_total
    multi_counter += 1

    if multi_counter % 15 == 0:
        print '\x1b[32m[*] Completed {0} out of {1} hosts\x1b[0m'.format(multi_counter, multi_total)


if __name__ == "__main__":
    title_screen()
    cli_parsed = create_cli_parser()

    if cli_parsed.createtargets:
        target_creator(cli_parsed)
        sys.exit()

    create_folders_css(cli_parsed)

    if cli_parsed.engine == 'ghost':
        logging.basicConfig(filename=cli_parsed.log_file_path,
                            level=logging.WARNING)
        logger = logging.getLogger('ghost')

    if cli_parsed.single:
        single_mode(cli_parsed)

    if cli_parsed.f is not None:
        multi_mode(cli_parsed)

    print('\n[*] Done! Check out the report in the {0} folder!').format(
        cli_parsed.d)
