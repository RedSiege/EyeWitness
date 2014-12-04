#!/usr/bin/env python

"""
 This script's inspiration was Tim Tomes's web screenshotting script PeepingTom
 I ran into issues where PeepingTom wasn't able to grab screenshots of certain
 websites, and the required libraries weren't all installed by default.  I
 wanted to find something that I felt was reliable, so Ghost is being used.  I
 also wanted to automate the install of dependencies, so this is the result of
 work.  A lot of the report output is based off of how Tim did PeepingTom
 because I thought he did a great job with it.  Finally, I also wanted it to
 be able to identify default creds.  That will be a growing process.
"""

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


def backup_request(page_code, outgoing_url, source_code_name, content_value,
                   iwitness_path, skip_cred_check, system_os):

    try:
        # Check if page is blank, due to no-cache.  If so,
        # make a backup request via urllib2
        if page_code.content == "None":
            try:
                response = urllib2.urlopen(outgoing_url)
                page_code.content = response.read()
                response.close()
            except urllib2.HTTPError:
                page_code.content = "Sorry, but couldn't get source code for\
                potentially a couple reasons.  If it was Basic Auth, a 50X,\
                or a 40X error, EyeWitness won't return source code.  Couldn't\
                get source from " + outgoing_url + ".".replace('    ', '')
            except urllib2.URLError:
                page_code.content = "Name resolution could not happen with " +\
                                    outgoing_url + ".".replace('    ', '')
            except:
                page_code.content = "Unknown error, server responded with an \
                unknown error code when connecting to " + outgoing_url
                + ".".replace('    ', '')

        # Generate the path of the report file
        if report_folder.startswith("/") or report_folder.startswith("C:\\"):
            report_file = join(report_folder, "source", source_code_name)
        else:
            report_file = join(iwitness_path, report_folder, "source",
                               source_code_name)
        # Write the obtained source to file
        with open(report_file, 'w') as source:
            source.write(page_code.content)

        if skip_cred_check:
            default_credentials_identified = None
        else:
            default_credentials_identified = default_creds(
                page_code.content, iwitness_path, system_os)

    except AttributeError:
        print "[*] ERROR: Web page possibly blank or SSL error!"
        content_value = 1
        default_credentials_identified = None

    except:
        print "[*] ERROR: Unknown error when accessing " + outgoing_url
        content_value = 1
        default_credentials_identified = None

    return content_value, default_credentials_identified


def casper_creator(ua_capture, timeout):
    # Instantiate Ghost Object
    if ua_capture == "None":
        ghost = screener.Ghost(wait_timeout=timeout, ignore_ssl_errors=True)
    else:
        ghost = screener.Ghost(wait_timeout=timeout,
                               user_agent=ua_capture, ignore_ssl_errors=True)
    return ghost


def checkHostPort(ip_to_check, port_to_check):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = s.connect_ex((ip_to_check, port_to_check))
    s.close()
    return result


def cli_parser():

    # Command line argument parser
    parser = argparse.ArgumentParser(
        add_help=False,
        description="EyeWitness is a tool used to capture screenshots\
        from a list of URLs")
    parser.add_argument(
        '-h', '-?', '--h', '-help', '--help', action="store_true",
        help=argparse.SUPPRESS)

    urls_in = parser.add_argument_group('URL Options')
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
                    overwrite_dir = raw_input('Directory Exists! Do you want to overwrite it? [y/n] ')
                    overwrite_dir = overwrite_dir.lower().strip()
                    if overwrite_dir == "n":
                        print "Quitting... Restart and provice the \
                        proper directory to write to.".replace('    ', '')
                        sys.exit()
                    elif overwrite_dir == "y":
                        pass
                    else:
                        print "Quitting since you didn't provide a valid response..."
                        sys.exit()
        elif args.d.startswith('C:\\'):
            args.d = args.d.rstrip("\\")
            if not os.access(os.path.dirname(args.d), os.W_OK):
                print "[*] Error: Please provide a valid folder name/Path\n"
                parser.print_help()
                sys.exit()
            else:
                if os.path.isdir(args.d):
                    overwrite_dir = raw_input('Directory Exists! Do you want to overwrite it? [y/n] ')
                    overwrite_dir = overwrite_dir.lower().strip()
                    if overwrite_dir == "n":
                        print "Quitting... Restart and provice the \
                        proper directory to write to.".replace('    ', '')
                        sys.exit()
                    elif overwrite_dir == "y":
                        pass
                    else:
                        print "Quitting since you didn't provide a valid response..."
                        sys.exit()
        else:
            file_path = join(current_directory, args.d)
            if not os.access(os.path.dirname(file_path), os.W_OK):
                print "[*] Error: Please provide a valid folder name/Path\n"
                parser.print_help()
                sys.exit()
            else:
                if os.path.isdir(file_path):
                    overwrite_dir = raw_input('Directory Exists! Do you want to overwrite it? [y/n] ')
                    overwrite_dir = overwrite_dir.lower().strip()
                    if overwrite_dir == "n":
                        print "Quitting... Restart and provice the \
                        proper directory to write to.".replace('    ', '')
                        sys.exit()
                    elif overwrite_dir == "y":
                        pass
                    else:
                        print "Quitting since you didn't provide a valid response..."
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

    # NOTE: You might want to change the below code to simply return the args
    #       object. This would reduce the amount of variables you explicitly
    #       defined - just an idea.

    # Return the file name which contains the URLs
    return current_directory, args


def default_creds(page_content, full_file_path, local_system_os):
    try:
        # Read in the file containing the web "signatures"
        file_path = join(os.path.normcase(full_file_path), 'signatures.txt')
        with open(file_path) as sig_file:
            signatures = sig_file.readlines()

        # Loop through and see if there are any matches from the source code
        # EyeWitness obtained
        for sig in signatures:
            # Find the signature(s), split them into their own list if needed
            # Assign default creds to its own variable
            sig_cred = sig.split('|')
            page_sig = sig_cred[0].split(";")
            cred_info = sig_cred[1]

            # Set our variable to 1 if the signature was identified.  If it is
            # identified, it will be added later on.  Find total number of
            # "signatures" needed to uniquely identify the web app
            sig_not_found = 0
            signature_range = len(page_sig)

            # This is used if there is more than one "part" of the
            # web page needed to make a signature Delimete the "signature"
            # by ";" before the "|", and then have the creds after the "|"
            for individual_signature in range(0, signature_range):
                if str(page_content).lower().find(page_sig[individual_signature].lower())\
                        is not -1:
                    pass
                else:
                    sig_not_found = 1

            # If the signature was found, break out of loops and
            # return the creds
            if sig_not_found == 0:
                return cred_info
                break
    except IOError:
        print "[*] WARNING: Credentials file not in the same directory as \
            EyeWitness!".replace('    ', '')
        print "[*] Skipping credential check"
        return


