# -*- coding: utf-8 -*- 
import hashlib
import os
import platform
import random
import shutil
import sys
import time
import xml.sax
import glob
import socket
from netaddr import IPAddress
from netaddr.core import AddrFormatError
from urllib.parse import urlparse


class XML_Parser(xml.sax.ContentHandler):

    def __init__(self, file_out, class_cli_obj):
        self.system_name = None
        self.port_number = None
        self.protocol = None
        self.masscan = False
        self.nmap = False
        self.nessus = False
        self.url_list = []
        self.port_open = False
        self.http_ports = ['80', '8080']
        self.https_ports = ['443', '8443']
        self.num_urls = 0
        self.get_fqdn = False
        self.get_ip = False
        self.service_detection = False
        self.out_file = file_out
        self.analyze_plugin_output = False
        self.read_plugin_output = False
        self.plugin_output = ""

        self.http_ports = self.http_ports + class_cli_obj.add_http_ports
        self.https_ports = self.https_ports + class_cli_obj.add_https_ports
        self.no_dns = class_cli_obj.no_dns
        self.only_ports = class_cli_obj.only_ports

    def startElement(self, tag, attributes):
        # Determine the Scanner being used
        if tag == "nmaprun" and attributes['scanner'] == "masscan":
            self.masscan = True
        elif tag == "nmaprun" and attributes['scanner'] == "nmap":
            self.nmap = True
        elif tag == "NessusClientData_v2":
            self.nessus = True

        if self.masscan or self.nmap:
            if tag == "address":
                if attributes['addrtype'].lower() == "mac":
                    pass
                else:
                    self.system_name = attributes['addr']
            elif tag == "hostname":
                if not self.no_dns:
                    if attributes['type'].lower() == "user":
                        self.system_name = attributes['name']
            elif tag == "port":
                self.port_number = attributes['portid']
            elif tag == "service":
                if "ssl" in attributes['name'] or self.port_number in self.https_ports:
                    self.protocol = "https"
                elif "tunnel" in attributes:
                    if "ssl" in attributes['tunnel'] and not "smtp" in attributes['name'] and not "imap" in attributes['name'] and not "pop3" in attributes['name']:
                        self.protocol = "https"
                elif "http" == attributes['name'] or self.port_number in self.http_ports:
                    self.protocol = "http"
                elif "http-alt" == attributes['name']:
                    self.protocol = "http"
            elif tag == "state":
                if attributes['state'] == "open":
                    self.port_open = True

        elif self.nessus:
            if tag == "ReportHost":
                if 'name' in attributes:
                    self.system_name = attributes['name']

            elif tag == "ReportItem":
                if "port" in attributes and "svc_name" in attributes and "pluginName" in attributes:
                    self.port_number = attributes['port']

                    service_name = attributes['svc_name']
                    # pluginID 22964 is the Service Detection Plugin
                    # But it uses www for the svc_name for both, http and https.
                    # To differentiate we have to look at the plugin_output...
                    if service_name == 'https?' or self.port_number in self.https_ports:
                        self.protocol = "https"
                    elif attributes['pluginID'] == "22964" and service_name == "www":
                        self.protocol = "http"
                        self.analyze_plugin_output = True
                    elif service_name == "www" or service_name == "http?":
                        self.protocol = "http"

                    self.service_detection = True

            elif tag == "plugin_output" and self.analyze_plugin_output:
                self.read_plugin_output = True

        return

    def endElement(self, tag):
        if self.masscan or self.nmap:
            if tag == "service":
                if not self.only_ports:
                    if (self.system_name is not None) and (self.port_number is not None) and self.port_open:
                        if self.protocol == "http" or self.protocol == "https":
                            built_url = self.protocol + "://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1
                        elif self.protocol is None and self.port_number in self.http_ports:
                            built_url = "http://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1
                        elif self.protocol is None and self.port_number in self.https_ports:
                            built_url = "https://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1

                else:
                    if (self.system_name is not None) and (self.port_number is not None) and self.port_open and int(self.port_number.encode('utf-8')) in self.only_ports:
                        if self.protocol == "http" or self.protocol == "https":
                            built_url = self.protocol + "://" + self.system_name
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1
                        elif self.protocol is None and self.port_number in self.http_ports:
                            built_url = "http://" + self.system_name
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1
                        elif self.protocol is None and self.port_number in self.https_ports:
                            built_url = "https://" + self.system_name
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1

                self.port_number = None
                self.protocol = None
                self.port_open = False

            elif tag == "port":
                if not self.only_ports and (self.protocol == None):
                    if (self.port_number is not None) and self.port_open and (self.system_name is not None):
                        if self.port_number in self.http_ports:
                            self.protocol = 'http'
                            built_url = self.protocol + "://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1
                        elif self.port_number in self.https_ports:
                            self.protocol = 'https'
                            built_url = self.protocol + "://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1
                else:
                    if (self.port_number is not None) and self.port_open and (self.system_name is not None) and int(self.port_number.encode('utf-8')) in self.only_ports:
                        if self.port_number in self.http_ports:
                            self.protocol = 'http'
                            built_url = self.protocol + "://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1
                        elif self.port_number in self.https_ports:
                            self.protocol = 'https'
                            built_url = self.protocol + "://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)
                                self.num_urls += 1
                self.port_number = None
                self.protocol = None
                self.port_open = False

            elif tag == "host":
                self.system_name = None

            elif tag == "nmaprun":
                if len(self.url_list) > 0:
                    with open(self.out_file, 'a') as temp_web:
                        for url in self.url_list:
                            temp_web.write(url + '\n')

        elif self.nessus:
            if tag == "plugin_output" and self.read_plugin_output:

                # Use plugin_output to differentiate between http and https.
                # "A web server is running on the remote host." indicates a http server
                # "A web server is running on this port through ..." indicates a https server
                if "A web server is running on this port through" in self.plugin_output:
                    self.protocol = "https"

                self.plugin_output = ""
                self.read_plugin_output = False
                self.analyze_plugin_output = False
            if tag == "ReportItem":
                if not self.only_ports:
                    if (self.system_name is not None) and (self.protocol is not None) and self.service_detection:
                        if self.protocol == "http" or self.protocol == "https":
                            built_url = self.protocol + "://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)

                else:
                    if (self.system_name is not None) and (self.protocol is not None) and self.service_detection and int(self.port_number.encode('utf-8')) in self.only_ports:
                        if self.protocol == "http" or self.protocol == "https":
                            built_url = self.protocol + "://" + self.system_name + ":" + self.port_number
                            if built_url not in self.url_list:
                                self.url_list.append(built_url)

                self.port_number = None
                self.protocol = None
                self.port_open = False
                self.service_detection = False

            elif tag == "ReportHost":
                self.system_name = None

            elif tag == "NessusClientData_v2":
                if len(self.url_list) > 0:
                    with open(self.out_file, 'a') as temp_web:
                        for url in self.url_list:
                            temp_web.write(url + '\n')

    def characters(self, content):
        if self.read_plugin_output:
            self.plugin_output += content

