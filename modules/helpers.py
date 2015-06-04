import os
import platform
import re
import shutil
import sys
import xml.etree.ElementTree as XMLParser
import time
import random

try:
    from fuzzywuzzy import fuzz
except ImportError:
    print '[*] fuzzywuzzy not found.'
    print '[*] Please run the script in the setup directory!'
    sys.exit()


def target_creator(command_line_object):
    """Parses input files to create target lists

    Args:
        command_line_object (ArgumentParser): Command Line Arguments

    Returns:
        List: URLs detected for http
        List: Hosts detected for RDP
        List: Hosts detected for VNC
    """
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
                                if int(port) in vnc_ports or 'vnc' in service:
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
                # Masscan only includes hosts that are alive, so less checking
                # needed.
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
                        if int(port) in rdp_ports:
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


def create_web_index_head(date, time):
    """Creates the header for a http report

    Args:
        date (String): Date of report start
        time (String): Time of report start

    Returns:
        String: HTTP Report Start html
    """
    return ("""<html>
        <head>
        <link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>
        <title>EyeWitness Report</title>
        <script src="jquery-1.11.3.min.js"></script>
        <script type="text/javascript">
        function toggleUA(id, url){{
        idi = "." + id;
        $(idi).toggle();
        change = document.getElementById(id);
        if (change.innerHTML.indexOf("expand") > -1){{
            change.innerHTML = "Click to collapse User Agents for " + url;
        }}else{{
            change.innerHTML = "Click to expand User Agents for " + url;
        }}
        }}
        </script>
        </head>
        <body>
        <center>
        <center>Report Generated on {0} at {1}</center>""").format(date, time)


def create_table_head():
    return ("""<table border=\"1\">
        <tr>
        <th>Web Request Info</th>
        <th>Web Screenshot</th>
        </tr>""")


def create_report_toc_head(date, time):
    return ("""<html>
        <head>
        <title>EyeWitness Report Table of Contents</title>
        </head>
        <h2>Table of Contents</h2>""")


def vnc_rdp_table_head():
    return ("""<table border=\"1\" align=\"center\">
    <tr>
    <th>IP / Screenshot</th>
    </tr>""")


def vnc_rdp_header(date, time):
    web_index_head = ("""<html>
    <head>
    <link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>
    <title>EyeWitness Report</title>
    </head>
    <body>
    <center>Report Generated on {0} at {1}</center>
    <br>""").format(date, time)
    return web_index_head


def title_screen():
    """Prints the title screen for EyeWitness
    """
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')
    print "#" * 80
    print "#" + " " * 34 + "EyeWitness" + " " * 34 + "#"
    print "#" * 80 + "\n"

    python_info = sys.version_info
    if python_info[0] is not 2 or python_info[1] < 7:
        print "[*] Error: Your version of python is not supported!"
        print "[*] Error: Please install Python 2.7.X"
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


def process_group(data, group, toc, toc_table, page_num, section, sectionid, html):
    """Retreives a group from the full data, and creates toc stuff

    Args:
        data (List): Full set of data containing all hosts
        group (String): String representing group to process
        toc (String): HTML for Table of Contents
        toc_table (String): HTML for Table in ToC
        page_num (int): Page number we're on in the report
        section (String): Display name of the group
        sectionid (String): Unique ID for ToC navigation
        html (String): HTML for current page of report

    Returns:
        List: Elements for category sorted and grouped
        String: HTML representing ToC
        String: HTML representing ToC Table
        String: HTML representing current report page
    """
    group_data = sorted([x for x in data if x.category == group],
                        key=lambda (k): k.page_title)

    grouped_elements = []
    if len(group_data) == 0:
        return grouped_elements, toc, toc_table, html
    if page_num == 0:
        toc += ("<li><a href=\"report.html#{0}\">{1} (Page 1)</a></li>").format(
            sectionid, section)
    else:
        toc += ("<li><a href=\"report_page{0}.html#{1}\">{2} (Page {0})</a></li>").format(
            str(page_num+1), sectionid, section)

    html += "<h2 id=\"{0}\">{1}</h2>".format(sectionid, section)
    unknowns = [x for x in group_data if x.page_title == 'Unknown']
    group_data = [x for x in group_data if x.page_title != 'Unknown']
    while len(group_data) > 0:
        test_element = group_data.pop(0)
        temp = [x for x in group_data if fuzz.token_sort_ratio(
            test_element.page_title, x.page_title) >= 70]
        temp.append(test_element)
        temp = sorted(temp, key=lambda (k): k.page_title)
        grouped_elements.extend(temp)
        group_data = [x for x in group_data if fuzz.token_sort_ratio(
            test_element.page_title, x.page_title) < 70]

    group_data.extend(unknowns)
    toc_table += ("<tr><td>{0}</td><td>{1}</td>").format(section,
                                                         str(len(grouped_elements)))
    return grouped_elements, toc, toc_table, html