def file_names(url_given):
    url_given = url_given.strip()
    pic_name = url_given
    pic_name = pic_name.replace("://", ".")
    pic_name = pic_name.replace(":", ".")
    pic_name = pic_name.replace("/", "")
    src_name = pic_name + ".txt"
    pic_name = pic_name + ".png"
    return url_given, src_name, pic_name


def folder_out(dir_name, full_path, local_os):

    # Write out the CSS stylesheet
    css_page = """img {
    max-width: 100%;
    height: auto;
    }
    #screenshot{
    overflow: auto;
    max-width: 850px;
    max-height: 550px;
    }"
    """.replace('    ', '')

    # Get the date and time, and create output name
    current_date = time.strftime("%m/%d/%Y")
    current_time = time.strftime("%H:%M:%S")
    if dir_name is not "None":
        output_folder_name = dir_name
    else:
        output_folder_name = current_date.replace("/", "") + "_" +\
            current_time.replace(":", "")

    # Translate *nix and Windows paths accordingly, when we are on Windows the
    # slashes are replaced with backslashes, for *nix based systems the opposite
    # is performed.
    output_folder_name = os.path.normcase(output_folder_name)

    # NOTE: There may be other starting paths for Windows, the C: drive may be
    #       the most common but it wouldn't cover my external drive for instance.
    #
    #       Additionally, we could check for relative paths instead of just
    #       checking for the current directory or absolute paths. For reference
    #       use the python documentation, search for os.path, that should contain
    #       all the info you need to improve your project's code.
    #

    if output_folder_name.startswith('C:\\') or output_folder_name.startswith("/"):
        # Create a folder which stores all snapshots
        # If it starts with a "/" or with 'C:\', then assume it is a full path
        if not os.path.isdir(output_folder_name):
            os.makedirs(join(output_folder_name, "screens"))
            os.makedirs(join(output_folder_name, "source"))

    # If it doesn't start with a "/" or "C:\", then assume it should be in the
    # same directory as EyeWitness.
    else:
        # Create a folder which stores all snapshots
        # note- os.makedirs
        full_path = join(full_path, output_folder_name)
        if not os.path.isdir(full_path):
            os.makedirs(join(full_path, "screens"))
            os.makedirs(join(full_path, "source"))

    with open(join(output_folder_name, "style.css"), 'w') as css_file:
        css_file.write(css_page)

    return output_folder_name, current_date, current_time


def ghost_capture(incoming_ghost_object, screen_url, rep_fold, screen_name,
                  ewitness_dir_path, local_platform):
    # Try to get our screenshot and source code of the page
    # Write both out to disk if possible (if we can get one,
    # we can get the other)
    ghost_page, ghost_extra_resources = incoming_ghost_object.open(
        screen_url, auth=('none', 'none'), default_popup_response=True)

    if rep_fold.startswith("/") or rep_fold.startswith("C:\\"):
        capture_path = join(ewitness_dir_path, rep_fold, "screens",
                                    screen_name)
    else:
        capture_path = join(rep_fold, "screens", screen_name)

    incoming_ghost_object.capture_to(capture_path)

    return ghost_page, ghost_extra_resources


# NOTE: This could throw an exception (https://github.com/ChrisTruncer/EyeWitness/issues/35)
def html_encode(dangerous_data):
    encoded = cgi.escape(dangerous_data, quote=True)
    return encoded