def duplicate_check(cli_object):
    # This is used for checking for duplicate images
    # if it finds any, it removes them and uses a single image
    # reducing file size for output
    # dict = {sha1hash: [pic1, pic2]}
    hash_files = {}
    report_files = []

    for name in glob.glob(cli_object.d + '/screens/*.png'):
        with open(name, 'rb') as screenshot:
            pic_data = screenshot.read()
        md5_hash = hashlib.md5(pic_data).hexdigest()
        if md5_hash in hash_files:
            hash_files[md5_hash].append(name.split('/')[-2] + '/' + name.split('/')[-1])
        else:
            hash_files[md5_hash] = [name.split('/')[-2] + '/' + name.split('/')[-1]]

    for html_file in glob.glob(cli_object.d + '/*.html'):
        report_files.append(html_file)

    for hex_value, file_dict in hash_files.items():
        total_files = len(file_dict)
        if total_files > 1:
            original_pic_name = file_dict[0]
            for num in range(1, total_files):
                next_filename = file_dict[num]
                for report_page in report_files:
                    with open(report_page, 'r') as report:
                        page_text = report.read()
                    page_text = page_text.replace(next_filename, original_pic_name)
                    with open(report_page, 'w') as report_out:
                        report_out.write(page_text)
                os.remove(cli_object.d + '/' + next_filename)
                with open(cli_object.d + "/Requests.csv", 'r') as csv_port_file:
                    csv_lines = csv_port_file.read()
                    if next_filename in csv_lines:
                        csv_lines = csv_lines.replace(next_filename, original_pic_name)
                with open(cli_object.d + "/Requests.csv", 'w') as csv_port_writer:
                    csv_port_writer.write(csv_lines)
    return