def write_vnc_rdp_data(cli_parsed, data):
    """Writes the reports for VNC and RDP hosts

    Args:
        cli_parsed (ArgumentParser): CLI Options
        data (TYPE): Full set of VNC/RDP data
    """
    vncstuff = [x for x in data if x.proto == 'vnc']
    rdpstuff = [x for x in data if x.proto == 'rdp']

    for x in [x for x in [vncstuff, rdpstuff] if len(x) > 0]:
        if len(x) == 0:
            return
        pages = []
        html = u""
        counter = 1
        proto = x[0].proto
        header = vnc_rdp_header(cli_parsed.date, cli_parsed.time)
        table_head = vnc_rdp_table_head()
        for y in x:
            html += y.create_table_html()
            if counter % cli_parsed.results == 0:
                html = (header + "EW_REPLACEME" + table_head + html +
                        "</table><br>")
                pages.append(html)
                html = u""
            counter += 1

        if html != u"":
            html = (header + "EW_REPLACEME" + table_head + html +
                    "</table><br>")
            pages.append(html)

        if len(pages) == 1:
            with open(os.path.join(cli_parsed.d, proto + '_report.html'), 'a') as f:
                f.write(pages[0].replace('EW_REPLACEME', ''))
                f.write("</body>\n</html>")
        else:
            num_pages = len(pages) + 1
            bottom_text = "\n<center><br>"
            bottom_text += (
                "<a href=\"{0}_report.html\"> Page 1</a>").format(proto)
            for i in range(2, num_pages):
                bottom_text += ("<a href=\"{0}_report_page{1}.html\"> Page {1}</a>").format(proto,
                                                                                            str(i))
            bottom_text += "</center>\n"
            top_text = bottom_text
            for i in range(0, len(pages)):
                headfoot = "<center>"
                if i == 0:
                    headfoot += ("<a href=\"{0}_report_page2.html\"> Next Page "
                                 "</a></center>").format(proto)
                elif i == len(pages) - 1:
                    if i == 1:
                        headfoot += ("<a href=\"{0}_report.html\">Previous Page"
                                     "</a>&nbsp</center>").format(proto)
                    else:
                        headfoot += ("<a href=\"{0}_report_page{1}.html\"> Previous Page "
                                     "</a></center>").format(proto, str(i))
                elif i == 1:
                    headfoot += ("<a href=\"{0}_report.html\">Previous Page</a>&nbsp"
                                 "<a href=\"{0}_report_page{1}.html\"> Next Page"
                                 "</a></center>").format(proto, str(i+2))
                else:
                    headfoot += ("<a href=\"{0}_report_page{1}.html\">Previous Page</a>"
                                 "&nbsp<a href=\"{0}_report_page{2}.html\"> Next Page"
                                 "</a></center>").format(proto, str(i), str(i+2))
                pages[i] = pages[i].replace(
                    'EW_REPLACEME', headfoot + top_text) + bottom_text + '<br>' + headfoot + '</body></html>'

            with open(os.path.join(cli_parsed.d, proto + '_report.html'), 'a') as f:
                f.write(pages[0])
            for i in range(2, len(pages) + 1):
                with open(os.path.join(cli_parsed.d, proto + '_report_page{0}.html'.format(str(i))), 'w') as f:
                    f.write(pages[i - 1])


