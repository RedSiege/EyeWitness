#!/usr/bin/env python

"""
 This script's inspiration was Tim Tomes's web screenshotting script PeepingTom
 I ran into issues where PeepingTom wasn't able to grab screenshots of certain websites, and the required libraries
 weren't all installed by default.  I wanted to find something that I felt was reliable, so Ghost is being used.  I also wanted to automate the install of dependencies, so this is the result of my work.
 A lot of the report output is based off of how Tim did PeepingTom because I thought he did a great job with it.
 Finally, I also wanted it to be able to identify default creds.  That will be a growing process.
"""

import ghost as screener
import argparse
import os
import time
import sys
import xml.etree.ElementTree as XMLParser
import urllib2
import cgi
import re
import logging
import random
import subprocess

def cliParser():

    # Command line argument parser
    parser = argparse.ArgumentParser(add_help=False, description="EyeWitness is a tool used to capture screenshots from a list of URLs")
    parser.add_argument("-f", metavar="Filename", help="File containing URLs to screenshot, each on a new line, NMap XML output, or a .nessus file")
    parser.add_argument("-t", metavar="Timeout", default="7", help="[Optional] Maximum number of seconds to wait while requesting a web page (Default: 7)")
    parser.add_argument("-d", metavar="Directory Name", help="[Optional] Directory name for report output")
    parser.add_argument('-h', '-?', '--h', '-help', '--help', action="store_true", help=argparse.SUPPRESS)
    parser.add_argument('--single', metavar="Single URL", help="Single URL to screenshot")
    parser.add_argument('--useragent', metavar="User Agent", help="User Agent to use for all requests")
    parser.add_argument('--cycle', metavar="UA Type", help="User Agent type (Browser, Mobile, Crawler, Scanner, Misc, All)")
    parser.add_argument("--difference", metavar="Difference Threshold", default="50", help="[Optional] Difference threshold when determining if user agent requests are close \"enough\" (Default: 50)")
    parser.add_argument('--jitter', metavar="# of Seconds", help="Randomize URLs and add a random delay between requests")
    parser.add_argument("--open", action='store_true', help="[Optional] Open all URLs in a browser")
    parser.add_argument("--skipcreds", action='store_true', help="Skip checking for default creds")
    args = parser.parse_args()

    if args.h:
        parser.print_help()
        sys.exit()

    if args.single:
        pass
    else:
        args.single = "None"

    if args.useragent:
        pass
    else:
        args.useragent = "None"

    if args.jitter:
        pass
    else:
        args.jitter = "None"

    if args.d:
        current_directory = os.path.dirname(os.path.realpath(__file__))
        if args.d.startswith('/'):
            if os.access(os.path.dirname(args.d), os.W_OK):
                pass
            else:
                print "[*] Error: Please provide a valid folder name/Path\n"
                parser.print_help()
                sys.exit()
        else:
            if os.access(os.path.dirname(current_directory + "/" + args.d), os.W_OK):
                pass
            else:
                print "[*] Error: Please provide a valid folder name/Path\n"
                parser.print_help()
                sys.exit()

    if args.f is None and args.single == "None":
        print "[*] Error: You didn't specify a file! I need a file containing URLs!\n"
        parser.print_help()
        sys.exit()

    if args.t:
        try:
            int(args.t)
        except ValueError:
            args.t = 7

    if args.difference:
        try:
            int(args.t)
        except ValueError:
            args.t = 50

    if args.cycle:
        pass
    else:
        args.cycle = "None"

    # Return the file name which contains the URLs
    return args.f, args.t, args.open, args.single, args.d, args.jitter, args.useragent, args.cycle, args.difference, args.skipcreds, current_directory

def folderOut(dir_name, full_path):

    # Get the date and time, and create output name
    current_date = time.strftime("%m/%d/%Y")
    current_time = time.strftime("%H:%M:%S")
    if dir_name is not "None":
        output_folder_name = dir_name
    else:
        output_folder_name = current_date.replace("/", "") + "_" + current_time.replace(":", "")

    # Write out the CSS stylesheet
    css_page =  """img {
    max-width: 100%;
    height: auto;
    }
    #screenshot{
    overflow: auto;
    max-width: 850px;
    max-height: 550px;
    }"
    """.replace('    ', '')

    if output_folder_name.startswith('/'):
        # Create a folder which stores all snapshots
        # If it starts with a "/", then assume it is a full path
        os.system("mkdir " + output_folder_name)
        os.system("mkdir " + output_folder_name + "/screens")
        os.system("mkdir " + output_folder_name + "/source")

        with open(output_folder_name + "/style.css", 'w') as css_file:
            css_file.write(css_page)

    # If it doesn't start with a "/", then assume it should be in the same directory as EyeWitness
    else:
        # Create a folder which stores all snapshots
        # note- os.makedirs
        os.system("mkdir " + full_path + "/" + output_folder_name)
        os.system("mkdir " + full_path + "/" + output_folder_name + "/screens")
        os.system("mkdir " + full_path + "/" + output_folder_name + "/source")

        with open(full_path + "/" + output_folder_name + "/style.css", 'w') as css_file:
            css_file.write(css_page)

    return output_folder_name, current_date, current_time