def resolve_host(system):
    parsed = urlparse(system)
    system = parsed.path if parsed.netloc == '' else parsed.netloc
    try:
        toresolve = IPAddress(system)
        resolved = socket.gethostbyaddr(str(toresolve))[0]
        return resolved
    except AddrFormatError:
        pass
    except socket.herror:
        return 'Unknown'

    try:
        resolved = socket.gethostbyname(system)
        return resolved
    except socket.gaierror:
        return 'Unknown'


def find_file_name():
    file_not_found = True
    file_name = "parsed_xml"
    counter = 0
    first_time = True
    while file_not_found:
        if first_time:
            if not os.path.isfile(file_name + ".txt"):
                file_not_found = False
            else:
                counter += 1
                first_time = False
        else:
            if not os.path.isfile(file_name + str(counter) + ".txt"):
                file_not_found = False
            else:
                counter += 1
    if first_time:
        return file_name + ".txt"
    else:
        return file_name + str(counter) + ".txt"


def textfile_parser(file_to_parse, cli_obj):
    urls = []
    openports = {}
    complete_urls = []

    try:
        # Open the URL file and read all URLs, and reading again to catch
        # total number of websites
        with open(file_to_parse) as f:
            all_urls = [url for url in f if url.strip()]

        # else:
        for line in all_urls:
            line = line.strip()

            # Account for odd case schemes and fix to lowercase for matching
            scheme = urlparse(line)[0]
            if scheme == 'http':
                line = scheme + '://' + line[7:]
            elif scheme == 'https':
                line = scheme + '://' + line[8:]

            if not cli_obj.only_ports:
                if scheme == 'http' or scheme == 'https':
                    urls.append(line)
                else:
                    if cli_obj.web:
                        if cli_obj.prepend_https:
                            urls.append("http://" + line)
                            urls.append("https://" + line)
                        else:
                            urls.append(line)
            else:
                if scheme == 'http' or scheme == 'https':
                    for port in cli_obj.only_ports:
                        urls.append(line + ':' + str(port))
                else:

                    if cli_obj.web:
                        if cli_obj.prepend_https:
                            for port in cli_obj.only_ports:
                                urls.append("http://" + line + ':' + str(port))
                                urls.append("https://" + line + ':' + str(port))
                        else:
                            for port in cli_obj.only_ports:
                                urls.append(line + ':' + str(port))
        
        # Look at URLs and make CSV output of open ports unless already parsed from XML output
        # This parses the text file
        for url_again in all_urls:
            url_again = url_again.strip()
            complete_urls.append(url_again)
            if url_again.count(":") == 2:
                try:
                    port_number = int(url_again.split(":")[2].split("/")[0])
                except ValueError:
                    print("ERROR: You potentially provided an mal-formed URL!")
                    print("ERROR: URL is - " + url_again)
                    sys.exit()
                hostname_again = url_again.split(":")[0] + ":" + url_again.split(":")[1] + ":" + url_again.split(":")[2]
                if port_number in openports:
                    openports[port_number] += "," + hostname_again
                else:
                    openports[port_number] = hostname_again
            else:
                if "https://" in url_again:
                    if 443 in openports:
                        openports[443] += "," + url_again
                    else:
                        openports[443] = url_again
                else:
                    if 80 in openports:
                        openports[80] += "," + url_again
                    else:
                        openports[80] = url_again

        # Start prepping to write out the CSV
        csv_data = "URL"
        ordered_ports = sorted(openports.keys())
        for opn_prt in ordered_ports:
            csv_data += "," + str(opn_prt)

        # Create the CSV data row by row
        for ind_system in complete_urls:
            # add new line and add hostname
            csv_data += '\n'
            csv_data += ind_system + ","
            for test_for_port in ordered_ports:
                if ind_system in openports[test_for_port]:
                    csv_data += "X,"
                else:
                    csv_data += ","

        # Write out CSV
        with open(cli_obj.d + "/open_ports.csv", 'w') as csv_file_out:
            csv_file_out.write(csv_data)

        return urls

    except IOError:
        if cli_obj.x is not None:
            print("ERROR: The XML file you provided does not have any active web servers!")
        else:
            print("ERROR: You didn't give me a valid file name! I need a valid file containing URLs!")
        sys.exit()


