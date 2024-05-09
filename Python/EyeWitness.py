#!/usr/bin/env python3

import argparse
import glob
import os
import re
import shutil
import signal
import sys
import time
import webbrowser

from modules import db_manager
from modules import objects
from modules import selenium_module
from modules.helpers import class_info
from modules.helpers import create_folders_css
from modules.helpers import default_creds_category
from modules.helpers import do_jitter
from modules.helpers import get_ua_values
from modules.helpers import target_creator
from modules.helpers import title_screen
from modules.helpers import open_file_input
from modules.helpers import resolve_host
from modules.helpers import duplicate_check
from modules.reporting import create_table_head
from modules.reporting import create_web_index_head
from modules.reporting import sort_data_and_write
from multiprocessing import Manager
from multiprocessing import Process
from multiprocessing import current_process
try:
    from pyvirtualdisplay import Display
except ImportError:
    print('[*] pyvirtualdisplay not found.')
    print('[*] Please run the script in the setup directory!')
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
    protocols.add_argument('--web', default=True, action='store_true',
                           help='HTTP Screenshot using Selenium')

    input_options = parser.add_argument_group('Input Options')
    input_options.add_argument('-f', metavar='Filename', default=None,
                               help='Line-separated file containing URLs to \
                                capture')
    input_options.add_argument('-x', metavar='Filename.xml', default=None,
                               help='Nmap XML or .Nessus file')
    input_options.add_argument('--single', metavar='Single URL', default=None,
                               help='Single URL/Host to capture')
    input_options.add_argument('--no-dns', default=False, action='store_true',
                               help='Skip DNS resolution when connecting to \
                            websites')

    timing_options = parser.add_argument_group('Timing Options')
    timing_options.add_argument('--timeout', metavar='Timeout', default=7, type=int,
                                help='Maximum number of seconds to wait while\
                                 requesting a web page (Default: 7)')
    timing_options.add_argument('--jitter', metavar='# of Seconds', default=0,
                                type=int, help='Randomize URLs and add a random\
                                 delay between requests')
    timing_options.add_argument('--delay', metavar='# of Seconds', default=0,
                                type=int, help='Delay between the opening of the navigator and taking the screenshot')
    timing_options.add_argument('--threads', metavar='# of Threads', default=10,
                                type=int, help='Number of threads to use while using\
                                file based input')
    timing_options.add_argument('--max-retries', default=1, metavar='Max retries on \
                                a timeout'.replace('    ', ''), type=int,
                                help='Max retries on timeouts')

    report_options = parser.add_argument_group('Report Output Options')
    report_options.add_argument('-d', metavar='Directory Name',
                                default=None,
                                help='Directory name for report output')
    report_options.add_argument('--results', metavar='Hosts Per Page',
                                default=25, type=int, help='Number of Hosts per\
                                 page of report')
    report_options.add_argument('--no-prompt', default=False,
                                action='store_true',
                                help='Don\'t prompt to open the report')
    report_options.add_argument('--no-clear', default=False,
                                action='store_true',
                                help='Don\'t clear screen buffer')

    http_options = parser.add_argument_group('Web Options')
    http_options.add_argument('--user-agent', metavar='User Agent',
                              default=None, help='User Agent to use for all\
                               requests')
    http_options.add_argument('--difference', metavar='Difference Threshold',
                              default=50, type=int, help='Difference threshold\
                               when determining if user agent requests are\
                                close \"enough\" (Default: 50)')
    http_options.add_argument('--proxy-ip', metavar='127.0.0.1', default=None,
                              help='IP of web proxy to go through')
    http_options.add_argument('--proxy-port', metavar='8080', default=None,
                              type=int, help='Port of web proxy to go through')
    http_options.add_argument('--proxy-type', metavar='socks5', default="http",
                              help='Proxy type (socks5/http)')
    http_options.add_argument('--show-selenium', default=False,
                              action='store_true', help='Show display for selenium')
    http_options.add_argument('--resolve', default=False,
                              action='store_true', help=("Resolve IP/Hostname"
                                                         " for targets"))
    http_options.add_argument('--add-http-ports', default=[], 
                              type=lambda s:[str(i) for i in s.split(",")],
                              help=("Comma-separated additional port(s) to assume "
                              "are http (e.g. '8018,8028')"))
    http_options.add_argument('--add-https-ports', default=[],
                              type=lambda s:[str(i) for i in s.split(",")],
                              help=("Comma-separated additional port(s) to assume "
                              "are https (e.g. '8018,8028')"))
    http_options.add_argument('--only-ports', default=[],
                              type=lambda s:[int(i) for i in s.split(",")],
                              help=("Comma-separated list of exclusive ports to "
                              "use (e.g. '80,8080')"))
    http_options.add_argument('--prepend-https', default=False, action='store_true',
                              help='Prepend http:// and https:// to URLs without either')
    http_options.add_argument('--selenium-log-path', default='./geckodriver.log', action='store',
                              help='Selenium geckodriver log path')
    http_options.add_argument('--cookies', metavar='key1=value1,key2=value2', default=None,
                              help='Additional cookies to add to the request')

    resume_options = parser.add_argument_group('Resume Options')
    resume_options.add_argument('--resume', metavar='ew.db',
                                default=None, help='Path to db file if you want to resume')

    args = parser.parse_args()
    args.date = time.strftime('%Y/%m/%d')
    args.time = time.strftime('%H:%M:%S')

    if args.h:
        parser.print_help()
        sys.exit()

    if args.f is None and args.single is None and args.resume is None and args.x is None:
        print("[*] Error: You didn't specify a file! I need a file containing "
              "URLs!")
        parser.print_help()
        sys.exit()

    if ((args.f is not None) and not os.path.isfile(args.f)) or ((args.x is not None) and not os.path.isfile(args.x)):
        print("[*] Error: You didn't specify the correct path to a file. Try again!\n")
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
            print('[*] Error: Please provide a valid folder name/path')
            parser.print_help()
            sys.exit()
        else:
            if not args.no_prompt:
                if os.path.isdir(args.d):
                    overwrite_dir = input(('Directory Exists! Do you want to '
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
            '/', '-') + '_' + args.time.replace(':', '')
        args.d = os.path.join(os.getcwd(), output_folder)

    args.log_file_path = os.path.join(args.d, 'logfile.log')

    if not any((args.resume, args.web)):
        print("[*] Error: You didn't give me an action to perform.")
        print("[*] Error: Please use --web!\n")
        parser.print_help()
        sys.exit()

    if args.resume:
        if not os.path.isfile(args.resume):
            print(" [*] Error: No valid DB file provided for resume!")
            sys.exit()

    if args.proxy_ip is not None and args.proxy_port is None:
        print("[*] Error: Please provide a port for the proxy!")
        parser.print_help()
        sys.exit()

    if args.proxy_port is not None and args.proxy_ip is None:
        print("[*] Error: Please provide an IP for the proxy!")
        parser.print_help()
        sys.exit()

    if args.cookies:
        cookies_list = []
        for one_cookie in args.cookies.split(","):
            if "=" not in args.cookies:
                print("[*] Error: Cookies must be in the form of key1=value1,key2=value2")
                sys.exit()
            cookies_list.append({
                "name": one_cookie.split("=")[0],
                "value": one_cookie.split("=")[1]
            })
        args.cookies = cookies_list
    args.ua_init = False
    return args


def single_mode(cli_parsed):
    display = None
    
    def exitsig(*args):
        if current_process().name == 'MainProcess':
            print('')
            print('Quitting...')
        os._exit(1)

    signal.signal(signal.SIGINT, exitsig)

    if cli_parsed.web:
        create_driver = selenium_module.create_driver
        capture_host = selenium_module.capture_host
        if not cli_parsed.show_selenium:
            display = Display(visible=0, size=(1920, 1080))
            display.start()

    url = cli_parsed.single
    http_object = objects.HTTPTableObject()
    http_object.remote_system = url
    http_object.set_paths(
        cli_parsed.d, None)

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)

    driver = create_driver(cli_parsed)
    result, driver = capture_host(cli_parsed, http_object, driver)
    result = default_creds_category(result)
    if cli_parsed.resolve:
        result.resolved = resolve_host(result.remote_system)
    driver.quit()
    if display is not None:
        display.stop()
    html = result.create_table_html()
    with open(os.path.join(cli_parsed.d, 'report.html'), 'w') as f:
        f.write(web_index_head)
        f.write(create_table_head())
        f.write(html)
        f.write("</table><br>")