def sort_data_and_write(cli_parsed, data):
    """Writes out reports for HTTP objects

    Args:
        cli_parsed (TYPE): CLI Options
        data (TYPE): Full set of data
    """
    # We'll be using this number for our table of contents
    total_results = len(data)
    from modules.objects import VNCRDPTableObject
    # We want to seperate out VNC?RDP results and handle them seperately
    vncrdpdata = [x for x in data if isinstance(x, VNCRDPTableObject)]
    data[:] = [x for x in data if not isinstance(x, VNCRDPTableObject)]
    write_vnc_rdp_data(cli_parsed, vncrdpdata)
    web_results = len(data)
    categories = [(None, 'Uncategorized', 'uncat'),
                  ('highval', 'High Value Targets', 'highval'),
                  ('cms', 'Content Management System (CMS)', 'cms'),
                  ('idrac', 'IDRAC/ILo', 'idrac'),
                  ('nas', 'Network Attached Storage (NAS)', 'nas'),
                  ('netdev', 'Network Devices', 'netdev'),
                  ('voip', 'Voice/Video over IP (VoIP)', 'voip'),
                  ('unauth', '401/403 Unauthorized', 'unauth'),
                  ('notfound', '404 Not Found', 'notfound'),
                  ('crap', 'Splash Pages', 'crap'),
                  ('printer', 'Printers', 'printer'),
                  ]
    if total_results == 0:
        print '[*] No URLS specified or no screenshots taken! Exiting'
        sys.exit()
    # Initialize stuff we need
    pages = []
    toc = create_report_toc_head(cli_parsed.date, cli_parsed.time)
    toc_table = "<table class=\"toc_table\">"
    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)
    table_head = create_table_head()
    counter = 1

    # Pre-filter error entries
    errors = sorted([x for x in data if x.error_state is not None],
                    key=lambda (k): (k.error_state, k.page_title))
    data[:] = [x for x in data if x.error_state is None]
    data = sorted(data, key=lambda (k): k.page_title)
    html = u""
    # Loop over our categories and populate HTML
    for cat in categories:
        grouped, toc, toc_table, html = process_group(
            data, cat[0], toc, toc_table, len(pages), cat[1], cat[2], html)
        if len(grouped) > 0:
            html += table_head
        for obj in grouped:
            html += obj.create_table_html()
            if counter % cli_parsed.results == 0:
                html = (web_index_head + "EW_REPLACEME" + html +
                        "</table><br>")
                pages.append(html)
                html = u"" + table_head
            counter += 1
        if len(grouped) > 0:
            html += "</table><br>"

    # Add our errors here (at the very very end)
    for obj in errors:
        html += obj.create_table_html()
        if counter % cli_parsed.results == 0:
            html = (web_index_head + "EW_REPLACEME" + table_head + html +
                    "</table><br>")
            pages.append(html)
            html = u""
        counter += 1

    # Close out any stuff thats hanging
    toc += "</ul>"
    toc_table += "<tr><td>Errors</td><td>{0}</td></tr>".format(
        str(len(errors)))
    toc_table += "<tr><th>Total</th><td>{0}</td></tr>".format(web_results)
    toc_table += "</table>"

    if html != u"":
        html = (web_index_head + "EW_REPLACEME" + html +
                "</table><br>")
        pages.append(html)

    toc = "<center>{0}<br><br>{1}<br><br></center>".format(toc, toc_table)

    if len(pages) == 1:
        with open(os.path.join(cli_parsed.d, 'report.html'), 'a') as f:
            f.write(toc)
            f.write(pages[0].replace('EW_REPLACEME', ''))
            f.write("</body>\n</html>")
    else:
        num_pages = len(pages) + 1
        bottom_text = "\n<center><br>"
        bottom_text += ("<a href=\"report.html\"> Page 1</a>")
        # Generate our header/footer data here
        for i in range(2, num_pages):
            bottom_text += ("<a href=\"report_page{0}.html\"> Page {0}</a>").format(
                str(i))
        bottom_text += "</center>\n"
        top_text = bottom_text
        # Generate our next/previous page buttons
        for i in range(0, len(pages)):
            headfoot = "<center>"
            if i == 0:
                headfoot += ("<a href=\"report_page2.html\"> Next Page "
                             "</a></center>")
            elif i == len(pages) - 1:
                if i == 1:
                    headfoot += ("<a href=\"report.html\"> Previous Page "
                                 "</a></center>")
                else:
                    headfoot += ("<a href=\"report_page{0}.html\"> Previous Page "
                                 "</a></center>").format(str(i))
            elif i == 1:
                headfoot += ("<a href=\"report.html\">Previous Page</a>&nbsp"
                             "<a href=\"report_page{0}.html\"> Next Page"
                             "</a></center>").format(str(i+2))
            else:
                headfoot += ("<a href=\"report_page{0}.html\">Previous Page</a>"
                             "&nbsp<a href=\"report_page{1}.html\"> Next Page"
                             "</a></center>").format(str(i), str(i+2))
            # Finalize our pages by replacing placeholder stuff and writing out the headers/footers
            pages[i] = pages[i].replace(
                'EW_REPLACEME', headfoot + top_text) + bottom_text + '<br>' + headfoot + '</body></html>'

        # Write out our report to disk!
        if len(pages) == 0:
            return
        with open(os.path.join(cli_parsed.d, 'report.html'), 'a') as f:
            f.write(toc)
            f.write(pages[0])
        for i in range(2, len(pages) + 1):
            with open(os.path.join(cli_parsed.d, 'report_page{0}.html'.format(str(i))), 'w') as f:
                f.write(pages[i - 1])


