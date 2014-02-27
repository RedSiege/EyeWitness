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
import subprocess

def cliParser():
    # Parse the command line options
    #const="7" for timeout
    parser = argparse.ArgumentParser(description="EyeWitness is a tool used to capture screenshots from a list of URLs.")
    parser.add_argument("-f", metavar="Filename", help="File containing URLs to screenshot, each on a new line, NMap XML output, or a .nessus file.")
    parser.add_argument("-t", metavar="Timeout", default="7", help="[Optional] Maximum number of seconds to wait while requesting a web page (Default: 7).")
    parser.add_argument("--open", action='store_true', help="[Optional] Open all URLs in a browser")
    args = parser.parse_args()

    if args.f is None:
        print "Error: You didn't specify a file! I need a file containing URLs!"
        sys.exit()

    if args.t:
        try:
            int(args.t)
        except ValueError:
            args.t = 7

    # Return the file name which contains the URLs
    return args.f, args.t, args.open

def logistics(url_file):

    # Get the date and time, and create output name
    current_date = time.strftime("%m/%d/%Y")
    current_time = time.strftime("%H:%M:%S")
    output_folder_name = current_date.replace("/", "") + "_" + current_time.replace(":", "")

    # Create a folder which stores all snapshots
    # note- os.makedirs
    os.system("mkdir " + output_folder_name)
    os.system("mkdir " + output_folder_name + "/screens")
    os.system("mkdir " + output_folder_name + "/source")

    # Write out the CSS stylesheet
    css_page =  "img {\n"
    css_page += "max-width: 100%;\n"
    css_page += "height: auto;\n"
    css_page += "}\n\n"
    css_page += "#screenshot{\n"
    css_page += "overflow: auto;\n"
    css_page += "max-width: 850px;\n"
    css_page += "max-height: 550px;\n"
    css_page += "}"


    css_file = open(output_folder_name + "/style.css", 'w')
    css_file.write(css_page)
    css_file.close()

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
                                service = ports.find('service').get('name')
                                if int(port) in http_ports or 'http' in service.lower():
                                    protocol = 'http'
                                    if int(port) in https_ports or 'https' in service.lower():
                                        protocol = 'https'
                                    urlBuild = '%s://%s:%s' % (protocol,target,port)
                                    if urlBuild not in urls:
                                        urls.append(urlBuild)
                                        num_urls = num_urls + 1
                            except AttributeError:
                                # This hits when it finds an open port, but isn't able to
                                # Determine the name of the service running on it, so we'll
                                # just pass in this instance
                                pass
            return urls, num_urls, output_folder_name, current_date, current_time

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

            return urls, num_urls, output_folder_name, current_date, current_time

        else:
            print "ERROR: EyeWitness only accepts NMap XML files!"

    except XMLParser.ParseError:

        try:
            # Open the URL file and read all URLs, and reading again to catch total number of websites
            f = open(url_file, 'r')
            all_urls = f.readlines()
            f.close()
            for line in all_urls:
                urls.append(line)
                num_urls = num_urls + 1

            return urls, num_urls, output_folder_name, current_date, current_time

        except IOError:
            print "ERROR: You didn't give me a valid file name! I need a valid file containing URLs!"
            sys.exit()

def titleScreen():
    os.system('clear')
    print "###########################################################################"
    print "#                             EyeWitness v1.0                             #"
    print "###########################################################################\n"

def defaultCreds(page_content):
    # Read in the file containing the web "signatures"
    sig_file = open('signatures.txt', 'r')
    signatures = sig_file.readlines()
    sig_file.close()

    # Loop through and see if there are any matches from the source code EyeWitness obtained
    for sig in signatures:
        # Find the signature(s), split them into their own dict of needed
        # Assign default creds to its own variable
        sig_cred = sig.split('|')
        page_sig = sig_cred[0].split(";")
        cred_info = sig_cred[1]

        # Set our variable to false if the signature was identified.  If it is identified,
        # it will be added later on.  Find total number of "signatures" needed to uniquely identify
        # the web app
        sig_not_found = 0
        signature_range = len(page_sig)

        # This is used if there is more than one "part" of the web page needed to make a signature
        # Delimete the "signature" by ";" before the "|", and then have the creds after the "|"
        for individual_signature in range(0, signature_range):
            if str(page.content).find(page_sig[individual_signature]) is not -1:
                pass
            else:
                sig_not_found = 1

        # If the signature was found, break out of loops and return the creds
        if sig_not_found == 0:
            return cred_info
            break

