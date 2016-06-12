#!/usr/bin/env python

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
from modules import phantomjs_module
from modules import rdp_module
from modules import selenium_module
from modules import vnc_module
from modules.helpers import create_folders_css
from modules.helpers import default_creds_category
from modules.helpers import do_jitter
from modules.helpers import get_ua_values
from modules.helpers import target_creator
from modules.helpers import title_screen
from modules.helpers import open_file_input
from modules.helpers import resolve_host
from modules.reporting import create_table_head
from modules.reporting import create_web_index_head
from modules.reporting import sort_data_and_write
from modules.reporting import vnc_rdp_header
from modules.reporting import vnc_rdp_table_head
from modules.reporting import write_vnc_rdp_data
from multiprocessing import Manager
from multiprocessing import Process
from multiprocessing import current_process
try:
    from pyvirtualdisplay import Display
    import rdpy.core.log as log
    from PyQt4 import QtGui
    from PyQt4.QtCore import QTimer
except ImportError:
    print '[*] pyvirtualdisplay not found.'
    print '[*] Please run the script in the setup directory!'
    sys.exit()

reload(sys)
sys.setdefaultencoding('utf8')

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
                                capture')
    input_options.add_argument('-x', metavar='Filename.xml', default=None,
                               help='Nmap XML or .Nessus file')
    input_options.add_argument('--single', metavar='Single URL', default=None,
                               help='Single URL/Host to capture')
    input_options.add_argument('--createtargets', metavar='targetfilename.txt',
                               default=None, help='Parses a .nessus or Nmap XML \
                            file into a line-seperated list of URLs')
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
    http_options.add_argument('--resolve', default=False,
                              action='store_true', help=("Resolve IP/Hostname"
                                                         " for targets"))
    http_options.add_argument('--add-http-ports', default=[], 
                              type=lambda s:[int(i) for i in s.split(",")],
                              help=("Comma-seperated additional port(s) to assume "
                              "are http (e.g. '8018,8028')"))
    http_options.add_argument('--add-https-ports', default=[],
                              type=lambda s:[int(i) for i in s.split(",")],
                              help=("Comma-seperated additional port(s) to assume "
                              "are https (e.g. '8018,8028')"))
    http_options.add_argument('--prepend-https', default=False, action='store_true',
                              help='Prepend http:\\\\ and https:\\\\ to URLs without either')
    http_options.add_argument('--vhost-name', default=None,metavar='hostname', help='Hostname to use in Host header (headless + single mode only)')
    http_options.add_argument(
        '--active-scan', default=False, action='store_true',
        help='Perform live login attempts to identify credentials or login pages.')

    resume_options = parser.add_argument_group('Resume Options')
    resume_options.add_argument('--resume', metavar='ew.db',
                                default=None, help='Path to db file if you want to resume')

    args = parser.parse_args()
    args.date = time.strftime('%m/%d/%Y')
    args.time = time.strftime('%H:%M:%S')

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

    if args.f is None and args.single is None and args.resume is None and args.x is None:
        print("[*] Error: You didn't specify a file! I need a file containing "
              "URLs!")
        parser.print_help()
        sys.exit()

    if not any((args.resume, args.web, args.vnc, args.rdp, args.all_protocols, args.headless)):
        print "[*] Error: You didn't give me an action to perform."
        print "[*] Error: Please use --web, --rdp, or --vnc!\n"
        parser.print_help()
        sys.exit()

    if all((args.web, args.headless)):
        print "[*] Error: Choose either web or headless"
        parser.print_help()
        sys.exit()

    if args.vhost_name and not all((args.single, args.headless)):
        print "[*] Error: vhostname can only be used in headless+single mode"
        sys.exit()
    
    if args.proxy_ip is not None and args.proxy_port is None:
        print "[*] Error: Please provide a port for the proxy!"
        parser.print_help()
        sys.exit()

    if args.proxy_port is not None and args.proxy_ip is None:
        print "[*] Error: Please provide an IP for the proxy!"
        parser.print_help()
        sys.exit()

    if args.resume:
        if not os.path.isfile(args.resume):
            print(" [*] Error: No valid DB file provided for resume!")
            sys.exit()

    if args.all_protocols:
        args.web = True
        args.vnc = True
        args.rdp = True

    args.ua_init = False
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
    if cli_parsed.active_scan:
        http_object._active_scan = True
    http_object.remote_system = url
    http_object.set_paths(
        cli_parsed.d, 'baseline' if cli_parsed.cycle is not None else None)
    if cli_parsed.active_scan:
        http_object._active_scan = True

    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)

    if cli_parsed.cycle is not None:
        print 'Making baseline request for {0}'.format(http_object.remote_system)
    else:
        print 'Attempting to screenshot {0}'.format(http_object.remote_system)
    driver = create_driver(cli_parsed)
    result, driver = capture_host(cli_parsed, http_object, driver)
    result = default_creds_category(result)
    if cli_parsed.resolve:
        result.resolved = resolve_host(result.remote_system)
    driver.quit()
    if cli_parsed.cycle is not None and result.error_state is None:
        ua_dict = get_ua_values(cli_parsed.cycle)
        for browser_key, user_agent_value in ua_dict.iteritems():
            print 'Now making web request with: {0} for {1}'.format(
                browser_key, result.remote_system)
            ua_object = objects.UAObject(browser_key, user_agent_value)
            ua_object.copy_data(result)
            driver = create_driver(cli_parsed, user_agent_value)
            ua_object, driver = capture_host(cli_parsed, ua_object, driver)
            ua_object = default_creds_category(ua_object)
            result.add_ua_data(ua_object)
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
    elif cli_parsed.headless:
        create_driver = phantomjs_module.create_driver
        capture_host = phantomjs_module.capture_host
    with lock:
        driver = create_driver(cli_parsed, user_agent)
    try:
        while True:
            http_object = targets.get()
            if http_object is None:
                break
            # Fix our directory if its resuming from a different path
            if os.path.dirname(cli_parsed.d) != os.path.dirname(http_object.screenshot_path):
                http_object.set_paths(
                    cli_parsed.d, 'baseline' if cli_parsed.cycle is not None else None)

            if cli_parsed.cycle is not None:
                if user_agent is None:
                    print 'Making baseline request for {0}'.format(http_object.remote_system)
                else:
                    browser_key, user_agent_str = user_agent
                    print 'Now making web request with: {0} for {1}'.format(
                        browser_key, http_object.remote_system)
            else:
                print 'Attempting to screenshot {0}'.format(http_object.remote_system)

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
                print '\x1b[32m[*] Completed {0} out of {1} services\x1b[0m'.format(counter[0].value, counter[1])
            do_jitter(cli_parsed)
    except KeyboardInterrupt:
        pass
    manager.close()
    driver.quit()