def target_creator(command_line_object):
    """Parses input files to create target lists

    Args:
        command_line_object (ArgumentParser): Command Line Arguments

    Returns:
        List: URLs detected for http
    """

    if command_line_object.x is not None:

        # Get a file name for the parsed results
        parsed_file_name = find_file_name()

        # Create parser
        parser = xml.sax.make_parser()

        # Turn off namespaces
        parser.setFeature(xml.sax.handler.feature_namespaces, 0)
        # Override the parser
        Handler = XML_Parser(parsed_file_name, command_line_object)
        parser.setContentHandler(Handler)
        # Parse the XML

        # Check if path exists
        if os.path.exists(command_line_object.x):
            # Check if it is a file
            if os.path.isfile(command_line_object.x):
                parser.parse(command_line_object.x)
            else:
                print("ERROR: The path you provided does not point to a file!")
                sys.exit()
        else:
            print("ERROR: The path you provided does not exist!")
            sys.exit()

        out_urls = textfile_parser(
            parsed_file_name, command_line_object)
        return out_urls

    elif command_line_object.f is not None:

        file_urls = textfile_parser(
            command_line_object.f, command_line_object)
        return file_urls


def get_ua_values(cycle_value):
    """Create the dicts which hold different user agents.
    Thanks to Chris John Riley for having an awesome tool which I
    could get this info from. His tool - UAtester.py -
    http://blog.c22.cc/toolsscripts/ua-tester/
    Additional user agent strings came from -
    http://www.useragentstring.com/pages/useragentstring.php

    Args:
        cycle_value (String): Which UA dict to retrieve

    Returns:
        Dict: Dictionary of user agents
    """

    # "Normal" desktop user agents
    desktop_uagents = {
        "MSIE9.0": ("Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1;"
                    " Trident/5.0)"),
        "MSIE8.0": ("Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64;"
                    "Trident/4.0)"),
        "MSIE7.0": "Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)",
        "MSIE6.0": ("Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1;"
                    " .NET CLR 2.0.50727)"),
        "Chrome32.0.1667.0": ("Mozilla/5.0 (Windows NT 6.2; Win64; x64)"
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0"
                              "Safari/537.36"),
        "Chrome31.0.1650.16": ("Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36"
                               " (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36"),
        "Firefox25": ("Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0)"
                      " Gecko/20100101 Firefox/25.0"),
        "Firefox24": ("Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0)"
                      " Gecko/20100101 Firefox/24.0,"),
        "Opera12.14": ("Opera/9.80 (Windows NT 6.0) Presto/2.12.388"
                       " Version/12.14"),
        "Opera12": ("Opera/12.0(Windows NT 5.1;U;en)Presto/22.9.168"
                    " Version/12.00"),
        "Safari5.1.7": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8)"
                        " AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2"),
        "Safari5.0": ("Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US)"
                      " AppleWebKit/533.18.1 (KHTML, like Gecko) Version/5.0 Safari/533.16")
    }

    # Miscellaneous user agents
    misc_uagents = {
        "wget1.9.1": "Wget/1.9.1",
        "curl7.9.8": ("curl/7.9.8 (i686-pc-linux-gnu) libcurl 7.9.8"
                      " (OpenSSL 0.9.6b) (ipv6 enabled)"),
        "PyCurl7.23.1": "PycURL/7.23.1",
        "Pythonurllib3.1": "Python-urllib/3.1"
    }

    # Bot crawler user agents
    crawler_uagents = {
        "Baiduspider": "Baiduspider+(+http://www.baidu.com/search/spider.htm)",
        "Bingbot": ("Mozilla/5.0 (compatible;"
                    " bingbot/2.0 +http://www.bing.com/bingbot.htm)"),
        "Googlebot2.1": "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
        "MSNBot2.1": "msnbot/2.1",
        "YahooSlurp!": ("Mozilla/5.0 (compatible; Yahoo! Slurp;"
                        " http://help.yahoo.com/help/us/ysearch/slurp)")
    }

    # Random mobile User agents
    mobile_uagents = {
        "BlackBerry": ("Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en)"
                       " AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile"
                       " Safari/534.11+"),
        "Android": ("Mozilla/5.0 (Linux; U; Android 2.3.5; en-us; HTC Vision"
                    " Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0"
                    " Mobile Safari/533.1"),
        "IEMobile9.0": ("Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS"
                        " 7.5; Trident/5.0; IEMobile/9.0)"),
        "OperaMobile12.02": ("Opera/12.02 (Android 4.1; Linux; Opera"
                             " Mobi/ADR-1111101157; U; en-US) Presto/2.9.201 Version/12.02"),
        "iPadSafari6.0": ("Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X)"
                          " AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d"
                          " Safari/8536.25"),
        "iPhoneSafari7.0.6": ("Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_6 like"
                              " Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0"
                              " Mobile/11B651 Safari/9537.53")
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
        print("[*] Error: You did not provide the type of user agents\
         to cycle through!".replace('    ', ''))
        print("[*] Error: Defaulting to desktop browser user agents.")
        return desktop_uagents


def title_screen():
    """Prints the title screen for EyeWitness
    """
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')
    print("#" * 80)
    print("#" + " " * 34 + "EyeWitness" + " " * 34 + "#")
    print("#" * 80)
    print("#" + " " * 11 + "FortyNorth Security - https://www.fortynorthsecurity.com" + " " * 11 + "#")
    print("#" * 80 + "\n")

    python_info = sys.version_info
    if python_info[0] != 3:
        print("[*] Error: Your version of python is not supported!")
        print("[*] Error: Please install Python 3.X.X")
        sys.exit()
    else:
        pass
    return


def strip_nonalphanum(string):
    """Strips any non-alphanumeric characters in the ascii range from a string

    Args:
        string (String): String to strip

    Returns:
        String: String stripped of all non-alphanumeric characters
    """
    todel = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
    return string.translate(None, todel)


def do_jitter(cli_parsed):
    """Jitters between URLs to add delay/randomness

    Args:
        cli_parsed (ArgumentParser): CLI Object

    Returns:
        TYPE: Description
    """
    if cli_parsed.jitter != 0:
        sleep_value = random.randint(0, 30)
        sleep_value = sleep_value * .01
        sleep_value = 1 - sleep_value
        sleep_value = sleep_value * cli_parsed.jitter
        print("[*] Sleeping for " + str(sleep_value) + " seconds..")
        try:
            time.sleep(sleep_value)
        except KeyboardInterrupt:
            pass

def do_delay(cli_parsed):
    """Delay between the opening of the navigator and taking the screenshot

    Args:
        cli_parsed (ArgumentParser): CLI Object

    Returns:
        TYPE: Description
    """
    if cli_parsed.delay != 0:
        sleep_value = cli_parsed.delay
        print("[*] Sleeping for " + str(sleep_value) + " seconds before taking the screenshot")
        try:
            time.sleep(sleep_value)
        except KeyboardInterrupt:
            pass

def create_folders_css(cli_parsed):
    """Writes out the CSS file and generates folders for output

    Args:
        cli_parsed (ArgumentParser): CLI Object
    """
    css_page = """img {
    max-width:100%;
    height:auto;
    }
    #screenshot{
    max-width: 850px;
    max-height: 550px;
    display: inline-block;
    width: 850px;
    overflow:scroll;
    }
    .hide{
    display:none;
    }
    .uabold{
    font-weight:bold;
    cursor:pointer;
    background-color:green;
    }
    .uared{
    font-weight:bold;
    cursor:pointer;
    background-color:red;
    }
    table.toc_table{
    border-collapse: collapse;
    border: 1px solid black;
    }
    table.toc_table td{
    border: 1px solid black;
    padding: 3px 8px 3px 8px;
    }
    table.toc_table th{
    border: 1px solid black;
    text-align: left;
    padding: 3px 8px 3px 8px;
    }
    """

    # Create output directories
    if os.path.exists(cli_parsed.d):
        shutil.rmtree(cli_parsed.d)
    os.makedirs(cli_parsed.d)
    os.makedirs(os.path.join(cli_parsed.d, 'screens'))
    os.makedirs(os.path.join(cli_parsed.d, 'source'))
    local_path = os.path.dirname(os.path.realpath(__file__))
    # Move our jquery file to the local directory
    shutil.copy2(
        os.path.join(local_path, '..', 'bin', 'jquery-1.11.3.min.js'), cli_parsed.d)

    # Write our stylesheet to disk
    with open(os.path.join(cli_parsed.d, 'style.css'), 'w') as f:
        f.write(css_page)


def default_creds_category(http_object):
    """Adds default credentials or categories to a http_object if either exist

    Args:
        http_object (HTTPTableObject): Object representing a URL

    Returns:
        HTTPTableObject: Object with creds/category added
    """
    http_object.default_creds = None
    http_object.category = None
    try:
        sigpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', 'signatures.txt')
        catpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', 'categories.txt')
        with open(sigpath) as sig_file:
            signatures = sig_file.readlines()

        with open(catpath) as cat_file:
            categories = cat_file.readlines()

        # Loop through and see if there are any matches from the source code
        # EyeWitness obtained
        if http_object.source_code is not None:
            for sig in signatures:
                # Find the signature(s), split them into their own list if needed
                # Assign default creds to its own variable
                sig_cred = sig.split('|')
                page_sig = sig_cred[0].split(";")
                cred_info = sig_cred[1].strip()

                # Set our variable to 1 if the signature was not identified.  If it is
                # identified, it will be added later on.  Find total number of
                # "signatures" needed to uniquely identify the web app
                # signature_range = len(page_sig)

                # This is used if there is more than one "part" of the
                # web page needed to make a signature Delimete the "signature"
                # by ";" before the "|", and then have the creds after the "|"
                if all([x.lower() in http_object.source_code.decode().lower() for x in page_sig]):
                    if http_object.default_creds is None:
                        http_object.default_creds = cred_info
                    else:
                        http_object.default_creds += '\n' + cred_info

            for cat in categories:
                # Find the signature(s), split them into their own list if needed
                # Assign default creds to its own variable
                cat_split = cat.split('|')
                cat_sig = cat_split[0].split(";")
                cat_name = cat_split[1]

                # Set our variable to 1 if the signature was not identified.  If it is
                # identified, it will be added later on.  Find total number of
                # "signatures" needed to uniquely identify the web app
                # signature_range = len(page_sig)

                # This is used if there is more than one "part" of the
                # web page needed to make a signature Delimete the "signature"
                # by ";" before the "|", and then have the creds after the "|"
                if all([x.lower() in http_object.source_code.decode().lower() for x in cat_sig]):
                    http_object.category = cat_name.strip()
                    break

        if http_object.page_title is not None:
            if (type(http_object.page_title)) == bytes:
                if '403 Forbidden'.encode() in http_object.page_title or '401 Unauthorized'.encode() in http_object.page_title:
                    http_object.category = 'unauth'
                if ('Index of /'.encode() in http_object.page_title or
                        'Directory Listing For /'.encode() in http_object.page_title or
                        'Directory of /'.encode() in http_object.page_title):
                    http_object.category = 'dirlist'
                if '404 Not Found'.encode() in http_object.page_title:
                    http_object.category = 'notfound'
            else:
                if '403 Forbidden' in http_object.page_title or '401 Unauthorized' in http_object.page_title:
                    http_object.category = 'unauth'
                if ('Index of /' in http_object.page_title or
                        'Directory Listing For /' in http_object.page_title or
                        'Directory of /' in http_object.page_title):
                    http_object.category = 'dirlist'
                if '404 Not Found' in http_object.page_title:
                    http_object.category = 'notfound'

        return http_object
    except IOError:
        print("[*] WARNING: Credentials file not in the same directory"
              " as EyeWitness")
        print('[*] Skipping credential check')
        return http_object


def open_file_input(cli_parsed):
    files = glob.glob(os.path.join(cli_parsed.d, '*report.html'))
    if len(files) > 0:
        print('\n[*] Done! Report written in the ' + cli_parsed.d + ' folder!')
        print('Would you like to open the report now? [Y/n]')
        while True:
            try:
                response = input().lower()
                if response == "":
                    return True
                else:
                    return strtobool(response)
            except ValueError:
                print("Please respond with y or n")
    else:
        print('[*] No report files found to open, perhaps no hosts were successful')
        return False


def strtobool(value, raise_exc=False):

    str2b_true = {'yes', 'true', 't', 'y', '1'}
    str2b_false = {'no', 'false', 'f', 'n', '0'}

    if isinstance(value, str) or sys.version_info[0] < 3 and isinstance(value, basestring):
        value = value.lower()
        if value in str2b_true:
            return True
        if value in str2b_false:
            return False

    if raise_exc:
        raise ValueError('Expected "%s"' % '", "'.join(str2b_true | str2b_false))
    return None

def class_info():
    class_image = '''MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
M                                                                M
M       .”cCCc”.                                                 M
M      /cccccccc\\                                                M
M      §cccccccc|            Check Back Soon For                 M
M      :ccccccccP                 Upcoming Training              M
M      \\cccccccc()                                               M
M       \\ccccccccD                                               M
M       |cccccccc\\        _                                      M
M       |ccccccccc)     //                                       M
M       |cccccc|=      //                                        M
M      /°°°°°°”-.     (CCCC)                                     M
M      ;----._  _._   |cccc|                                     M
M   .*°       °°   °. \\cccc/                                     M
M  /  /       (      )/ccc/                                      M
M  |_/        |    _.°cccc|                                      M
M  |/         °^^^°ccccccc/                                      M
M  /            \\cccccccc/                                       M
M /              \\cccccc/                                        M
M |                °*°                                           M
M /                  \\      Psss. Follow us on >> Twitter        M
M °*-.__________..-*°°                         >> Facebook       M
M  \\WWWWWWWWWWWWWWWW/                          >> LinkedIn       M
M   \\WWWWWWWWWWWWWW/                                             M
MMMMM|WWWWWWWWWWWW|MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM'''
    print(class_image)