def worker_thread(cli_parsed, targets, lock, counter, user_agent=None):
    manager = db_manager.DB_Manager(cli_parsed.d + '/ew.db')
    manager.open_connection()

    if cli_parsed.web:
        create_driver = selenium_module.create_driver
        capture_host = selenium_module.capture_host

    with lock:
        driver = create_driver(cli_parsed, user_agent)
    try:
        while True:
            http_object = targets.get()
            if http_object is None:
                break
            # Try to ensure object values are blank
            http_object._category = None
            http_object._default_creds = None
            http_object._error_state = None
            http_object._page_title = None
            http_object._ssl_error = False
            http_object.category = None
            http_object.default_creds = None
            http_object.error_state = None
            http_object.page_title = None
            http_object.resolved = None
            http_object.source_code = None
            # Fix our directory if its resuming from a different path
            if os.path.dirname(cli_parsed.d) != os.path.dirname(http_object.screenshot_path):
                http_object.set_paths(
                    cli_parsed.d, None)

            print('Attempting to screenshot {0}'.format(http_object.remote_system))

            http_object.resolved = resolve_host(http_object.remote_system)
            if user_agent is None:
                http_object, driver = capture_host(
                    cli_parsed, http_object, driver)
                if http_object.category is None and http_object.error_state is None:
                    http_object = default_creds_category(http_object)
                manager.update_http_object(http_object)
            else:
                ua_object, driver = capture_host(
                    cli_parsed, http_object, driver)
                if http_object.category is None and http_object.error_state is None:
                    ua_object = default_creds_category(ua_object)
                manager.update_ua_object(ua_object)

            counter[0].value += 1
            if counter[0].value % 15 == 0:
                print('\x1b[32m[*] Completed {0} out of {1} services\x1b[0m'.format(counter[0].value, counter[1]))
            do_jitter(cli_parsed)
    except KeyboardInterrupt:
        pass
    manager.close()
    driver.quit()