def logistics(url_file):

    try:
        # Setup variables
        # The nmap xml parsing code was sent to me and worked on by Jason Hill (@jasonhillva)
        http_ports = [80,8000,8080,8081,8082]
        https_ports = [443,8443]
        urls = []
        num_urls = 0

        try:
            xml_tree = XMLParser.parse(url_file)
        except IOError:
            print "Error: EyeWitness needs a text or XML file for parsing URLs!"
            sys.exit()
        root = xml_tree.getroot()

        if root.tag.lower() == "nmaprun":
            for item in root.iter('host'):
                # We only want hosts that are alive
                if item.find('status').get('state') == "up":
                    # If there is no hostname then we'll set the IP as the target 'hostname'
                    if item.find('hostnames/hostname') is not None:
                        target = item.find('hostnames/hostname').get('name')
                    else:
                        target = item.find('address').get('addr')
                    # find open ports that match the http/https port list or have http/https as a service
                    for ports in item.iter('port'):
                        if ports.find('state').get('state') == 'open':
                            port = ports.attrib.get('portid')
                            try:
                                service = ports.find('service').get('name').lower()
                            except AttributeError:
                                # This hits when it finds an open port, but isn't able to
                                # Determine the name of the service running on it, so we'll
                                # just pass in this instance
                                pass
                            try:
                                tunnel = ports.find('service').get('tunnel').lower()
                            except AttributeError:
                                # This hits when it finds an open port, but isn't able to
                                # Determine the name of the service running on it, so we'll
                                # just pass in this instance
                                tunnel = "fakeportservicedoesntexist"
                            if int(port) in http_ports or 'http' in service:
                                protocol = 'http'
                                if int(port) in https_ports or 'https' in service or ('http' in service and 'ssl' in tunnel):
                                    protocol = 'https'
                                urlBuild = '%s://%s:%s' % (protocol,target,port)
                                if urlBuild not in urls:
                                    urls.append(urlBuild)
                                    num_urls = num_urls + 1
            return urls, num_urls

        # Find root level if it is nessus output
        # This took a little bit to do, to learn to parse the nessus output.  There are a variety of
        # scripts that do it, but also being able to reference PeepingTom really helped.  Tim did a great
        # job figuring out how to parse this file format
        elif root.tag.lower() == "nessusclientdata_v2":
            # Find each host in the nessus report
            for host in root.iter("ReportHost"):
                name = host.get('name')
                for item in host.iter('ReportItem'):
                    service_name = item.get('svc_name')
                    plugin_name = item.get('pluginName')
                    # I had www, but later checked out PeepingTom and Tim had http? and https? for here
                    # Small tests of mine haven't shown those, but as he's smarter than I am, I'll add them too
                    if (service_name in ['www','http?','https?'] and plugin_name.lower().startswith('service detection')):
                        port_number = item.get('port')
                        # Convert essentially to a text string and then strip newlines
                        plugin_output = item.find('plugin_output').text.strip()
                        # Look to see if web page is over SSL or TLS.  
                        # If so assume it is over https and prepend https, otherwise, http
                        http_output = re.search('TLS', plugin_output) or re.search('SSL', plugin_output)
                        if http_output:
                            url = "https://" + name + ":" + port_number
                        else:
                            url = "http://" + name + ":" + port_number
                        # Just do a quick check to make sure the url we are adding doesn't already exist
                        if url not in urls:
                            urls.append(url)
                            num_urls = num_urls + 1

            return urls, num_urls

        else:
            print "ERROR: EyeWitness only accepts NMap XML files!"

    except XMLParser.ParseError:

        try:
            # Open the URL file and read all URLs, and reading again to catch total number of websites
            with open(url_file, 'r') as f:
                all_urls = f.readlines()

            for line in all_urls:
                urls.append(line)
                num_urls = num_urls + 1

            return urls, num_urls

        except IOError:
            print "ERROR: You didn't give me a valid file name! I need a valid file containing URLs!"
            sys.exit()

def titleScreen():
    os.system('clear')
    print "#############################################################################"
    print "#                               EyeWitness                                  #"
    print "#############################################################################\n"

