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
from pathlib import Path
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

    # Use pathlib for cross-platform path handling
    output_dir = Path(cli_object.d)
    screens_pattern = str(output_dir / 'screens' / '*.png')
    
    for name in glob.glob(screens_pattern):
        with open(name, 'rb') as screenshot:
            pic_data = screenshot.read()
        md5_hash = hashlib.md5(pic_data).hexdigest()
        
        # Get relative path from output directory for storage
        name_path = Path(name)
        relative_path = name_path.relative_to(output_dir)
        relative_path_str = str(relative_path).replace('\\', '/')  # Normalize for HTML
        
        if md5_hash in hash_files:
            hash_files[md5_hash].append(relative_path_str)
        else:
            hash_files[md5_hash] = [relative_path_str]

    # Find HTML report files
    html_pattern = str(output_dir / '*.html')
    for html_file in glob.glob(html_pattern):
        report_files.append(html_file)

    # Process duplicates
    for hex_value, file_dict in hash_files.items():
        total_files = len(file_dict)
        if total_files > 1:
            original_pic_name = file_dict[0]
            for num in range(1, total_files):
                next_filename = file_dict[num]
                
                # Update HTML report files
                for report_page in report_files:
                    with open(report_page, 'r') as report:
                        page_text = report.read()
                    page_text = page_text.replace(next_filename, original_pic_name)
                    with open(report_page, 'w') as report_out:
                        report_out.write(page_text)
                
                # remove the duplicate 
                duplicate_file_path = output_dir / next_filename.replace('/', os.sep)
                if duplicate_file_path.exists():
                    os.remove(duplicate_file_path)  # should probably use pathlib but this works
                
                # Update CSV file
                csv_file_path = output_dir / "Requests.csv"
                if csv_file_path.exists():
                    with open(csv_file_path, 'r') as csv_port_file:
                        csv_lines = csv_port_file.read()
                        if next_filename in csv_lines:
                            csv_lines = csv_lines.replace(next_filename, original_pic_name)
                    with open(csv_file_path, 'w') as csv_port_writer:
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
                char = url_again.split(":")[2].split("/")[0]
                check = char.isdigit()
                if check == True:                   
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
            if ' ' in url_again.strip():
                    print("ERROR: You potentially provided an mal-formed URL!")
                    print("ERROR: URL is - " + url_again)
                    sys.exit()

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

def title_screen(cli_parsed):
    """Prints the title screen for EyeWitness
    """
    if not cli_parsed.no_clear:
        from modules.platform_utils import platform_mgr
        platform_mgr.clear_screen()

    print("#" * 80)
    print("#" + " " * 34 + "EyeWitness" + " " * 34 + "#")
    print("#" * 80)
    print("#" + " " * 11 + "Red Siege Information Security - https://www.redsiege.com" + " " * 10 + "#")
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
    # create output dirs and copy css/js files

    # Create output directories using pathlib for cross-platform compatibility
    output_dir = Path(cli_parsed.d)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    output_dir.mkdir(parents=True)
    (output_dir / 'screens').mkdir()
    (output_dir / 'source').mkdir()
    
    # Get paths using pathlib
    local_path = Path(__file__).parent
    bin_path = local_path.parent / 'bin'

    # Copy CSS and JS files using pathlib
    shutil.copy2(bin_path / 'jquery-3.7.1.min.js', output_dir)
    shutil.copy2(bin_path / 'bootstrap.min.css', output_dir)
    shutil.copy2(bin_path / 'style.css', output_dir)



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
        # Use pathlib for cross-platform path handling
        module_dir = Path(__file__).parent
        sigpath = module_dir.parent / 'signatures.txt'
        catpath = module_dir.parent / 'categories.txt'
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

# Waiting for approval to add web scraper for class dates. 
# Makes zero sense to hard code these as an advert people would need to pull down
# the latest version of the code everytime a new class is offered
# get_class_info() method goes here. 

def class_info():
    class_image = '''MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
M                                                                M
M       .”cCCc”.                                                 M
M      /cccccccc\\                                                M
M      §cccccccc|                                                M
M      :ccccccccP                                                M
M      \\cccccccc()                  Looking for training?       M
M       \\ccccccccD             https://redsiege.com/training     M
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