def webHeader():
    # Start our web page report
    web_index_head =  "<html>\n<head>\n"
    web_index_head += "<link rel=\"stylesheet\" href=\"style.css\" type=\"text/css\"/>"
    web_index_head += "<title>EyeWitness Report</title>\n</head>\n"
    web_index_head += "<body>\n"
    web_index_head += "<center>Report Generated on " + report_date + " at " + report_time
    web_index_head += "<br><table border=\"1\">\n"
    web_index_head += "<tr>\n"
    web_index_head += "<th>Web Request Info</th>\n"
    web_index_head += "<th>Web Screenshot</th>\n"
    web_index_head += "</tr>\n"
    return web_index_head

def fileNames(url_given):
    url_given = url_given.strip()
    pic_name = url_given.replace("http://", "")
    pic_name = pic_name.replace("https://", "")
    pic_name = pic_name.replace("www.", "")
    pic_name = pic_name.replace(":", "")
    pic_name = pic_name.replace("/", "")
    src_name = pic_name + ".txt"
    pic_name = pic_name + ".png"
    return url_given, src_name, pic_name

def htmlEncode(dangerous_data):
    encoded = cgi.escape(dangerous_data, quote=True)
    return encoded
    
if __name__ == "__main__":

    # Print the title header
    titleScreen()

    # Parse command line options and return the filename containing URLS and how long to wait for each website
    url_filename, timeout_wait, open_urls = cliParser()

    # Create the output directories, open the urlfile, and return all URLs
    url_list, number_urls, report_folder, report_date, report_time = logistics(url_filename) 
    
    # Add the web "header" to our web page
    web_index = webHeader()
    print "Trying to screenshot " + str(number_urls) + " websites...\n"

    # Create a URL counter to know when to go to a new page
    # Create a page counter to track pages
    url_counter = 0
    page_counter = 1

    # Loop through all URLs and create a screenshot
    for url in url_list:

        content_blank = 0

        # Create the filename to store each website's picture
        url, source_name, picture_name = fileNames(url)

        # This is the code which opens the specified URL and captures it to a screenshot
        print "Attempting to capture: " + url
        try:
            # Try to get our screenshot and source code of the page
            # Write both out to disk if possible (if we can get one, we can get the other)
            ghost = screener.Ghost(wait_timeout=int(timeout_wait), ignore_ssl_errors=True)
            logger = logging.getLogger('ghost')
            logger.disabled = True
            page, extra_resources = ghost.open(url, auth=('none', 'none'))
            ghost.capture_to(report_folder + "/screens/" + picture_name)

            # If EyeWitness receives a no-cache, it can't get the page source, therefore lets
            # make a backup request get the source
            try:
                if page.content == "None":
                    try:
                        response = urllib2.urlopen(url)
                        page.content = response.read()
                        response.close()
                    except urllib2.HTTPError:
                        page.content = "Sorry, but couldn't get source code for potentially a couple reasons.  If it was Basic Auth, a 50X, or a 40X error, EyeWitness won't return source code.  Couldn't get source from " + url + "."
                # check if page is blank
                source = open(report_folder + "/source/" + source_name, 'w')
                source.write(page.content)
                source.close()
                default_creds = defaultCreds(page.content)
            except AttributeError:
                print "[*] ERROR: Web page possibly blank or SSL error!"
                content_blank = 1
                default_creds = None

            # Continue adding to the table assuming that we were able to capture the screenshot
            # Only add elements if they exist
            web_index += "<tr>\n"           
            web_index += "<td><div style=\"display: inline-block; width: 300px; word-wrap: break-word\">"

            # Add URL to table data at the top
            web_index += "<a href=\"" + url + "\" target=\"_blank\">" + url + "</a><br>"

            if default_creds is not None:
                web_index += "<br><b>Default credentials:</b> " + default_creds + "<br>"

            try:
                for key, value in page.headers.items():
                    web_index += "\n<br><b> " + htmlEncode(key.replace("u\'", "")) + ":</b> " + htmlEncode(value)

            except AttributeError:
                web_index += "\n<br><br>Potential blank page or SSL issue with <a href=\"" + url + "\" target=\"_blank\">" + url + "</a>."

            if content_blank == 1:
                web_index += "\n<br></td>"
                web_index += "\n<td><div style=\"display: inline-block; width: 850px;\">Page Blank or SSL Issues</div></td>\n"
                web_index += "</tr>\n"
                content_blank = 0

            else:
                web_index += "\n<br><a href=\"source/" + source_name + "\" target=\"_blank\">Source Code</a></div></td>"
                web_index += "\n<td><div id=\"screenshot\" style=\"display: inline-block; width: 850px; height 400px; overflow: scroll;\"><a href=\"screens/" + picture_name + "\" target=\"_blank\"><img src=\"screens/" + picture_name + "\" height=\"400\"></a></div></td>\n"
                web_index += "</tr>\n"

            # If user wants URL opened in a browser as it runs, do it
            if open_urls:
                iceweasel_command = "iceweasel -new-tab " + url
                iceweasel_command = iceweasel_command.split()
                p = subprocess.Popen(iceweasel_command)
            
        # Skip a url if Ctrl-C is hit
        except KeyboardInterrupt:
            print "[*] Skipping: " + url
            web_index += "<tr>\n"
            web_index += "<td>" + url + "</td>\n"
            web_index += "<td>User Skipped this URL</td>\n"
            web_index += "</tr>\n"
        # Catch timeout warning
        except screener.TimeoutError:
            print "[*] Hit timeout limit when connecting to: " + url
            web_index += "<tr>\n"
            web_index += "<td>" + url + "</td>\n"
            web_index += "<td>Hit timeout limit while attempting screenshot</td>\n"
            web_index += "</tr>\n"

            # If user wants URL opened in a browser as it runs, do it
            if open_urls:
                iceweasel_command = "iceweasel -new-tab " + url
                iceweasel_command = iceweasel_command.split()
                p = subprocess.Popen(iceweasel_command)

        # Track the number of URLs
        url_counter = url_counter + 1

        # If we hit 100 urls in the counter, finish the page and start a new one
        if url_counter == 100:
            if page_counter == 1:
                # Close out the html and write it to disk
                web_index += "</table>\n"
                fo = open(report_folder + "/report.html", 'w')
                fo.write(web_index)
                fo.close()
                # Revert URL counter back to 0, increment the page count to 1
                # Clear web_index of all values by giving web_index the "header"
                # of the new html page
                url_counter = 0
                page_counter = page_counter + 1
                web_index = webHeader()
            else:
                # Write out to the next page
                web_index += "</table>\n"
                page_out = open(report_folder + "/report_page" + str(page_counter) + ".html", 'w')
                page_out.write(web_index)
                page_out.close()
                # Reset the URL counter
                url_counter = 0
                page_counter = page_counter + 1
                web_index = webHeader()

    if page_counter == 1:
        # Close out the html and write it to disk
        web_index += "</table>\n"
        web_index += "</body>\n"
        web_index += "</html>"
        fo = open(report_folder + "/report.html", 'w')
        fo.write(web_index)
        fo.close()
    else:
        # Write out our extra page
        web_index += "</table>\n"
        page_out = open(report_folder + "/report_page" + str(page_counter) + ".html", 'w')
        page_out.write(web_index)
        page_out.close()

        # Create the link structure at the bottom
        link_text = "\n<br>Links: <a href=\"report.html\">Page 1</a> "
        for page in range(2,page_counter+1):
            link_text += "<a href=\"report_page" + str(page) + ".html\">Page " + str(page) + "</a> "
        link_text += "\n</body>\n"
        link_text += "</html>"
        
        # Write out link structure to bottom of report
        report_append = open(report_folder + "/report.html", 'a')
        report_append.write(link_text)
        report_append.close()

        # Write out link structure to bottom of extra pages
        for page_footer in range(2,page_counter+1):
            page_append = open(report_folder + "/report_page" + str(page_footer) + ".html", 'a')
            page_append.write(link_text)
            page_append.close()

    print "\n[*] Done! Check out the report in the " + report_folder + " folder!"