def defaultCreds(page_content, full_file_path):
    # Read in the file containing the web "signatures"
    with open(full_file_path + '/signatures.txt', 'r') as sig_file:
        signatures = sig_file.readlines()

    # Loop through and see if there are any matches from the source code EyeWitness obtained
    for sig in signatures:
        # Find the signature(s), split them into their own list if needed
        # Assign default creds to its own variable
        sig_cred = sig.split('|')
        page_sig = sig_cred[0].split(";")
        cred_info = sig_cred[1]

        # Set our variable to 1 if the signature was identified.  If it is identified,
        # it will be added later on.  Find total number of "signatures" needed to uniquely identify
        # the web app
        sig_not_found = 0
        signature_range = len(page_sig)

        # This is used if there is more than one "part" of the web page needed to make a signature
        # Delimete the "signature" by ";" before the "|", and then have the creds after the "|"
        for individual_signature in range(0, signature_range):
            if str(page_content).find(page_sig[individual_signature]) is not -1:
                pass
            else:
                sig_not_found = 1

        # If the signature was found, break out of loops and return the creds
        if sig_not_found == 0:
            return cred_info
            break

def webHeader():
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
    </tr>""".format(report_day=report_date, reporthtml_time=report_time).replace('    ', '')
    return web_index_head

def fileNames(url_given):
    url_given = url_given.strip()
    pic_name = url_given
    pic_name = pic_name.replace("//", "")
    pic_name = pic_name.replace(":", "")
    pic_name = pic_name.replace("/", "")
    src_name = pic_name + ".txt"
    pic_name = pic_name + ".png"
    return url_given, src_name, pic_name

def htmlEncode(dangerous_data):
    encoded = cgi.escape(dangerous_data, quote=True)
    return encoded

def ghostCapture(incoming_ghost_object, screen_url, rep_fold, screen_name, ewitness_dir_path):
    # Try to get our screenshot and source code of the page
    # Write both out to disk if possible (if we can get one, we can get the other)
    ghost_page, ghost_extra_resources = incoming_ghost_object.open(screen_url, auth=('none', 'none'), default_popup_response=True)
    
    if rep_fold.startswith('/'):
        incoming_ghost_object.capture_to(rep_fold + "/screens/" + screen_name)
    else:
        incoming_ghost_object.capture_to(ewitness_dir_path + "/" + rep_fold + "/screens/" + screen_name)
    return ghost_page, ghost_extra_resources

def backupRequest(page_code, outgoing_url, source_code_name, content_value, iwitness_path, skip_cred_check):

    try:
        # Check if page is blank, due to no-cache.  If so, make a backup request via urllib2
        if page_code.content == "None":
            try:
                response = urllib2.urlopen(outgoing_url)
                page_code.content = response.read()
                response.close()
            except urllib2.HTTPError:
                page_code.content = "Sorry, but couldn't get source code for potentially a couple reasons.  If it was Basic Auth, a 50X, or a 40X error, EyeWitness won't return source code.  Couldn't get source from " + url + "."
            except urllib2.URLError:
                page_code.content = "Name resolution could not happen with " + outgoing_url + "."

        if report_folder.startswith('/'):
            with open(report_folder + "/source/" + source_code_name, 'w') as source:
                source.write(page_code.content)
        else:
            with open(iwitness_path + "/" + report_folder + "/source/" + source_code_name, 'w') as source:
                source.write(page_code.content)

        if skip_cred_check:
            default_creds = None
        else:
            default_creds = defaultCreds(page_code.content, iwitness_path)

    except AttributeError:
        print "[*] ERROR: Web page possibly blank or SSL error!"
        content_value = 1
        default_creds = None

    return content_value, default_creds

def tableMaker(web_table_index, website_url, possible_creds, web_page, content_empty, log_path, extra_notes, browser_out, ua_out, source_code_table, screenshot_table, length_difference):

    # Continue adding to the table assuming that we were able to capture the screenshot
    # Only add elements if they exist
    # This block adds the URL to the row at the top
    web_table_index += """<tr>
    <td><div style=\"display: inline-block; width: 300px; word-wrap: break-word\">
    <a href=\"{web_url_addy}\" target=\"_blank\">{web_url_addy}</a><br>
    """.format(web_url_addy=website_url).replace('    ', '')

    if browser_out is not "None" and ua_out is not "None" and length_difference is not "Baseline" and length_difference is not "None":
        web_table_index += """
        <br>This request was different from the baseline.<br>
        The browser type is: <b>{browser_report}</b><br><br>
        The user agent is: <b>{useragent_report}</b><br><br>
        Difference in length of the two webpage sources is: <b>{page_source_hash}</b><br>
        """.format(browser_report=browser_out, useragent_report=ua_out, page_source_hash=length_difference).replace('    ', '')

    if length_difference == "Baseline":
        web_table_index +="""
        <br>This is the baseline request.<br>
        The browser type is: <b>{browser_report}</b><br><br>
        The user agent is: <b>{useragent_report}</b><br><br>
        <b>This is the baseline request.</b><br>
        """.format(browser_report=browser_out, useragent_report=ua_out).replace('    ', '')

    # Check if log file is empty, if so, good, otherwise, Check for SSL errors
    # If there is a SSL error, be sure to add a note about it in the table
    # Once done, delete the file
    if os.stat(log_path)[6]==0:
        pass
    else:
        with open(log_path, 'r') as log_file:
            log_contents = log_file.readlines()
        for line in log_contents:
            if "SSL certificate error" in line:
                web_table_index += "<br><b>SSL Certificate error present on <a href=\"" + website_url + "\" target=\"_blank\">" + website_url + "</a></b><br>"
                break
        clear_logs = open(log_path, 'w')
        clear_logs.close()

    # If there are some default creds, escape them, and add them to the report
    if possible_creds is not None:
        web_table_index += "<br><b>Default credentials:</b> " + htmlEncode(possible_creds) + "<br>"

    # Loop through all server header responses, and add them to table
    # Handle exception if there is a SSL error and no headers were received.
    try:
        for key, value in web_page.headers.items():
            web_table_index += "<br><b> " + htmlEncode(key.decode('utf-8')) + ":</b> " + htmlEncode(value) + "\n"

    except AttributeError:
        web_table_index += "\n<br><br>Potential blank page or SSL issue with <a href=\"" + website_url + "\" target=\"_blank\">" + website_url + "</a>."

    # If page is empty, or SSL errors, add it to report
    if content_empty == 1:
        web_table_index += """<br></td>
        <td><div style=\"display: inline-block; width: 850px;\">Page Blank or SSL Issues</div></td>
        </tr>
        """.replace('    ', '')

    # If eyewitness could get the source code and take a screenshot, add them to report
    # First line adds source code to header column of table, and then closes out that <td>
    # Second line creates new <td> for the screenshot column, adds screenshot in to report, and closes the <td>
    # Final line closes out the row
    else:
        web_table_index += """<br><br><a href=\"source/{page_source_name}\" target=\"_blank\">Source Code</a></div></td>
        <td><div id=\"screenshot\" style=\"display: inline-block; width: 850px; height 400px; overflow: scroll;\"><a href=\"screens/{screen_picture_name}\" target=\"_blank\"><img src=\"screens/{screen_picture_name}\" height=\"400\"></a></div></td>
        </tr>
        """.format(page_source_name=source_code_table, screen_picture_name=screenshot_table).replace('    ', '')

    return web_table_index

def singleReportPage(report_source, report_path):
    # Close out the html and write it to disk
    report_source += """</table>
    </body>
    </html>
    """.replace('    ', '')
    if report_folder.startswith('/'):
        with open(report_folder + "/report.html", 'w') as fo:
            fo.write(report_source)
    else:
        with open(report_path + "/" + report_folder + "/report.html", 'w') as fo:
            fo.write(report_source)
    return

def userAgentDefinition(cycle_value):
    # Create the dicts which hold different user agents.
    # Thanks to Chris John Riley for having an awesome tool which I could get this info from
    # His tool - UAtester.py - http://blog.c22.cc/toolsscripts/ua-tester/
    # Additional user agent strings came from - http://www.useragentstring.com/pages/useragentstring.php

    # "Normal" desktop user agents
    desktop_uagents = {
    "MSIE9.0" : "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)",
    "MSIE8.0" : "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0)",
    "MSIE7.0" : "Mozilla/5.0 (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)",
    "MSIE6.0" : "Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)",
    "Chrome32.0.1667.0" : "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
    "Chrome31.0.1650.16" : "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36",
    "Firefox25" : "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0",
    "Firefox24" : "Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0,",
    "Opera12.14" : "Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14",
    "Opera12" : "Opera/12.0(Windows NT 5.1;U;en)Presto/22.9.168 Version/12.00",
    "Safari5.1.7" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2",
    "Safari5.0" : "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.18.1 (KHTML, like Gecko) Version/5.0 Safari/533.16"
    }

    # Miscellaneous user agents
    misc_uagents = {
    "wget1.9.1" : "Wget/1.9.1",
    "curl7.9.8" : "curl/7.9.8 (i686-pc-linux-gnu) libcurl 7.9.8 (OpenSSL 0.9.6b) (ipv6 enabled)",
    "PyCurl7.23.1" : "PycURL/7.23.1",
    "Pythonurllib3.1" : "Python-urllib/3.1"
    }

    # Bot crawler user agents
    crawler_uagents = {
    "Baiduspider" : "Baiduspider+(+http://www.baidu.com/search/spider.htm)",
    "Bingbot" : "Mozilla/5.0 (compatible; bingbot/2.0 +http://www.bing.com/bingbot.htm)",
    "Googlebot2.1" : "Googlebot/2.1 (+http://www.googlebot.com/bot.html)",
    "MSNBot2.1" : "msnbot/2.1",
    "YahooSlurp!" : "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)"
    }

    # Random mobile User agents
    mobile_uagents = {
    "BlackBerry" : "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile Safari/534.11+",
    "Android" : "Mozilla/5.0 (Linux; U; Android 2.3.5; en-us; HTC Vision Build/GRI40) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "IEMobile9.0" : "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0)",
    "OperaMobile12.02" : "Opera/12.02 (Android 4.1; Linux; Opera Mobi/ADR-1111101157; U; en-US) Presto/2.9.201 Version/12.02",
    "iPadSafari6.0" : "Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5355d Safari/8536.25",
    "iPhoneSafari7.0.6" : "Mozilla/5.0 (iPhone; CPU iPhone OS 7_0_6 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B651 Safari/9537.53"
    }

    # Web App Vuln Scanning user agents (give me more if you have any)
    scanner_uagents = {
    "w3af" : "w3af.org",
    "skipfish" : "Mozilla/5.0 SF/2.10b",
    "HTTrack" : "Mozilla/4.5 (compatible; HTTrack 3.0x; Windows 98)",
    "nikto" : "Mozilla/5.00 (Nikto/2.1.5) (Evasions:None) (Test:map_codes)"
    }

    # Combine all user agents into a single dictionary
    all_combined_uagents = dict(desktop_uagents.items() + misc_uagents.items() + crawler_uagents.items() + mobile_uagents.items())

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
        print "[*] Error: You did not provide the type of user agents to cycle through!"
        print "[*] Error: Defaulting to desktop browser user agents."
        return desktop_uagents

# This is the ghost object creation function
def casperCreator(ua_capture, url_timeout):
    # Instantiate Ghost Object
    if ua_capture == "None":
        ghost = screener.Ghost(wait_timeout=int(url_timeout), ignore_ssl_errors=True)
    else:
        ghost = screener.Ghost(wait_timeout=int(url_timeout), user_agent=ua_capture, ignore_ssl_errors=True)
    return ghost

def requestComparison(original_content, new_content, max_difference):
    # Function which compares the original baseline request with the new request with the modified user agent
    orig_request_length = len(original_content)
    new_request_length = len(new_content)

    if new_request_length > orig_request_length:
        a, b = new_request_length, orig_request_length
        total_difference = a - b
        if total_difference > int(max_difference):
            return False, total_difference
        else:
            return True, "None"
    else:
        total_difference = orig_request_length - new_request_length
        if total_difference > int(max_difference):
            return False, total_difference
        else:
            return True, "None"

if __name__ == "__main__":

    # Print the title header
    titleScreen()

    # Parse command line options and return the filename containing URLS and how long to wait for each website
    url_filename, timeout_wait, open_urls, single_url, directory_name, request_jitter, browser_user_agent, ua_cycle, diff_value, cred_skip, script_path = cliParser()

    # Create the directory needed and support files
    report_folder, report_date, report_time = folderOut(directory_name, script_path)

    # Change log path if full path is given for output directory
    if directory_name.startswith('/'):
        # Location of the log file Ghost logs to (to catch SSL errors)
        log_file_path = directory_name + "/logfile.log"
    elif directory_name is not "None":
        # Location of the log file Ghost logs to (to catch SSL errors)
        log_file_path = script_path + "/" + report_folder + "/logfile.log"
    else:
        # Location of the log file Ghost logs to (to catch SSL errors)
        log_file_path = script_path + "/" + report_folder + "/logfile.log"

    # If the user wants to cycle through user agents, return the dictionary of applicable user agents
    if ua_cycle == "None":
        ghost_object = casperCreator(browser_user_agent, timeout_wait)
    else:
        ua_dict = userAgentDefinition(ua_cycle)
        ghost_object = casperCreator(browser_user_agent, timeout_wait)

    # Logging setup
    logging.basicConfig(filename=log_file_path, level=logging.WARNING)
    logger = logging.getLogger('ghost')

    # Define a couple default variables
    extra_info = "None"
    blank_value = "None"
    baseline_request = "Baseline"
    page_length = "None"

    if single_url is not "None":

        # If URL doesn't start with http:// or https://, assume it is http:// and add it to URL
        if single_url.startswith('http://') or single_url.startswith('https://'):
            pass
        else:
            single_url = "http://" + single_url

        # Used for monitoring for blank pages or SSL errors
        content_blank = 0

        web_index = webHeader()
        print "Trying to screenshot " + single_url

        # Create the filename to store each website's picture
        single_url, source_name, picture_name = fileNames(single_url)

        # If a normal single request, then perform the request
        if ua_cycle == "None":
            try:
                page, extra_resources = ghostCapture(ghost_object, single_url, report_folder, picture_name, script_path)

                content_blank, default_creds = backupRequest(page, single_url, source_name, content_blank, script_path, cred_skip)

                # Create the table info for the single URL (screenshot, server headers, etc.)
                web_index = tableMaker(web_index, single_url, default_creds, page, content_blank, log_file_path, blank_value, blank_value, blank_value, source_name, picture_name, page_length)

            # Skip a url if Ctrl-C is hit
            except KeyboardInterrupt:
                print "[*] Skipping: " + single_url
                web_index += """<tr>
                <td><a href=\"{single_given_url}\">{single_given_url}</a></td>
                <td>User Skipped this URL</td>
                </tr>
                """.format(single_given_url=single_url).replace('    ', '')
            # Catch timeout warning
            except screener.TimeoutError:
                print "[*] Hit timeout limit when connecting to: " + single_url
                web_index += """<tr>
                <td><a href=\"{single_timeout_url}\" target=\"_blank\">{single_timeout_url}</a></td>
                <td>Hit timeout limit while attempting screenshot</td>
                </tr>
                """.format(single_timeout_url=single_url)

        # If cycling through user agents, start that process here
        # Create a baseline requst, then loop through the dictionary of user agents, and make requests w/those UAs
        # Then use comparison function.  If UA request content matches baseline content, do nothing.
        # If UA request content is different from baseline, add to report
        else:
            # Setup variables to set file names properly
            original_source = source_name
            original_screenshot = picture_name

            # Create baseline file names
            source_name = source_name + "_baseline.txt"
            picture_name = picture_name + "_baseline.png"
            request_number = 0

            # Iterate through the user agents the user has selected to use, and set ghost to use them
            # Then perform a comparison of the baseline results to the new results.  If different, add to report
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
                        baseline_page, baseline_extra_resources = ghostCapture(ghost_object, single_url, report_folder, picture_name, script_path)
                        
                        # Hack for a bug in Ghost at the moment
                        baseline_page.content = "None"

                        baseline_content_blank, baseline_default_creds = backupRequest(baseline_page, single_url, source_name, content_blank, script_path, cred_skip)
                        extra_info = "This is the baseline request"

                        # Create the table info for the single URL (screenshot, server headers, etc.)
                        web_index = tableMaker(web_index, single_url, baseline_default_creds, baseline_page, baseline_content_blank, log_file_path, blank_value, browser_key, user_agent_value, source_name, picture_name, baseline_request)

                        # Move beyond the baseline
                        request_number = 1

                    else:
                        new_ua_page, new_ua_extra_resources = ghostCapture(ghost_object, single_url, report_folder, picture_name, script_path)

                        # Hack for a bug in Ghost at the moment
                        new_ua_page.content = "None"

                        new_ua_content_blank, new_ua_default_creds = backupRequest(new_ua_page, single_url, source_name, content_blank, script_path, cred_skip)

                        # Function which hashes the original request with the new request and checks to see if they are identical
                        same_or_different, total_length_difference = requestComparison(baseline_page.content, new_ua_page.content, diff_value)

                        # If they are the same, then go on to the next user agent, if they are different, add it to the report
                        if same_or_different:
                            pass
                        else:
                            # Create the table info for the single URL (screenshot, server headers, etc.)
                            web_index = tableMaker(web_index, single_url, baseline_default_creds, baseline_page, baseline_content_blank, log_file_path, blank_value, browser_key, user_agent_value, source_name, picture_name, total_length_difference)
                        total_length_difference = "None"
           
                # Skip a url if Ctrl-C is hit
                except KeyboardInterrupt:
                    print "[*] Skipping: " + single_url
                    web_index += """<tr>
                    <td><a href=\"{single_given_url}\">{single_given_url}</a></td>
                    <td>User Skipped this URL</td>
                    </tr>
                    """.format(single_given_url=single_url).replace('    ', '')
                # Catch timeout warning
                except screener.TimeoutError:
                    print "[*] Hit timeout limit when connecting to: " + single_url
                    web_index += """<tr>
                    <td><a href=\"{single_timeout_url}\" target=\"_blank\">{single_timeout_url}</a></td>
                    <td>Hit timeout limit while attempting screenshot</td>
                    </tr>
                    """.format(single_timeout_url=single_url)

                # Add Random sleep based off of user provided jitter value if requested
                if request_jitter is not "None":
                    sleep_value = random.randint(0,30)
                    sleep_value = sleep_value * .01
                    sleep_value = 1 - sleep_value
                    sleep_value = sleep_value * int(request_jitter)
                    print "[*] Sleeping for " + str(sleep_value) + " seconds..."
                    try:
                        time.sleep(sleep_value)
                    except KeyboardInterrupt:
                        print "[*] User cancelled sleep for this URL!"

        # Open each url in a browser if requested
        if open_urls:
            iceweasel_command = "iceweasel -new-tab " + single_url
            iceweasel_command = iceweasel_command.split()
            p = subprocess.Popen(iceweasel_command)

        # Write out the report for the single URL
        singleReportPage(web_index, script_path)

    else:

        # Create the output directories, open the urlfile, and return all URLs
        url_list, number_urls = logistics(url_filename)

        # Check if user wants random URLs, if so, randomize URLs here
        if request_jitter is not "None":
            random.shuffle(url_list)

        # Add the web "header" to our web page
        web_index = webHeader()
        print "Trying to screenshot " + str(number_urls) + " websites...\n"

        # Create a URL counter to know when to go to a new page
        # Create a page counter to track pages
        url_counter = 0
        page_counter = 1

        # Loop through all URLs and create a screenshot
        for url in url_list:

            # Check for http or https protocol, if not present, assume http
            url = url.strip()
            if url.startswith('http://') or url.startswith('https://'):
                pass
            else:
                url = "http://" + url

            # Used for monitoring for blank pages or SSL errors
            content_blank = 0

            # Create the filename to store each website's picture
            url, source_name, picture_name = fileNames(url)

            # This is the code which opens the specified URL and captures it to a screenshot
            print "Attempting to capture: " + url
            # If not trying to cycle through different user agents, make the web requests as it was originall done
            if ua_cycle == "None":
                try:
                    # Ghost capturing web page
                    page, extra_resources = ghostCapture(ghost_object, url, report_folder, picture_name, script_path)

                    # If EyeWitness receives a no-cache, it can't get the page source, therefore lets
                    # make a backup request get the source
                    content_blank, default_creds = backupRequest(page, url, source_name, content_blank, script_path, cred_skip)

                    web_index = tableMaker(web_index, url, default_creds, page, content_blank, log_file_path, blank_value, blank_value, blank_value, source_name, picture_name, page_length)

                # Skip a url if Ctrl-C is hit
                except KeyboardInterrupt:
                    print "[*] Skipping: " + url
                    web_index += """<tr>
                    <td><a href=\"{single_given_url}\">{single_given_url}</a></td>
                    <td>User Skipped this URL</td>
                    </tr>
                    """.format(single_given_url=url).replace('    ', '')
                # Catch timeout warning
                except screener.TimeoutError:
                    print "[*] Hit timeout limit when connecting to: " + url
                    web_index += """<tr>
                    <td><a href=\"{single_timeout_url}\" target=\"_blank\">{single_timeout_url}</a></td>
                    <td>Hit timeout limit while attempting screenshot</td>
                    </tr>
                    """.format(single_timeout_url=url)

            else:
                # Setup variables to set file names properly
                original_source = source_name
                original_screenshot = picture_name

                # Create baseline file names
                source_name = source_name + "_baseline.txt"
                picture_name = picture_name + "_baseline.png"
                request_number = 0

                # Iterate through the user agents the user has selected to use, and set ghost to use them
                # Then perform a comparison of the baseline results to the new results.  If different, add to report
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
                            baseline_page, baseline_extra_resources = ghostCapture(ghost_object, url, report_folder, picture_name, script_path)
                        
                            # Hack for a bug in Ghost at the moment
                            baseline_page.content = "None"

                            baseline_content_blank, baseline_default_creds = backupRequest(baseline_page, url, source_name, content_blank, script_path, cred_skip)

                            # Create the table info for the single URL (screenshot, server headers, etc.)
                            web_index = tableMaker(web_index, url, baseline_default_creds, baseline_page, baseline_content_blank, log_file_path, blank_value, browser_key, user_agent_value, source_name, picture_name, baseline_request)

                            # Move beyond the baseline
                            request_number = 1

                        else:
                            # Get page with new screenshot/
                            new_ua_page, new_ua_extra_resources = ghostCapture(ghost_object, url, report_folder, picture_name, script_path)
                            new_ua_content_blank, new_ua_default_creds = backupRequest(new_ua_page, url, source_name, content_blank, script_path, cred_skip)

                            # Function which hashes the original request with the new request and checks to see if they are identical
                            same_or_different, l_difference = requestComparison(baseline_page.content, new_ua_page.content, diff_value)

                            # If they are the same, then go on to the next user agent, if they are different, add it to the report
                            if same_or_different:
                                pass
                            else:
                                # Create the table info for the single URL (screenshot, server headers, etc.)
                                web_index = tableMaker(web_index, url, baseline_default_creds, baseline_page, baseline_content_blank, log_file_path, blank_value, browser_key, user_agent_value, source_name, picture_name, l_difference)
                            l_difference = "None"

                    # Skip a url if Ctrl-C is hit
                    except KeyboardInterrupt:
                        print "[*] Skipping: " + url
                        web_index += """<tr>
                        <td><a href=\"{single_given_url}\">{single_given_url}</a></td>
                        <td>User Skipped this URL</td>
                        </tr>
                        """.format(single_given_url=url).replace('    ', '')
                    # Catch timeout warning
                    except screener.TimeoutError:
                        print "[*] Hit timeout limit when connecting to: " + url
                        web_index += """<tr>
                        <td><a href=\"{single_timeout_url}\" target=\"_blank\">{single_timeout_url}</a></td>
                        <td>Hit timeout limit while attempting screenshot</td>
                        </tr>
                        """.format(single_timeout_url=url)

                    # Add Random sleep based off of user provided jitter value if requested
                    if request_jitter is not "None":
                        sleep_value = random.randint(0,30)
                        sleep_value = sleep_value * .01
                        sleep_value = 1 - sleep_value
                        sleep_value = sleep_value * int(request_jitter)
                        print "[*] Sleeping for " + str(sleep_value) + " seconds..."
                        try:
                            time.sleep(sleep_value)
                        except KeyboardInterrupt:
                            print "[*] User cancelled sleep for this URL!"

            # If user wants URL opened in a browser as it runs, do it
            if open_urls:
                iceweasel_command = "iceweasel -new-tab " + url
                iceweasel_command = iceweasel_command.split()
                p = subprocess.Popen(iceweasel_command)

            # Add Random sleep based off of user provided jitter value if requested
            if request_jitter is not "None" and ua_cycle is "None":
                sleep_value = random.randint(0,30)
                sleep_value = sleep_value * .01
                sleep_value = 1 - sleep_value
                sleep_value = sleep_value * int(request_jitter)
                print "[*] Sleeping for " + str(sleep_value) + " seconds..."
                try:
                    time.sleep(sleep_value)
                except KeyboardInterrupt:
                    print "[*] User cancelled sleep for this URL!"

            # Track the number of URLs
            url_counter = url_counter + 1

            # If we hit 100 urls in the counter, finish the page and start a new one
            if url_counter == 25:
                if page_counter == 1:
                    # Close out the html and write it to disk
                    web_index += "</table>\n"
                    with open(script_path + "/" + report_folder + "/report.html", 'w') as f1:
                        f1.write(web_index)

                    # Revert URL counter back to 0, increment the page count to 1
                    # Clear web_index of all values by giving web_index the "header"
                    # of the new html page
                    url_counter = 0
                    page_counter = page_counter + 1
                    web_index = webHeader()
                else:
                    # Write out to the next page
                    web_index += "</table>\n"
                    with open(script_path + "/" + report_folder + "/report_page" + str(page_counter) + ".html", 'w') as page_out:
                        page_out.write(web_index)

                    # Reset the URL counter
                    url_counter = 0
                    page_counter = page_counter + 1
                    web_index = webHeader()

        if page_counter == 1:
            singleReportPage(web_index, script_path)
        else:
            # Write out our extra page
            web_index += "</table>\n"
            with open(script_path + "/" + report_folder + "/report_page" + str(page_counter) + ".html", 'w') as page_out:
                page_out.write(web_index)

            # Create the link structure at the bottom
            link_text = "\n<br>Links: <a href=\"report.html\">Page 1</a> "
            for page in range(2,page_counter+1):
                link_text += "<a href=\"report_page" + str(page) + ".html\">Page " + str(page) + "</a> "
            link_text += "\n</body>\n"
            link_text += "</html>"
        
            # Write out link structure to bottom of report
            with open(script_path + "/" + report_folder + "/report.html", 'a') as report_append:
                report_append.write(link_text)

            # Write out link structure to bottom of extra pages
            for page_footer in range(2,page_counter+1):
                with open(script_path + "/" + report_folder + "/report_page" + str(page_footer) + ".html", 'a') as page_append:
                    page_append.write(link_text)

    os.system('rm ' + log_file_path)
    print "\n[*] Done! Check out the report in the " + report_folder + " folder!"