def logistics(url_file, target_maker, no_dns):

    if target_maker is not None:
        print "Creating text file containing all web servers..."

    urls = []
    num_urls = 0
    use_amap = False
    try:
        # Setup variables
        # The nmap xml parsing code was sent to me and worked on by Jason Hill
        # (@jasonhillva)
        http_ports = [80, 8000, 8080, 8081, 8082]
        https_ports = [443, 8443]

        try:
            xml_tree = XMLParser.parse(url_file)
        except IOError:
            print "Error: EyeWitness needs a text or XML file to parse URLs!"
            sys.exit()
        root = xml_tree.getroot()

        if root.tag.lower() == "nmaprun":
            for item in root.iter('host'):
                check_ip_address = False
                # We only want hosts that are alive
                if item.find('status').get('state') == "up":
                    web_ip_address = None
                    # If there is no hostname then we'll set the IP as the
                    # target 'hostname'
                    if item.find('hostnames/hostname') is not None and no_dns is False:
                        target = item.find('hostnames/hostname').get('name')
                        web_ip_address = item.find('address').get('addr')
                    else:
                        target = item.find('address').get('addr')
                    # find open ports that match the http/https port list or
                    # have http/https as a service
                    for ports in item.iter('port'):
                        if ports.find('state').get('state') == 'open':
                            port = ports.attrib.get('portid')
                            try:
                                service = ports.find('service').get('name')\
                                    .lower()
                            except AttributeError:
                                # This hits when it finds an open port, but
                                # isn't able to Determine the name of the
                                # service running on it, so we'll just
                                # pass in this instance
                                pass
                            try:
                                tunnel = ports.find('service').get('tunnel')\
                                    .lower()
                            except AttributeError:
                                # This hits when it finds an open port, but
                                # isn't able to Determine the name of the
                                # service running on it, so we'll just pass
                                # in this instance
                                tunnel = "fakeportservicedoesntexist"
                            if int(port) in http_ports or 'http' in service:
                                protocol = 'http'
                                if int(port) in https_ports or 'https' in\
                                        service or ('http' in service and
                                                    'ssl' in tunnel):
                                    protocol = 'https'
                                urlBuild = '%s://%s:%s' % (protocol, target,
                                                           port)
                                if urlBuild not in urls:
                                    urls.append(urlBuild)
                                    num_urls += 1
                                else:
                                    check_ip_address = True

                        if check_ip_address:
                            if int(port) in http_ports or 'http' in service:
                                protocol = 'http'
                                if int(port) in https_ports or 'https' in\
                                        service or ('http' in service and
                                                    'ssl' in tunnel):
                                    protocol = 'https'
                                if web_ip_address is not None:
                                    urlBuild = '%s://%s:%s' % (
                                        protocol, web_ip_address, port)
                                else:
                                    urlBuild = '%s://%s:%s' % (
                                        protocol, target, port)
                                if urlBuild not in urls:
                                        urls.append(urlBuild)
                                        num_urls += 1

            if target_maker is not None:
                with open(target_maker, 'w') as target_file:
                    for item in urls:
                        target_file.write(item + '\n')
                print "Target file created (" + target_maker + ").\n"
                sys.exit()
            return urls, num_urls

        # Find root level if it is nessus output
        # This took a little bit to do, to learn to parse the nessus output.
        # There are a variety of scripts that do it, but also being able to
        # reference PeepingTom really helped.  Tim did a great job figuring
        # out how to parse this file format
        elif root.tag.lower() == "nessusclientdata_v2":
            # Find each host in the nessus report
            for host in root.iter("ReportHost"):
                name = host.get('name')
                for item in host.iter('ReportItem'):
                    service_name = item.get('svc_name')
                    plugin_name = item.get('pluginName')
                    # I had www, but later checked out PeepingTom and Tim had
                    # http? and https? for here.  Small tests of mine haven't
                    # shown those, but as he's smarter than I am, I'll add them
                    if (service_name in ['www', 'http?', 'https?'] and
                            plugin_name.lower()
                            .startswith('service detection')):
                        port_number = item.get('port')
                        # Convert essentially to a text string and then strip
                        # newlines
                        plugin_output = item.find('plugin_output').text.strip()
                        # Look to see if web page is over SSL or TLS.
                        # If so assume it is over https and prepend https,
                        # otherwise, http
                        http_output = re.search('TLS', plugin_output) or\
                            re.search('SSL', plugin_output)
                        if http_output:
                            url = "https://" + name + ":" + port_number
                        else:
                            url = "http://" + name + ":" + port_number
                        # Just do a quick check to make sure the url we are
                        # adding doesn't already exist
                        if url not in urls:
                            urls.append(url)
                            num_urls = num_urls + 1

            if target_maker is not None:
                with open(target_maker, 'w') as target_file:
                    for item in urls:
                        target_file.write(item + '\n')
                print "Target file created (" + target_maker + ").\n"
                sys.exit()
            return urls, num_urls

        else:
            print "ERROR: EyeWitness only accepts NMap XML files!"

    except XMLParser.ParseError:

        try:
            # Open the URL file and read all URLs, and reading again to catch
            # total number of websites
            with open(url_file) as f:
                all_urls = [url for url in f if url.strip()]

            for line in all_urls:
                if "www.thc.org/thc-amap" in line:
                    use_amap = True
                    break

            if use_amap is True:
                with open(url_file) as f:
                    for line in f:
                        if "matches http" in line:
                            prefix = "http://"
                        elif "matches ssl" in line and "by trigger http" in line:
                            prefix = "https://"
                        else:
                            prefix = None

                        if prefix is not None:
                            suffix = line.split("Protocol on ")[1].split("/tcp")[0]
                            urlBuild = '%s%s' % (prefix, suffix)
                            if urlBuild not in urls:
                                urls.append(urlBuild)
                                num_urls += 1

                # Code for parsing amap file and creating a target list within
                # a file.
                if target_maker is not None:
                    with open(target_maker, 'w') as target_file:
                        for item in urls:
                            target_file.write(item + '\n')
                print "Target file created (" + target_maker + ").\n"
                sys.exit()

            else:
                for line in all_urls:
                    urls.append(line)
                    num_urls += 1

            return urls, num_urls

        except IOError:
            print "ERROR: You didn't give me a valid file name! I need a valid\
            file containing URLs!"
            sys.exit()


def request_comparison(original_content, new_content, max_difference):
    # Function which compares the original baseline request with the new
    # request with the modified user agent
    orig_request_length = len(original_content)
    new_request_length = len(new_content)

    if new_request_length > orig_request_length:
        a, b = new_request_length, orig_request_length
        total_difference = a - b
        if total_difference > max_difference:
            return False, total_difference
        else:
            return True, "None"
    else:
        total_difference = orig_request_length - new_request_length
        if total_difference > max_difference:
            return False, total_difference
        else:
            return True, "None"


def scanner(cidr_range, tool_path, system_platform):
    # This function was developed by Rohan Vazarkar, and then I slightly
    # modified it to fit.  Thanks for writing this man.
    ports = [80, 443, 8080, 8443]

    # Create a list of all identified web servers
    live_webservers = []

    # Define the timeout limit
    timeout = 5

    scanner_output_path = join(tool_path, "scanneroutput.txt")

    # Write out the live machine to same path as EyeWitness
    try:
        ip_range = IPNetwork(cidr_range)
        socket.setdefaulttimeout(timeout)

        for ip_to_scan in ip_range:
            ip_to_scan = str(ip_to_scan)
            for port in ports:
                print "[*] Scanning " + ip_to_scan + " on port " + str(port)
                result = checkHostPort(ip_to_scan, port)
                if (result == 0):
                    # port is open, add to the list
                    if port is 443:
                        add_to_list = "https://" + ip_to_scan + ":" + str(port)
                    else:
                        add_to_list = "http://" + ip_to_scan + ":" + str(port)
                    print "[*] Potential live webserver at " + add_to_list
                    live_webservers.append(add_to_list)
                else:
                    if (result == 10035 or result == 10060):
                        # Host is unreachable
                        pass

    except KeyboardInterrupt:
        print "[*] Scan interrupted by you rage quitting!"
        print "[*] Writing out live web servers found so far..."

    # Write out the live machines which were found so far
    for live_computer in live_webservers:
        with open(scanner_output_path, 'a') as scanout:
            scanout.write("{0}{1}".format(live_computer, os.linesep))

    frmt_str = "List of live machines written to: {0}"
    print frmt_str.format(scanner_output_path)
    sys.exit()



def single_report_page(report_source, report_path, platform_os):
    # Close out the html and write it to disk
    report_source += """</table>
    </body>
    </html>
    """.replace('    ', '')

    if report_folder.startswith('/') or report_folder.startswith("C:\\"):
        report_file = join(report_folder, "report.html")
    else:
        report_file = join(report_path, report_folder, "report.html")

    with open(report_file, 'w') as fo:
        fo.write(report_source)
    return


