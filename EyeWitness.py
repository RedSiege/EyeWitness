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

    urls_in = parser.add_argument_group('Web Options')
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

    ua_options = parser.add_argument_group('User Agent Options')
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

    system_options = parser.add_argument_group('Local System Options')
    system_options.add_argument(
        "--open", action='store_true',
        help="Open all URLs in a browser")

    cred_check_options = parser.add_argument_group('Credential Check Options')
    cred_check_options.add_argument(
        "--skipcreds", action='store_true',
        help="Skip checking for default creds")

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
