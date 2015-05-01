import argparse
import os
import re
import time
import sys
import netaddr
import xml.etree.ElementTree as XMLParser
from modules import selenium_module
from modules import objects


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


def target_creator(command_line_object):

    if command_line_object.createtargets is not None:
        print "Creating text file containing all web servers..."

    urls = []
    rdp = []
    vnc = []
    num_urls = 0
    try:
        # Setup variables
        # The nmap xml parsing code was sent to me and worked on by Jason Hill
        # (@jasonhillva)
        http_ports = [80, 8000, 8080, 8081, 8082, 8888]
        https_ports = [443, 8443, 9443]
        rdp_ports = [3389]
        vnc_ports = [5900, 5901]

        try:
            xml_tree = XMLParser.parse(command_line_object.f)
        except IOError:
            print "Error: EyeWitness needs a text or XML file to parse URLs!"
            sys.exit()
        root = xml_tree.getroot()

        if root.tag.lower() == "nmaprun" and root.attrib.get('scanner') == 'nmap':
            print "Detected nmap xml file\n"
            for item in root.iter('host'):
                check_ip_address = False
                # We only want hosts that are alive
                if item.find('status').get('state') == "up":
                    web_ip_address = None
                    # If there is no hostname then we'll set the IP as the
                    # target 'hostname'
                    if item.find('hostnames/hostname') is not None and command_line_object.no_dns is False:
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

                            if command_line_object.rdp:
                                if int(port) in rdp_ports or 'ms-wbt' in service:
                                    rdp.append(target)

                            if command_line_object.vnc:
                                if int(port) in vnc_ports or 'vnc' in services:
                                    vnc.append((target, port))

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

            if command_line_object.createtargets is not None:
                with open(command_line_object.createtargets, 'w') as target_file:
                    for item in urls:
                        target_file.write(item + '\n')
                print "Target file created (" + command_line_object.createtargets + ").\n"
                sys.exit()
            return urls, rdp, vnc

        # Added section for parsing masscan xml output which is "inspired by"
        # but not identical to the nmap format. Based on existing code above
        # for nmap xml files. Also added check for "scanner" attribute to
        # differentiate between a file from nmap and a file from masscan.

        if root.tag.lower() == "nmaprun" and root.attrib.get('scanner') == 'masscan':
            print "Detected masscan xml file\n"
            for item in root.iter('host'):
                check_ip_address = False
                # Masscan only includes hosts that are alive, so less checking needed.
                web_ip_address = None
                target = item.find('address').get('addr')
                # find open ports that match the http/https port list or
                # have http/https as a service
                for ports in item.iter('port'):
                    if ports.find('state').get('state') == 'open':
                        port = ports.attrib.get('portid')

                        # Check for http ports
                        if int(port) in http_ports:
                            protocol = 'http'
                            urlBuild = '%s://%s:%s' % (
                                protocol, target, port)
                            if urlBuild not in urls:
                                urls.append(urlBuild)

                        # Check for https ports
                        if int(port) in https_ports:
                            protocol = 'https'
                            urlBuild = '%s://%s:%s' % (
                                protocol, target, port)
                            if urlBuild not in urls:
                                urls.append(urlBuild)

                        # Check for RDP
                        if int(port) in rdp_port:
                            protocol = 'rdp'
                            if target not in rdp:
                                rdp.append(target)

                        # Check for VNC
                        if int(port) in vnc_ports:
                            protocol = 'vnc'
                            if target not in vnc:
                                vnc.append(target)

            if command_line_object.createtargets is not None:
                with open(command_line_object.createtargets, 'w') as target_file:
                    for item in urls:
                        target_file.write(item + '\n')
                print "Target file created (" + command_line_object.createtargets + ").\n"
                sys.exit()

            return urls, rdp, vnc

        # Find root level if it is nessus output
        # This took a little bit to do, to learn to parse the nessus output.
        # There are a variety of scripts that do it, but also being able to
        # reference PeepingTom really helped.  Tim did a great job figuring
        # out how to parse this file format
        elif root.tag.lower() == "nessusclientdata_v2":
            print "Detected .Nessus file\n"
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
                    elif 'vnc' in service_name and plugin_name.lower().startswith('service detection') and command_line_object.vnc:
                        port_number = item.get('port')
                        vnc.append((name, port))
                    elif 'msrdp' in service_name and plugin_name.lower().startswith('windows terminal services') and command_line_object.rdp:
                        rdp.append(name)
            if command_line_object.createtargets is not None:
                with open(command_line_object.createtargets, 'w') as target_file:
                    for item in urls:
                        target_file.write(item + '\n')
                print "Target file created (" + command_line_object.createtargets + ").\n"
                sys.exit()
            return urls, rdp, vnc

        else:
            print "ERROR: EyeWitness only accepts NMap XML files!"

    except XMLParser.ParseError:

        try:
            # Open the URL file and read all URLs, and reading again to catch
            # total number of websites
            with open(command_line_object.f) as f:
                all_urls = [url for url in f if url.strip()]

            # else:
            for line in all_urls:
                if line.startswith('http://') or line.startswith('https://'):
                    urls.append(line)
                elif line.startswith('rdp://'):
                    rdp.append(line[6:])
                elif line.startswith('vnc://'):
                    vnc.append(line[6:])
                else:
                    urls.append(line)
                    if command_line_object.rdp:
                        rdp.append(line)
                    if command_line_object.vnc:
                        vnc.append(line)
                num_urls += 1

            return urls, rdp, vnc

        except IOError:
            print "ERROR: You didn't give me a valid file name! I need a valid\
            file containing URLs!"
            sys.exit()


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

    if cli_parsed.single and cli_parsed.web:
        selenium_module.single_mode(cli_parsed)