def single_vnc_rdp(cli_parsed, engine):
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

    html = obj.create_table_html()
    with open(os.path.join(cli_parsed.d, engine + '_report.html'), 'w') as f:
        f.write(vnc_rdp_header(cli_parsed.date, cli_parsed.time))
        f.write(vnc_rdp_table_head())
        f.write(html)
        f.write("</table><br>")


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
            print ''
            print 'Resume using ./EyeWitness.py --resume {0}'.format(cli_parsed.d + '/ew.db')
        os._exit(1)

    signal.signal(signal.SIGINT, exitsig)
    if cli_parsed.resume:
        pass
    else:
        url_list, rdp_list, vnc_list = target_creator(cli_parsed)
        if any((cli_parsed.web, cli_parsed.headless)):
            for url in url_list:
                dbm.create_http_object(url, cli_parsed)
        for rdp in rdp_list:
            dbm.create_vnc_rdp_object('rdp', rdp, cli_parsed)
        for vnc in vnc_list:
            dbm.create_vnc_rdp_object('vnc', vnc, cli_parsed)

    if any((cli_parsed.web, cli_parsed.headless)):
        if cli_parsed.web and not cli_parsed.show_selenium:
            display = Display(visible=0, size=(1920, 1080))
            display.start()

        multi_total = dbm.get_incomplete_http(targets)
        if multi_total > 0:
            if cli_parsed.resume:
                print 'Resuming Web Scan ({0} Hosts Remaining)'.format(str(multi_total))
            else:
                print 'Starting Web Requests ({0} Hosts)'.format(str(multi_total))

        if multi_total < cli_parsed.threads:
            num_threads = multi_total
        else:
            num_threads = cli_parsed.threads
        for i in xrange(num_threads):
            targets.put(None)
        try:
            workers = [Process(target=worker_thread, args=(
                cli_parsed, targets, lock, (multi_counter, multi_total))) for i in xrange(num_threads)]
            for w in workers:
                w.start()
            for w in workers:
                w.join()
        except Exception as e:
            print str(e)

        # Set up UA table here
        if cli_parsed.cycle is not None:
            ua_dict = get_ua_values(cli_parsed.cycle)
            if not cli_parsed.ua_init:
                dbm.clear_table("ua")
                completed = dbm.get_complete_http()
                completed[:] = [x for x in completed if x.error_state is None]
                for item in completed:
                    for browser, ua in ua_dict.iteritems():
                        dbm.create_ua_object(item, browser, ua)

                cli_parsed.ua_init = True
                dbm.clear_table("opts")
                dbm.save_options(cli_parsed)

            for browser, ua in ua_dict.iteritems():
                targets = m.Queue()
                multi_counter.value = 0
                multi_total = dbm.get_incomplete_ua(targets, browser)
                if multi_total > 0:
                    print("[*] Starting requests for User Agent {0}"
                          " ({1} Hosts)").format(browser, str(multi_total))
                if multi_total < cli_parsed.threads:
                    num_threads = multi_total
                else:
                    num_threads = cli_parsed.threads
                for i in xrange(num_threads):
                    targets.put(None)
                workers = [Process(target=worker_thread,
                                   args=(cli_parsed, targets, lock,
                                         (multi_counter, multi_total),
                                         (browser, ua)))
                           for i in xrange(num_threads)]
                for w in workers:
                    w.start()
                for w in workers:
                    w.join()

    if any((cli_parsed.vnc, cli_parsed.rdp)):
        log._LOG_LEVEL = log.Level.ERROR
        multi_total, targets = dbm.get_incomplete_vnc_rdp()
        if multi_total > 0:
            print ''
            print 'Starting VNC/RDP Requests ({0} Hosts)'.format(str(multi_total))

            app = QtGui.QApplication(sys.argv)
            timer = QTimer()
            timer.start(10)
            timer.timeout.connect(lambda: None)

            # add qt4 reactor
            import qt4reactor
            qt4reactor.install()
            from twisted.internet import reactor

            for target in targets:
                if os.path.dirname(cli_parsed.d) != os.path.dirname(target.screenshot_path):
                    target.set_paths(cli_parsed.d)
                tdbm = db_manager.DB_Manager(cli_parsed.d + '/ew.db')
                if target.proto == 'vnc':
                    reactor.connectTCP(
                        target.remote_system, target.port,
                        vnc_module.RFBScreenShotFactory(
                            target.screenshot_path, reactor, app,
                            target, tdbm))
                else:
                    reactor.connectTCP(
                        target.remote_system, int(target.port),
                        rdp_module.RDPScreenShotFactory(
                            reactor, app, 1200, 800,
                            target.screenshot_path, cli_parsed.timeout,
                            target, tdbm))
            reactor.runReturn()
            app.exec_()

    if display is not None:
        display.stop()
    results = dbm.get_complete_http()
    vnc_rdp = dbm.get_complete_vnc_rdp()
    dbm.close()
    m.shutdown()
    write_vnc_rdp_data(cli_parsed, vnc_rdp)
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
    start_time = time.time()

    if cli_parsed.createtargets:
        target_creator(cli_parsed)
        sys.exit()

    if cli_parsed.resume:
        print '[*] Loading Resume Data...'
        temp = cli_parsed
        dbm = db_manager.DB_Manager(cli_parsed.resume)
        dbm.open_connection()
        cli_parsed = dbm.get_options()
        cli_parsed.d = os.path.dirname(temp.resume)
        cli_parsed.resume = temp.resume
        if temp.results:
            cli_parsed.results = temp.results
        dbm.close()

        print 'Loaded Resume Data with the following options:'
        engines = []
        if cli_parsed.web:
            engines.append('Firefox')
        if cli_parsed.headless:
            engines.append('PhantomJS')
        if cli_parsed.vnc:
            engines.append('VNC')
        if cli_parsed.rdp:
            engines.append('RDP')
        print ''
        print 'Input File: {0}'.format(cli_parsed.f)
        print 'Engine(s): {0}'.format(','.join(engines))
        print 'Threads: {0}'.format(cli_parsed.threads)
        print 'Output Directory: {0}'.format(cli_parsed.d)
        print 'Timeout: {0}'.format(cli_parsed.timeout)
        print ''
    else:
        create_folders_css(cli_parsed)

    if cli_parsed.single:
        if any((cli_parsed.web, cli_parsed.headless)):
            single_mode(cli_parsed)
        elif cli_parsed.rdp:
            single_vnc_rdp(cli_parsed, 'rdp')
        elif cli_parsed.vnc:
            single_vnc_rdp(cli_parsed, 'vnc')
        if not cli_parsed.no_prompt:
            open_file = open_file_input(cli_parsed)
            if open_file:
                files = glob.glob(os.path.join(cli_parsed.d, '*report.html'))
                for f in files:
                    webbrowser.open(f)
                    sys.exit()
        sys.exit()

    if cli_parsed.f is not None or cli_parsed.x is not None:
        multi_mode(cli_parsed)

    print 'Finished in {0} seconds'.format(time.time() - start_time)

    if not cli_parsed.no_prompt:
        open_file = open_file_input(cli_parsed)
        if open_file:
            files = glob.glob(os.path.join(cli_parsed.d, '*report.html'))
            for f in files:
                webbrowser.open(f)
                sys.exit()
        sys.exit()
