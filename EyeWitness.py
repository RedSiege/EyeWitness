#!/usr/bin/env python

# This is going to be the 2.0 release of EyeWitness.  This is being worked on
# by Christopher Truncer and Rohan Vazarkar.  We're adding in the ability to
# use selenium for screenshot, as well as being able to screenshot RDP and VNC.

import ghost as screener
import argparse
import os
from os.path import join
import time
import sys
import xml.etree.ElementTree as XMLParser
import urllib2
import cgi
import re
import logging
import random
import socket
import difflib
from netaddr import IPNetwork
import platform
import webbrowser


def cli_parser():

    # Command line argument parser
    parser = argparse.ArgumentParser(
        add_help=False,
        description="EyeWitness is a tool used to capture screenshots\
        from a list of URLs")
    parser.add_argument(
        '-h', '-?', '--h', '-help', '--help', action="store_true",
        help=argparse.SUPPRESS)

    protocols = parser.add_argument_group('Protocol Options')
    protocols.add_argument("--web", default=False, action='store_true',
                           help="Screenshot websites!")
    protocols.add_argument("--rdp", default=False, action='store_true',
                           help="Screenshot RDP services!")
    protocols.add_argument("--vnc", default=False, action='store_true',
                           help="Screenshot open VNC services!")
    protocols.add_argument("--all-protocols", default=False,
                           action='store_true', help="Screenshot all\
                           supported protocols!")

    urls_in = parser.add_argument_group('Input Options')
    urls_in.add_argument(
        "-f", metavar="Filename",
        help="File containing URLs to screenshot, each on a new line,\
        NMap XML output, or a .nessus file")
    urls_in.add_argument(
        '--single', metavar="Single URL", default="None",
        help="Single URL to screenshot")
    urls_in.add_argument(
        "--createtargets", metavar="targetfilename.txt", default=None,
        help="Creates text file (of provided name) containing URLs\
        of all targets.")
    urls_in.add_argument(
        "--no-dns", default=False, action='store_true',
        help="Use IP address, not DNS hostnames, when connecting to websites.")

    timing_options = parser.add_argument_group('Timing Options')
    timing_options.add_argument(
        "-t", metavar="Timeout", default=7, type=int,
        help="Maximum number of seconds to wait while\
        requesting a web page (Default: 7)")
    timing_options.add_argument(
        '--jitter', metavar="# of Seconds", default="None",
        help="Randomize URLs and add a random delay between requests")

    report_options = parser.add_argument_group('Report Output Options')
    report_options.add_argument(
        "-d", metavar="Directory Name", default="None",
        help="Directory name for report output")
    report_options.add_argument(
        "--results", metavar="URLs Per Page", default="25", type=int,
        help="Number of URLs per page of the report")

    ua_options = parser.add_argument_group('Web Options')
    ua_options.add_argument(
        '--ghost', metavar="Ghost Screenshot Library", default=False,
        action='store_true', help="Use Ghost to screenshot web pages")
    ua_options.add_argument(
        '--selenium', metavar="Selenium Screenshot Library", default=False,
        action='store_true', help="Use Selenium to screenshot web pages")
    ua_options.add_argument(
        '--useragent', metavar="User Agent", default="None",
        help="User Agent to use for all requests")
    ua_options.add_argument(
        '--cycle', metavar="UA Type", default="None",
        help="User Agent type (Browser, Mobile, Crawler, Scanner, Misc, All)")
    ua_options.add_argument(
        "--difference", metavar="Difference Threshold", default=50, type=int,
        help="Difference threshold when determining if user agent\
        requests are close \"enough\" (Default: 50)")

    scan_options = parser.add_argument_group('Scan Options')
    scan_options.add_argument(
        "--localscan", metavar='192.168.1.0/24', default=False,
        help="CIDR Notation of network to scan")

    args = parser.parse_args()

    current_directory = os.path.dirname(os.path.realpath(__file__))

    if args.h:
        parser.print_help()
        sys.exit()

    if args.d:
        if args.d.startswith('/'):
            args.d = args.d.rstrip("/")
            if not os.access(os.path.dirname(args.d), os.W_OK):
                print "[*] Error: Please provide a valid folder name/Path\n"
                parser.print_help()
                sys.exit()
            else:
                if os.path.isdir(args.d):
                    overwrite_dir = raw_input('Directory Exists!\
                        Do you want to overwrite it? [y/n] ')
                    overwrite_dir = overwrite_dir.lower().strip()
                    if overwrite_dir == "n":
                        print "Quitting... Restart and provice the \
                        proper directory to write to.".replace('    ', '')
                        sys.exit()
                    elif overwrite_dir == "y":
                        pass
                    else:
                        print "Quitting since you didn't provide a valid\
                            response..."
                        sys.exit()
        elif args.d.startswith('C:\\'):
            args.d = args.d.rstrip("\\")
            if not os.access(os.path.dirname(args.d), os.W_OK):
                print "[*] Error: Please provide a valid folder name/Path\n"
                parser.print_help()
                sys.exit()
            else:
                if os.path.isdir(args.d):
                    overwrite_dir = raw_input('Directory Exists! Do you want\
                        to overwrite it? [y/n] ')
                    overwrite_dir = overwrite_dir.lower().strip()
                    if overwrite_dir == "n":
                        print "Quitting... Restart and provice the \
                        proper directory to write to.".replace('    ', '')
                        sys.exit()
                    elif overwrite_dir == "y":
                        pass
                    else:
                        print "Quitting since you didn't provide a valid\
                            response..."
                        sys.exit()
        else:
            file_path = join(current_directory, args.d)
            if not os.access(os.path.dirname(file_path), os.W_OK):
                print "[*] Error: Please provide a valid folder name/Path\n"
                parser.print_help()
                sys.exit()
            else:
                if os.path.isdir(file_path):
                    overwrite_dir = raw_input('Directory Exists! Do you want\
                        to overwrite it? [y/n] ')
                    overwrite_dir = overwrite_dir.lower().strip()
                    if overwrite_dir == "n":
                        print "Quitting... Restart and provice the \
                        proper directory to write to.".replace('    ', '')
                        sys.exit()
                    elif overwrite_dir == "y":
                        pass
                    else:
                        print "Quitting since you didn't provide a valid\
                            response..."
                        sys.exit()

    if args.f is None and args.single == "None" and args.localscan is False:
        print "[*] Error: You didn't specify a file! I need a file containing \
        URLs!\n".replace('    ', '')
        parser.print_help()
        sys.exit()

    if args.localscan:
        if not validate_cidr(args.localscan):
            print "[*] Error: Please provide valid CIDR notation!"
            print "[*] Example: 192.168.1.0/24"
            sys.exit()

    return current_directory, args