def create_table_entry(htmldictionary, website_url, possible_creds, web_page,
                       content_empty, log_path, extra_notes, browser_out,
                       ua_out, source_code_table, screenshot_table,
                       length_difference, iwitness_path, local_system):
    html = u""
    html += """<tr>
    <td><div style=\"display: inline-block; width: 300px; word-wrap:\
     break-word\">
    <a href=\"{web_url_addy}\" target=\"_blank\">{web_url_addy}</a><br>
    """.format(web_url_addy=website_url).replace('    ', '')

    if (browser_out is not "None" and ua_out is not "None" and
       length_difference is not "Baseline" and
       length_difference is not "None"):
        html += """
        <br>This request was different from the baseline.<br>
        The browser type is: <b>{browser_report}</b><br><br>
        The user agent is: <b>{useragent_report}</b><br><br>
        Difference in length of the two webpage sources is\
        : <b>{page_source_hash}</b><br>
        """.format(browser_report=browser_out, useragent_report=ua_out,
                   page_source_hash=length_difference).replace('    ', '')

    if length_difference == "Baseline":
        html += """
        <br>This is the baseline request.<br>
        The browser type is: <b>{browser_report}</b><br><br>
        The user agent is: <b>{useragent_report}</b><br><br>
        <b>This is the baseline request.</b><br>
        """.format(browser_report=browser_out, useragent_report=ua_out)\
            .replace('    ', '')

    # Check if log file is empty, if so, good, otherwise, Check for SSL errors
    # If there is a SSL error, be sure to add a note about it in the table
    # Once done, delete the file
    if os.stat(log_path)[6] == 0:
        pass
    else:
        with open(log_path, 'r') as log_file:
            log_contents = log_file.readlines()
        for line in log_contents:
            if "SSL certificate error" in line:
                html += "<br><b>SSL Certificate error present on\
                 <a href=\"" + website_url + "\" target=\"_blank\">" +\
                    website_url + "</a></b><br>"
                break
        with open(log_path, 'w'):
            pass

    # If there are some default creds, escape them, and add them to the report
    if possible_creds is not None:
        html += "<br><b>Default credentials:</b> " +\
            html_encode(possible_creds) + "<br>"

    # Hacky regex. The first group takes care of anything inside the title
    # tag, while the second group gives us our actual title
    title_regex = re.compile(
        "<title(.*)>(.*)</title>", re.IGNORECASE+re.DOTALL
        )
    # Ghost saves unicode strings as some crazy format, so reopen the source
    # files and read title tags from there
    filepath = ""

    if report_folder.startswith('/'):
        filepath = join(report_folder, "source", source_code_table)
    else:
        filepath = join(iwitness_path, report_folder, "source", source_code_table)

    if (os.path.isfile(filepath)):
        with open(filepath) as source:
            pagesource = source.read()
            titletag = title_regex.search(pagesource)
            if titletag:
                pagetitle = titletag.groups()[1]
            else:
                pagetitle = "Unknown"
    else:
        pagetitle = "Unknown"

    # Implement a fallback in case of errors, but add the page
    # title to the table
    try:
        html += "\n<br><b> " + html_encode("Page Title") +\
            ":</b> " + html_encode(pagetitle) + "\n"
    except UnicodeDecodeError:
        html += "\n<br><b> " + html_encode("Page Title") +\
            ":</b> Unable to Display \n"

    # Loop through all server header responses, and add them to table
    # Handle exception if there is a SSL error and no headers were received.
    try:
        for key, value in web_page.headers.items():
            html += "<br><b> " + html_encode(key.decode('utf-8')) +\
                ":</b> " + html_encode(value) + "\n"

    except AttributeError:
        html += "\n<br><br>Potential blank page or SSL issue with\
            <a href=\"" + website_url + "\" target=\"_blank\">" +\
            website_url + "</a>."

    # If page is empty, or SSL errors, add it to report
    if content_empty == 1:
        html += """<br></td>
        <td><div style=\"display: inline-block; width: 850px;\">Page Blank,\
        Connection error, or SSL Issues</div></td>
        </tr>
        """.replace('    ', '')

    # If eyewitness could get the source code and take a screenshot,
    # add them to report. First line adds source code to header column of the
    # table, and then closes out that <td> Second line creates new <td> for
    # the screenshot column, adds screenshot in to report, and closes the <td>
    # Final line closes out the row
    else:
        html += """<br><br><a href=\"source/{page_source_name}\"\
        target=\"_blank\">Source Code</a></div></td>
        <td><div id=\"screenshot\" style=\"display: inline-block; width:\
        850px; height 400px; overflow: scroll;\"><a href=\"screens/\
        {screen_picture_name}\" target=\"_blank\"><img src=\"screens/\
        {screen_picture_name}\" height=\"400\"></a></div></td>
        </tr>
        """.format(page_source_name=source_code_table,
                   screen_picture_name=screenshot_table).replace('    ', '')

    if (website_url in htmldictionary):
        htmldictionary[website_url] = (
            htmldictionary[website_url][0], htmldictionary[website_url][1] +
            html)
    else:
        htmldictionary[website_url] = (pagetitle, html)

    return htmldictionary