def do_jitter(cli_parsed):
    """Jitters between URLs to add delay/randomness

    Args:
        cli_parsed (ArgumentParser): CLI Object

    Returns:
        TYPE: Description
    """
    if cli_parsed.jitter is not 0:
        sleep_value = random.randint(0, 30)
        sleep_value = sleep_value * .01
        sleep_value = 1 - sleep_value
        sleep_value = sleep_value * cli_parsed.jitter
        print "[*] Sleeping for " + str(sleep_value) + " seconds.."
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
    os.makedirs(cli_parsed.d)
    os.makedirs(os.path.join(cli_parsed.d, 'screens'))
    os.makedirs(os.path.join(cli_parsed.d, 'source'))
    local_path = os.path.dirname(os.path.realpath(__file__))
    # Move our jquery file to the local directory
    shutil.copy2(os.path.join(local_path, '..', 'bin', 'jquery-1.11.3.min.js'), cli_parsed.d)

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
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'signatures.txt')
        with open(path) as sig_file:
            signatures = sig_file.readlines()

        # Loop through and see if there are any matches from the source code
        # EyeWitness obtained
        for sig in signatures:
            # Find the signature(s), split them into their own list if needed
            # Assign default creds to its own variable
            sig_cred = sig.split('|')
            page_sig = sig_cred[0].split(";")
            cred_info = sig_cred[1]
            category = sig_cred[2]
            if cred_info == '':
                cred_info = None
            if category == 'none':
                category = None

            # Set our variable to 1 if the signature was not identified.  If it is
            # identified, it will be added later on.  Find total number of
            # "signatures" needed to uniquely identify the web app
            sig_not_found = 0
            # signature_range = len(page_sig)

            # This is used if there is more than one "part" of the
            # web page needed to make a signature Delimete the "signature"
            # by ";" before the "|", and then have the creds after the "|"
            for individual_signature in page_sig:
                if str(http_object.source_code).lower().find(
                        individual_signature.lower()) is not -1:
                    pass
                else:
                    sig_not_found = 1

            # If the signature was found, return the creds
            if sig_not_found == 0:
                http_object.default_creds = cred_info
                http_object.category = category.strip()
                return http_object

        http_object.default_creds = None
        http_object.category = None
        return http_object
    except IOError:
        print("[*] WARNING: Credentials file not in the same directory"
              " as EyeWitness")
        print '[*] Skipping credential check'
        return http_object
