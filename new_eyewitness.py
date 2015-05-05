import argparse
import netaddr
import os
import re
import sys
import time

from helpers import get_ua_values
from helpers import target_creator
from modules import objects
from modules import phantomjs_module
from modules import selenium_module


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

    localscan_options = parser.add_argument_group('Local Scan Options')
    localscan_options.add_argument('--localscan', metavar='192.168.1.0/24',
                                   default=None, help='CIDR\
                               Notation of network to scan')

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

    if args.f is None and args.single is None and args.localscan is None:
        print "[*] Error: You didn't specify a file! I need a file containing\
         URLs!"
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

    if args.localscan:
        try:
            netaddr.IPAddress(args.localscan)
        except netaddr.core.AddrFormatError:
            print "[*] Error: Please provide valid CIDR notation!"
            print "[*] Example: 192.168.1.0/24"
            sys.exit()

    return args


def create_folders_css(cli_parsed):
    css_page = """img {
    max-width: 100%;
    height: auto;
    }
    #screenshot{
    max-width: 850px;
    max-height: 550px;
    display: inline-block;
    width: 850px;
    height: 550px;
    overflow:scroll;
    }"
    """

    os.makedirs(cli_parsed.d)
    os.makedirs(os.path.join(cli_parsed.d, 'screens'))
    os.makedirs(os.path.join(cli_parsed.d, 'source'))

    with open(os.path.join(cli_parsed.d, 'style.css'), 'w') as f:
        f.write(css_page)

if __name__ == "__main__":
    cli_parsed = create_cli_parser()
    if cli_parsed.localscan:
        raise NotImplementedError

    if cli_parsed.createtargets:
        target_creator(cli_parsed)
        sys.exit()

    create_folders_css(cli_parsed)

    if cli_parsed.single:
        if cli_parsed.web:
            selenium_module.single_mode(cli_parsed)
        elif cli_parsed.headless:
            phantomjs_module.single_mode(cli_parsed)

    if cli_parsed.f is not None:
        if cli_parsed.web:
            selenium_module.multi_mode(cli_parsed)
        elif cli_parsed.headless:
            phantomjs_module.multi_mode(cli_parsed)