def table_maker(web_table_index, website_url, possible_creds, web_page,
                content_empty, log_path, extra_notes, browser_out, ua_out,
                source_code_table, screenshot_table, length_difference,
                iwitness_path, system_os):

    # Continue adding to the table assuming that we were able
    # to capture the screenshot.  Only add elements if they exist
    # This block adds the URL to the row at the top
    web_table_index += """<tr>
    <td><div style=\"display: inline-block; width: 300px; word-wrap:\
     break-word\">
    <a href=\"{web_url_addy}\" target=\"_blank\">{web_url_addy}</a><br>
    """.format(web_url_addy=website_url).replace('    ', '')

    if (browser_out is not "None" and ua_out is not "None" and
       length_difference is not "Baseline" and
       length_difference is not "None"):
        web_table_index += """
        <br>This request was different from the baseline.<br>
        The browser type is: <b>{browser_report}</b><br><br>
        The user agent is: <b>{useragent_report}</b><br><br>
        Difference in length of the two webpage sources is\
        : <b>{page_source_hash}</b><br>
        """.format(browser_report=browser_out, useragent_report=ua_out,
                   page_source_hash=length_difference).replace('    ', '')

    if length_difference == "Baseline":
        web_table_index += """
        <br>This is the baseline request.<br>
        The browser type is: <b>{browser_report}</b><br><br>
        The user agent is: <b>{useragent_report}</b><br><br>
        <b>This is the baseline request.</b><br>
        """.format(browser_report=browser_out, useragent_report=ua_out)\
            .replace('    ', '')

    # Check if log file is empty, if so, good, otherwise, Check for SSL errors
    # If there is a SSL error, be sure to add a note about it in the table
    # Once done, delete the file
    if os.stat(log_path)[6] == 0:
        pass
    else:
        with open(log_path, 'r') as log_file:
            log_contents = log_file.readlines()
        for line in log_contents:
            if "SSL certificate error" in line:
                web_table_index += "<br><b>SSL Certificate error present on\
                 <a href=\"" + website_url + "\" target=\"_blank\">" +\
                    website_url + "</a></b><br>"
                break
        with open(log_path, 'w'):
            pass

    # If there are some default creds, escape them, and add them to the report
    if possible_creds is not None:
        web_table_index += "<br><b>Default credentials:</b> " +\
            html_encode(possible_creds) + "<br>"

    # Hacky regex. The first group takes care of anything inside the title
    # tag, while the second group gives us our actual title
    title_regex = re.compile(
        "<title(.*)>(.*)</title>", re.IGNORECASE+re.DOTALL
        )
    # Ghost saves unicode strings as some crazy format, so reopen the source
    # files and read title tags from there
    filepath = ""
    if report_folder.startswith('/') or report_folder.startswith("C:\\"):
        filepath = join(report_folder, "source", source_code_table)
    else:
        filepath = join(iwitness_path, report_folder, "source", source_code_table)

    if (os.path.isfile(filepath)):
        with open(filepath, 'r') as source:
            titletag = title_regex.search(source.read())
            if (not titletag is None):
                pagetitle = titletag.groups()[1]
            else:
                pagetitle = "Unknown"
    else:
        pagetitle = "Unknown"

    # Implement a fallback in case of errors, but add the page title
    # to the table
    try:
        web_table_index += "\n<br><b> " + html_encode("Page Title") +\
            ":</b> " + html_encode(pagetitle) + "\n"
    except UnicodeDecodeError:
        web_table_index += "\n<br><b> " + html_encode("Page Title") +\
            ":</b> Unable to Display \n"

    # Loop through all server header responses, and add them to table
    # Handle exception if there is a SSL error and no headers were received.
    try:
        for key, value in web_page.headers.items():
            web_table_index += "<br><b> " + html_encode(key.decode('utf-8')) +\
                ":</b> " + html_encode(value) + "\n"

    except AttributeError:
        web_table_index += "\n<br><br>Potential blank page or SSL issue with\
            <a href=\"" + website_url + "\" target=\"_blank\">" +\
            website_url + "</a>."

    except UnicodeDecodeError:
        web_table_index += "\n<br><br>Error properly escaping server headers for\
            <a href=\"" + website_url + "\" target=\"_blank\">" +\
            website_url + "</a>."

    # If page is empty, or SSL errors, add it to report
    if content_empty == 1:
        web_table_index += """<br></td>
        <td><div style=\"display: inline-block; width: 850px;\">Page Blank,\
        Connection error, or SSL Issues</div></td>
        </tr>
        """.replace('    ', '')

    # If eyewitness could get the source code and take a screenshot,
    # add them to report. First line adds source code to header column of the
    # table, and then closes out that <td> Second line creates new <td> for
    # the screenshot column, adds screenshot in to report, and closes the <td>
    # Final line closes out the row
    else:
        web_table_index += """<br><br><a href=\"source/{page_source_name}\"\
        target=\"_blank\">Source Code</a></div></td>
        <td><div id=\"screenshot\" style=\"display: inline-block; width:\
        850px; height 400px; overflow: scroll;\"><a href=\"screens/\
        {screen_picture_name}\" target=\"_blank\"><img src=\"screens/\
        {screen_picture_name}\" height=\"400\"></a></div></td>
        </tr>
        """.format(page_source_name=source_code_table,
                   screen_picture_name=screenshot_table).replace('    ', '')

    return web_table_index


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


def web_header(real_report_date, real_report_time):
    # Start our web page report
    web_index_head = """<html>
    <head>
    <link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>
    <title>EyeWitness Report</title>
    </head>
    <body>
    <center>Report Generated on {report_day} at {reporthtml_time}</center>
    <br><table border=\"1\">
    <tr>
    <th>Web Request Info</th>
    <th>Web Screenshot</th>
    </tr>""".format(report_day=real_report_date,
                    reporthtml_time=real_report_time).replace('    ', '')
    return web_index_head