def multi_mode(cli_parsed):
    dbm = db_manager.DB_Manager(cli_parsed.d + '/ew.db')
    dbm.open_connection()
    if not cli_parsed.resume:
        dbm.initialize_db()
    dbm.save_options(cli_parsed)
    m = Manager()
    targets = m.Queue()
    lock = m.Lock()
    multi_counter = m.Value('i', 0)
    display = None

    def exitsig(*args):
        dbm.close()
        if current_process().name == 'MainProcess':
            print('')
            print('Resume using ./EyeWitness.py --resume {0}'.format(cli_parsed.d + '/ew.db'))
        os._exit(1)

    signal.signal(signal.SIGINT, exitsig)
    if cli_parsed.resume:
        pass
    else:
        url_list = target_creator(cli_parsed)
        if cli_parsed.web:
            for url in url_list:
                dbm.create_http_object(url, cli_parsed)

    if cli_parsed.web:
        if cli_parsed.web and not cli_parsed.show_selenium:
            display = Display(visible=0, size=(1920, 1080))
            display.start()

        multi_total = dbm.get_incomplete_http(targets)
        if multi_total > 0:
            if cli_parsed.resume:
                print('Resuming Web Scan ({0} Hosts Remaining)'.format(str(multi_total)))
            else:
                print('Starting Web Requests ({0} Hosts)'.format(str(multi_total)))

        if multi_total < cli_parsed.threads:
            num_threads = multi_total
        else:
            num_threads = cli_parsed.threads
        for i in range(num_threads):
            targets.put(None)
        try:
            workers = [Process(target=worker_thread, args=(
                cli_parsed, targets, lock, (multi_counter, multi_total))) for i in range(num_threads)]
            for w in workers:
                w.start()
            for w in workers:
                w.join()
        except Exception as e:
            print(str(e))

    if display is not None:
        display.stop()
    results = dbm.get_complete_http()
    dbm.close()
    m.shutdown()
    sort_data_and_write(cli_parsed, results)


def multi_callback(x):
    global multi_counter
    global multi_total
    multi_counter += 1

    if multi_counter % 15 == 0:
        print('\x1b[32m[*] Completed {0} out of {1} hosts\x1b[0m'.format(multi_counter, multi_total))


if __name__ == "__main__":
    cli_parsed = create_cli_parser()
    start_time = time.time()
    title_screen(cli_parsed)
    
    if cli_parsed.resume:
        print('[*] Loading Resume Data...')
        temp = cli_parsed
        dbm = db_manager.DB_Manager(cli_parsed.resume)
        dbm.open_connection()
        cli_parsed = dbm.get_options()
        cli_parsed.d = os.path.dirname(temp.resume)
        cli_parsed.resume = temp.resume
        if temp.results:
            cli_parsed.results = temp.results
        dbm.close()

        print('Loaded Resume Data with the following options:')
        engines = []
        if cli_parsed.web:
            engines.append('Firefox')
        print('')
        print('Input File: {0}'.format(cli_parsed.f))
        print('Engine(s): {0}'.format(','.join(engines)))
        print('Threads: {0}'.format(cli_parsed.threads))
        print('Output Directory: {0}'.format(cli_parsed.d))
        print('Timeout: {0}'.format(cli_parsed.timeout))
        print('')
    else:
        create_folders_css(cli_parsed)

    if cli_parsed.single:
        if cli_parsed.web:
            single_mode(cli_parsed)
        if not cli_parsed.no_prompt:
            open_file = open_file_input(cli_parsed)
            if open_file:
                files = glob.glob(os.path.join(cli_parsed.d, '*report.html'))
                for f in files:
                    webbrowser.open(f)
                    class_info()
                    sys.exit()
        class_info()
        sys.exit()

    if cli_parsed.f is not None or cli_parsed.x is not None:
        multi_mode(cli_parsed)
        duplicate_check(cli_parsed)

    print('Finished in {0} seconds'.format(time.time() - start_time))

    if not cli_parsed.no_prompt:
        open_file = open_file_input(cli_parsed)
        if open_file:
            files = glob.glob(os.path.join(cli_parsed.d, '*report.html'))
            for f in files:
                webbrowser.open(f)
                class_info()
                sys.exit()
        class_info()
        sys.exit()