def title_screen():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')
    print "#############################################################################"
    print "#                               EyeWitness                                  #"
    print "#############################################################################\n"

    python_info = sys.version_info
    if python_info[0] is not 2 or python_info[1] < 7:
        print "[*] Error: Your version of python is not supported!"
        print "[*] Error: Please install Python 2.7.X"
        sys.exit()
    else:
        pass

    return


def user_agent_definition(cycle_value):
    # Create the dicts which hold different user agents.
    # Thanks to Chris John Riley for having an awesome tool which I could
    # get this info from.  His tool - UAtester.py -
    # http://blog.c22.cc/toolsscripts/ua-tester/
    # Additional user agent strings came from -
    # http://www.useragentstring.com/pages/useragentstring.php

    # "Normal" desktop user agents
    desktop_uagents = {
        "MSIE9.0": "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; \
            Trident/5.0)",
        "MSIE8.0": "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; \
            Trident/4.0)",
        "MSIE7.0": "Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)",
        "MSIE6.0": "Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; \
            .NET CLR 2.0.50727)",
        "Chrome32.0.1667.0": "Mozilla/5.0 (Windows NT 6.2; Win64; x64) \
        AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 \
        Safari/537.36",
        "Chrome31.0.1650.16": "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36\
         (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36",
        "Firefox25": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) \
        Gecko/20100101 Firefox/25.0",
        "Firefox24": "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) \
        Gecko/20100101 Firefox/24.0,",
        "Opera12.14": "Opera/9.80 (Windows NT 6.0) Presto/2.12.388 \
        Version/12.14",
        "Opera12": "Opera/12.0(Windows NT 5.1;U;en)Presto/22.9.168 \
        Version/12.00",
        "Safari5.1.7": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) \
        AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2",
        "Safari5.0": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) \
        AppleWebKit/533.18.1 (KHTML, like Gecko) Version/5.0 Safari/533.16"
    }

    # Miscellaneous user agents
    misc_uagents = {
        "wget1.9.1": "Wget/1.9.1",
        "curl7.9.8": "curl/7.9.8 (i686-pc-linux-gnu) libcurl 7.9.8 \
        (OpenSSL 0.9.6b) (ipv6 enabled)",
        "PyCurl7.23.1": "PycURL/7.23.1",
        "Pythonurllib3.1": "Python-urllib/3.1"
    }

    # Bot crawler user agents
    crawler_uagents = {
        "Baiduspider": "Baiduspider+(+http://www.baidu.com/search/spider.htm)",
        "Bingbot": "Mozilla/5.0 (compatible; \
            bingbot/2.0 +http://www.bing.com/bingbot.htm)",
        "Googlebot2.1": "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
        "MSNBot2.1": "msnbot/2.1",
        "YahooSlurp!": "Mozilla/5.0 (compatible; Yahoo! Slurp; \
            http://help.yahoo.com/help/us/ysearch/slurp)"
    }

    # Random mobile User agents
    mobile_uagents = {
        "BlackBerry": "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en) \
        AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile \
        Safari/534.11+",
        "Android": "Mozilla/5.0 (Linux; U; Android 2.3.5; en-us; HTC Vision \
            Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 \
            Mobile Safari/533.1",
        "IEMobile9.0": "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS\
            7.5; Trident/5.0; IEMobile/9.0)",
        "OperaMobile12.02": "Opera/12.02 (Android 4.1; Linux; Opera \
            Mobi/ADR-1111101157; U; en-US) Presto/2.9.201 Version/12.02",
        "iPadSafari6.0": "Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) \
        AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d \
        Safari/8536.25",
        "iPhoneSafari7.0.6": "Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_6 like \
            Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 \
            Mobile/11B651 Safari/9537.53"
    }

    # Web App Vuln Scanning user agents (give me more if you have any)
    scanner_uagents = {
        "w3af": "w3af.org",
        "skipfish": "Mozilla/5.0 SF/2.10b",
        "HTTrack": "Mozilla/4.5 (compatible; HTTrack 3.0x; Windows 98)",
        "nikto": "Mozilla/5.00 (Nikto/2.1.5) (Evasions:None) (Test:map_codes)"
    }

    # Combine all user agents into a single dictionary
    all_combined_uagents = dict(desktop_uagents.items() + misc_uagents.items()
                                + crawler_uagents.items() +
                                mobile_uagents.items())

    cycle_value = cycle_value.lower()

    if cycle_value == "browser":
        return desktop_uagents
    elif cycle_value == "misc":
        return misc_uagents
    elif cycle_value == "crawler":
        return crawler_uagents
    elif cycle_value == "mobile":
        return mobile_uagents
    elif cycle_value == "scanner":
        return scanner_uagents
    elif cycle_value == "all":
        return all_combined_uagents
    else:
        print "[*] Error: You did not provide the type of user agents\
         to cycle through!".replace('    ', '')
        print "[*] Error: Defaulting to desktop browser user agents."
        return desktop_uagents


def validate_cidr(val_cidr):
    # This came from (Mult-line link for pep8 compliance)
    # http://python-iptools.googlecode.com/svn-history/r4
    # /trunk/iptools/__init__.py
    cidr_re = re.compile(r'^(\d{1,3}\.){0,3}\d{1,3}/\d{1,2}$')
    if cidr_re.match(val_cidr):
        ip, mask = val_cidr.split('/')
        if validate_ip(ip):
            if int(mask) > 32:
                return False
        else:
            return False
        return True
    return False


def validate_ip(val_ip):
    # This came from (Mult-line link for pep8 compliance)
    # http://python-iptools.googlecode.com/svn-history/r4
    # /trunk/iptools/__init__.py
    ip_re = re.compile(r'^(\d{1,3}\.){0,3}\d{1,3}$')
    if ip_re.match(val_ip):
        quads = (int(q) for q in val_ip.split('.'))
        for q in quads:
            if q > 255:
                return False
        return True
    return False