if __name__ == "__main__":

    # Print the title header
    title_screen()

    # Detect the Operating System EyeWitness is running on
    operating_system = platform.system()

    # Parse command line options and return the filename containing URLS
    # and how long to wait for each website
    script_path, cli_parsed = cli_parser()

    # If the user wants to perform a scan for web servers locally,
    # then perform the scan, write out to a file, and exit
    if cli_parsed.localscan:
        scanner(cli_parsed.localscan, script_path, operating_system)

    if cli_parsed.createtargets:
        pass
    else:
        # Create the directory needed and support files
        report_folder, report_date, report_time = folder_out(cli_parsed.d,
                                                             script_path,
                                                             operating_system)

        # Change log path if full path is given for output directory
        if cli_parsed.d.startswith('/') or cli_parsed.d.startswith("C:\\"):
            # Location of the log file Ghost logs to (to catch SSL errors)
            log_file_path = join(script_path, report_folder, "logfile.log")
        else:
            # Location of the log file Ghost logs to (to catch SSL errors)
            log_file_path = join(report_folder, "logfile.log")

        # If the user wants to cycle through user agents, return the dictionary
        # of applicable user agents
        if cli_parsed.cycle == "None":
            ghost_object = casper_creator(cli_parsed.useragent, cli_parsed.t)
        else:
            ua_dict = user_agent_definition(cli_parsed.cycle)
            ghost_object = casper_creator(cli_parsed.useragent, cli_parsed.t)

        # Logging setup
        logging.basicConfig(filename=log_file_path, level=logging.WARNING)
        logger = logging.getLogger('ghost')

        # Define a couple default variables
        extra_info = "None"
        blank_value = "None"
        baseline_request = "Baseline"
        page_length = "None"

    if cli_parsed.single is not "None":

        # If URL doesn't start with http:// or https://, assume it is http://
        # and add it to URL
        if cli_parsed.single.startswith('http://') or cli_parsed.single\
                .startswith('https://'):
            pass
        else:
            cli_parsed.single = "http://" + cli_parsed.single

        # Used for monitoring for blank pages or SSL errors
        content_blank = 0

        web_index = web_header(report_date, report_time)
        print "Trying to screenshot " + cli_parsed.single

        # Create the filename to store each website's picture
        cli_parsed.single, source_name, picture_name = file_names(cli_parsed.single)

        # If a normal single request, then perform the request
        if cli_parsed.cycle == "None":
            try:
                page, extra_resources = ghost_capture(ghost_object, cli_parsed.single,
                                                      report_folder,
                                                      picture_name,
                                                      script_path,
                                                      operating_system)

                print dir(page)
                print "\n"
                print page.content
                print "\n"

                content_blank, single_default_credentials = backup_request(
                    page, cli_parsed.single, source_name, content_blank, script_path,
                    cli_parsed.skipcreds, operating_system)

                # Create the table info for the single URL (screenshot,
                # server headers, etc.)
                web_index = table_maker(web_index, cli_parsed.single,
                                        single_default_credentials,
                                        page, content_blank, log_file_path,
                                        blank_value, blank_value, blank_value,
                                        source_name, picture_name, page_length,
                                        script_path, operating_system)

            # Skip a url if Ctrl-C is hit
            except KeyboardInterrupt:
                print "[*] Skipping: " + cli_parsed.single
                web_index += """<tr>
                <td><a href=\"{single_given_url}\">{single_given_url}</a></td>
                <td>User Skipped this URL</td>
                </tr>
                """.format(single_given_url=cli_parsed.single).replace('    ', '')
            # Catch timeout warning
            except screener.TimeoutError:
                print "[*] Hit timeout limit when connecting to: " + cli_parsed.single
                web_index += """<tr>
                <td><a href=\"{single_timeout_url}\" target=\"_blank\">\
                {single_timeout_url}</a></td>
                <td>Hit timeout limit while attempting screenshot</td>
                </tr>
                """.format(single_timeout_url=cli_parsed.single)

        # If cycling through user agents, start that process here
        # Create a baseline requst, then loop through the dictionary of user
        # agents, and make requests w/those UAs
        # Then use comparison function.  If UA request content matches baseline
        # content, do nothing. If UA request content is different from baseline
        # add it to report
        else:
            # Setup variables to set file names properly
            original_source = source_name
            original_screenshot = picture_name

            # Create baseline file names
            source_name = source_name + "_baseline.txt"
            picture_name = picture_name + "_baseline.png"
            request_number = 0

            # Iterate through the user agents the user has selected to use,
            # and set ghost to use them. Then perform a comparison of the
            # baseline results to the new results.  If different, add to report
            for browser_key, user_agent_value in ua_dict.iteritems():
                # Create the counter to ensure our file names are unique
                source_name = original_source + "_" + browser_key + ".txt"
                picture_name = original_screenshot + "_" + browser_key + ".png"

                # Setting the new user agent
                ghost_object.page.setUserAgent(user_agent_value)

                # Making the request with the new user agent
                print "[*] Now making web request with: " + browser_key
                try:
                    if request_number == 0:
                        # Get baseline screenshot
                        baseline_page, baseline_extra_resources = \
                            ghost_capture(ghost_object, cli_parsed.single,
                                          report_folder, picture_name,
                                          script_path, operating_system)

                        # Hack for a bug in Ghost at the moment
                        baseline_page.content = "None"

                        baseline_content_blank, baseline_default_creds = \
                            backup_request(baseline_page, cli_parsed.single,
                                           source_name, content_blank,
                                           script_path, cli_parsed.skipcreds,
                                           operating_system)
                        extra_info = "This is the baseline request"

                        # Create the table info for the single URL
                        # (screenshot, server headers, etc.)
                        web_index = table_maker(web_index, cli_parsed.single,
                                                baseline_default_creds,
                                                baseline_page,
                                                baseline_content_blank,
                                                log_file_path, blank_value,
                                                browser_key, user_agent_value,
                                                source_name, picture_name,
                                                baseline_request, script_path,
                                                operating_system)

                        # Move beyond the baseline
                        request_number = 1

                    else:
                        new_ua_page, new_ua_extra_resources = \
                            ghost_capture(ghost_object, cli_parsed.single,
                                          report_folder, picture_name,
                                          script_path,
                                          operating_system)
                        try:
                            # Hack for a bug in Ghost at the moment
                            new_ua_page.content = "None"

                            new_ua_content_blank, new_ua_default_creds = \
                                backup_request(new_ua_page, cli_parsed.single,
                                               source_name, content_blank,
                                               script_path, cli_parsed.skipcreds,
                                               operating_system)

                            # Function which hashes the original request with
                            # the new request and checks to see if they are
                            # identical
                            same_or_different, total_length_difference = \
                                request_comparison(baseline_page.content,
                                                   new_ua_page.content,
                                                   cli_parsed.difference)

                            # If they are the same, then go on to the next user
                            # agent, if they are different, add it to the
                            # report
                            if same_or_different:
                                pass
                            else:
                                # Create the table info for the single URL
                                # (screenshot, server headers, etc.)
                                web_index = table_maker(
                                    web_index, cli_parsed.single,
                                    new_ua_default_creds, baseline_page,
                                    baseline_content_blank, log_file_path,
                                    blank_value, browser_key, user_agent_value,
                                    source_name, picture_name,
                                    total_length_difference, script_path,
                                    operating_system)
                        except AttributeError:
                            print "[*] Unable to request " + cli_parsed.single +\
                                " with " + browser_key
                            web_index += """<tr>
                            <td><a href=\"{single_given_url}\">\
                            {single_given_url}</a></td>
                            <td>Unable to request {single_given_url} with \
                            {browser_user}.</td>
                            </tr>
                            """.format(single_given_url=cli_parsed.single,
                                       browser_user=browser_key).\
                                replace('    ', '')
                        total_length_difference = "None"

                # Skip a url if Ctrl-C is hit
                except KeyboardInterrupt:
                    print "[*] Skipping: " + cli_parsed.single
                    web_index += """<tr>
                    <td><a href=\"{single_given_url}\">{single_given_url}\
                    </a></td>
                    <td>User Skipped this URL</td>
                    </tr>
                    """.format(single_given_url=cli_parsed.single).replace('    ', '')
                # Catch timeout warning
                except screener.TimeoutError:
                    print "[*] Hit timeout limit when connecting to: "\
                        + cli_parsed.single
                    web_index += """<tr>
                    <td><a href=\"{single_timeout_url}\" target=\"_blank\">\
                    {single_timeout_url}</a></td>
                    <td>Hit timeout limit while attempting screenshot</td>
                    </tr>
                    """.format(single_timeout_url=cli_parsed.single)

                # Add Random sleep based off of user provided jitter value
                #  if requested
                if cli_parsed.jitter is not "None":
                    sleep_value = random.randint(0, 30)
                    sleep_value = sleep_value * .01
                    sleep_value = 1 - sleep_value
                    sleep_value = sleep_value * int(cli_parsed.jitter)
                    print "[*] Sleeping for " + str(sleep_value) + " seconds.."
                    try:
                        time.sleep(sleep_value)
                    except KeyboardInterrupt:
                        print "[*] User cancelled sleep for this URL!"
        if cli_parsed.open:
            webbrowser.open_new_tab(cli_parsed.single)

        # Write out the report for the single URL
        single_report_page(web_index, script_path, operating_system)

    else:

        # Create the output directories, open the urlfile, and return all URLs
        url_list, number_urls = logistics(
            cli_parsed.f, cli_parsed.createtargets, cli_parsed.no_dns)

        # Check if user wants random URLs, if so, randomize URLs here
        if cli_parsed.jitter is not "None":
            random.shuffle(url_list)

        # Add the web "header" to our web page
        web_index = web_header(report_date, report_time)
        print "Trying to screenshot " + str(number_urls) + " websites...\n"

        # Create a URL counter to know when to go to a new page
        # Create a page counter to track pages
        page_counter = 0

        htmldictionary = {}

        url_counter = 0

        # Loop through all URLs and create a screenshot
        for url in url_list:

            url_counter += 1

            # Check for http or https protocol, if not present, assume http
            url = url.strip()
            if not url.startswith('http://') and not url.startswith('https://'):
                url = "http://" + url

            # Used for monitoring for blank pages or SSL errors
            content_blank = 0

            # Create the filename to store each website's picture
            url, source_name, picture_name = file_names(url)

            # This is the code which opens the specified URL and captures
            # it to a screenshot
            print "Attempting to capture: " + url + "  (" + str(url_counter) + "/" + str(number_urls) + ")"
            # If not trying to cycle through different user agents, make
            # the web requests as it was originall done
            if cli_parsed.cycle == "None":
                try:
                    # Ghost capturing web page
                    page, extra_resources = ghost_capture(
                        ghost_object, url, report_folder, picture_name,
                        script_path, operating_system)

                    # If EyeWitness receives a no-cache, it can't get the
                    # page source, therefore lets
                    # make a backup request get the source
                    content_blank, multi_line_default_creds = backup_request(
                        page, url, source_name, content_blank, script_path,
                        cli_parsed.skipcreds, operating_system)

                    htmldictionary = create_table_entry(
                        htmldictionary, url, multi_line_default_creds, page,
                        content_blank, log_file_path, blank_value, blank_value,
                        blank_value, source_name, picture_name, page_length,
                        script_path, operating_system)

                # Skip a url if Ctrl-C is hit
                except KeyboardInterrupt:
                    print "[*] Skipping: " + url
                    htmldictionary[url] = ('Unknown', """<tr>
                    <td><a href=\"{single_given_url}\">{single_given_url}\
                    </a></td>
                    <td>User Skipped this URL</td>
                    </tr>
                    """.format(single_given_url=url).replace('    ', ''))
                # Catch timeout warning
                except screener.TimeoutError:
                    print "[*] Hit timeout limit when connecting to: " + url
                    htmldictionary[url] = ('Unknown', """<tr>
                    <td><a href=\"{single_timeout_url}\" target=\"_blank\">\
                    {single_timeout_url}</a></td>
                    <td>Hit timeout limit while attempting screenshot</td>
                    </tr>
                    """.format(single_timeout_url=url))

            else:
                # Setup variables to set file names properly
                original_source = source_name
                original_screenshot = picture_name

                # Create baseline file names
                source_name = source_name + "_baseline.txt"
                picture_name = picture_name + "_baseline.png"
                request_number = 0

                # Iterate through the user agents the user has selected to use,
                # and set ghost to use them.  Then perform a comparison of the
                # baseline results to the new results.  If different,
                # add to report
                for browser_key, user_agent_value in ua_dict.iteritems():
                    # Create the counter to ensure our file names are unique
                    source_name = original_source + "_" + browser_key + ".txt"
                    picture_name = original_screenshot + "_" + browser_key +\
                        ".png"

                    # Setting the new user agent
                    ghost_object.page.setUserAgent(user_agent_value)

                    # Making the request with the new user agent
                    print "[*] Now making web request with: " + browser_key
                    try:
                        if request_number == 0:
                            # Get baseline screenshot
                            baseline_page, baseline_extra_resources = \
                                ghost_capture(ghost_object, url, report_folder,
                                              picture_name, script_path,
                                              operating_system)

                            # Hack for a bug in Ghost at the moment
                            baseline_page.content = "None"

                            baseline_content_blank, baseline_default_creds =\
                                backup_request(baseline_page, url, source_name,
                                               content_blank, script_path,
                                               cli_parsed.skipcreds, operating_system)

                            # Create the table info for the single URL
                            # (screenshot, server headers, etc.)
                            htmldictionary = create_table_entry(
                                htmldictionary, url, baseline_default_creds,
                                baseline_page, baseline_content_blank,
                                log_file_path, blank_value, browser_key,
                                user_agent_value, source_name, picture_name,
                                baseline_request, script_path,
                                operating_system)

                            # Move beyond the baseline
                            request_number = 1

                        else:
                            # Get page with new screenshot/
                            new_ua_page, new_ua_extra_resources =\
                                ghost_capture(
                                    ghost_object, url, report_folder,
                                    picture_name, script_path,
                                    operating_system)

                            try:
                                # Hack fix for potential bug in Ghost
                                new_ua_page.content = "None"

                                new_ua_content_blank, new_ua_default_creds =\
                                    backup_request(
                                        new_ua_page, url, source_name,
                                        content_blank, script_path, cli_parsed.skipcreds,
                                        operating_system)

                                # Function which hashes the original request
                                # with the new request and checks to see if
                                # they are identical
                                same_or_different, l_difference = \
                                    request_comparison(
                                        baseline_page.content,
                                        new_ua_page.content, cli_parsed.difference)

                                # If they are the same, then go on to the next
                                # user agent, if they are different, add it to
                                # the report
                                if same_or_different:
                                    pass
                                else:
                                    # Create the table info for the single URL
                                    # (screenshot, server headers, etc.)
                                    htmldictionary = create_table_entry(
                                        htmldictionary, url,
                                        new_ua_default_creds, baseline_page,
                                        baseline_content_blank, log_file_path,
                                        blank_value, browser_key,
                                        user_agent_value, source_name,
                                        picture_name, l_difference,
                                        script_path, operating_system)

                            except AttributeError:
                                print "[*] Unable to request " + url +\
                                    " with " + browser_key
                                if (url in htmldictionary):
                                    htmldictionary[url][1] = htmldictionary[url][1] + """<tr>
                                <td><a href=\"{single_given_url}\">\
                                {single_given_url}</a></td>
                                <td>Unable to request {single_given_url} with \
                                {browser_user}.</td>
                                </tr>
                                """.format(single_given_url=url,
                                           browser_user=browser_key)\
                                        .replace('    ', '')
                                else:
                                    htmldictionary[url] = ('Unknown', """<tr>
                                <td><a href=\"{single_given_url}\">\
                                {single_given_url}</a></td>
                                <td>Unable to request {single_given_url} with \
                                {browser_user}.</td>
                                </tr>
                                """.format(single_given_url=url,
                                           browser_user=browser_key)
                                        .replace('    ', ''))

                            l_difference = "None"

                    # Skip a url if Ctrl-C is hit
                    except KeyboardInterrupt:
                        print "[*] Skipping: " + url
                        htmldictionary[url] = ('Unknown', """<tr>
                        <td><a href=\"{single_given_url}\">{single_given_url}\
                        </a></td>
                        <td>User Skipped this URL</td>
                        </tr>
                        """.format(single_given_url=url).replace('    ', ''))
                    # Catch timeout warning
                    except screener.TimeoutError:
                        print "[*] Hit timeout limit when connecting to: "\
                            + url
                        htmldictionary[url] = ('Unknown', """<tr>
                        <td><a href=\"{single_timeout_url}\" target=\"_blank\"\
                        >{single_timeout_url}</a></td>
                        <td>Hit timeout limit while attempting screenshot</td>
                        </tr>
                        """.format(single_timeout_url=url))

                    # Add Random sleep based off of user provided jitter value
                    # if requested
                    if cli_parsed.jitter is not "None":
                        sleep_value = random.randint(0, 30)
                        sleep_value = sleep_value * .01
                        sleep_value = 1 - sleep_value
                        sleep_value = sleep_value * int(cli_parsed.jitter)
                        print "[*] Sleeping for " + str(sleep_value) +\
                            " seconds..."
                        try:
                            time.sleep(sleep_value)
                        except KeyboardInterrupt:
                            print "[*] User cancelled sleep for this URL!"

            # If user wants URL opened in a browser as it runs, do it
            if cli_parsed.open:
                webbrowser.open_new_tab(url)

            # Add Random sleep based off of user provided jitter value if
            # requested
            if cli_parsed.jitter is not "None" and cli_parsed.cycle is "None":
                sleep_value = random.randint(0, 30)
                sleep_value = sleep_value * .01
                sleep_value = 1 - sleep_value
                sleep_value = sleep_value * int(cli_parsed.jitter)
                print "[*] Sleeping for " + str(sleep_value) + " seconds..."
                try:
                    time.sleep(sleep_value)
                except KeyboardInterrupt:
                    print "[*] User cancelled sleep for this URL!"

        tosort = htmldictionary.items()
        groupedlist = []
        # Work our way from the back of the list and find similar elements.
        # Group them together.
        while (len(tosort) > 0):
            element = tosort.pop()
            groupedlist.append(element)
            for x in tosort:
                if (difflib.SequenceMatcher(
                        None, element[1][0], x[1][0]).ratio() > .7):
                    tosort.remove(x)
                    groupedlist.append(x)

        # Reverse the list to preserve original order (sort of)
        groupedlist.reverse()

        for i in range(1, len(groupedlist) + 1):
            element = groupedlist[i - 1]
            web_index += element[1][1]
            if (i % cli_parsed.results == 0 or i == len(groupedlist)):
                if page_counter == 0:
                    # Close out the html and write it to disk
                    web_index += "</table>\n"
                    with open(join(script_path, report_folder, "report.html"),
                              'w') as f1:
                        f1.write(web_index)

                    # Revert URL counter back to 0, increment the page count
                    # to 1 Clear web_index of all values by giving web_index
                    # the "header" of the new html page
                    page_counter = page_counter + 1
                    if i < len(groupedlist):
                        web_index = web_header(report_date, report_time)
                else:
                    # Write out to the next page
                    web_index += "</table>\n"
                    with open(join(script_path, report_folder, "report_page" + str(page_counter+1) +
                            ".html"), 'w') as page_out:
                        page_out.write(web_index)

                    page_counter += 1
                    # Reset the URL counter
                    if i != len(groupedlist):
                        page_counter = page_counter + 1
                        web_index = web_header(report_date, report_time)

        if page_counter == 1:
            single_report_page(web_index, script_path, operating_system)
        else:

            # Write out our extra page
            web_index += "</table>\n"
            with open(join(script_path, report_folder, "report_page" +
                      str(page_counter) + ".html"), 'w') as page_out:
                page_out.write(web_index)

            # Create the link structure at the bottom
            link_text = "\n<center><br>Links: <a href=\"report.html\">Page 1</a> "
            for page in range(2, page_counter + 1):
                link_text += "<a href=\"report_page" + str(page) + ".html\">\
                Page " + str(page) + "</a> ".replace('    ', '')
            top_links = link_text
            link_text += "</center>\n</body>\n"
            link_text += "</html>"

            # Write out link structure to bottom of report
            # and add it to the top as well
            with open(join(script_path, report_folder, "report.html"), 'a')\
                    as report_append:
                report_append.write(link_text)

            with open(join(script_path, report_folder, "report.html"), 'r')\
                    as link_add:
                content = link_add.readlines()

            content.insert(6, "<center>" + top_links + "</center>\n")
            content = "".join(content)

            with open(join(script_path, report_folder, "report.html"), 'w')\
                    as final_report_page:
                final_report_page.write(content)

            # Write out link structure to bottom of extra pages
            # Also add links to the top of extra pages
            for page_footer in range(2, page_counter + 1):
                with open(join(script_path, report_folder, "report_page" +
                          str(page_footer) + ".html"), 'a') as page_append:
                    page_append.write(link_text)

            for page_footer in range(2, page_counter + 1):
                with open(join(script_path, report_folder, "report_page" +
                          str(page_footer) + ".html"), 'r') as link_add:
                    content = link_add.readlines()

                content.insert(6, "<center>" + top_links + "</center>\n")
                content = "".join(content)

                with open(join(script_path, report_folder, "report_page" +
                          str(page_footer) + ".html"), 'w') as final_reports_page:
                    final_reports_page.write(content)

    # Kill xvfb session if started
    if hasattr(ghost_object, 'xvfb'):
        ghost_object.xvfb.terminate()

    if operating_system == "Windows":
        # Stupid windows won't let me delete the log file
        pass
    else:
        os.system('rm ' + log_file_path)
    print "\n[*] Done! Check out the report in the " + report_folder +\
        " folder!"
