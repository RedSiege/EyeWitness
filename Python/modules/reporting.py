import os
import sys
import urllib.parse

try:
    from fuzzywuzzy import fuzz
except ImportError:
    print('[*] fuzzywuzzy not found.')
    print('[*] Please run the script in the setup directory!')
    sys.exit()


def process_group(
        data, group, toc, toc_table, page_num, section,
        sectionid, html):
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
    group_data = sorted([x for x in data if x.category == group], key=lambda k: str(k.page_title))

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
        temp = sorted(temp, key=lambda k: k.page_title)
        grouped_elements.extend(temp)
        group_data = [x for x in group_data if fuzz.token_sort_ratio(
            test_element.page_title, x.page_title) < 70]

    grouped_elements.extend(unknowns)
    toc_table += ("<tr><td>{0}</td><td>{1}</td>").format(section,
                                                         str(len(grouped_elements)))
    return grouped_elements, toc, toc_table, html



def sort_data_and_write(cli_parsed, data):
    """Writes out reports for HTTP objects

    Args:
        cli_parsed (TYPE): CLI Options
        data (TYPE): Full set of data
    """
    # We'll be using this number for our table of contents
    total_results = len(data)
    categories = [('highval', 'High Value Targets', 'highval'),
                  ('dirlist', 'Directory Listings', 'dirlist'),
                  ('cms', 'Content Management System (CMS)', 'cms'),
                  ('idrac', 'IDRAC/ILo/Management Interfaces', 'idrac'),
                  ('nas', 'Network Attached Storage (NAS)', 'nas'),
                  ('comms', 'Communications', 'comms'),
                  ('devops', 'Development Operations', 'devops'),
                  ('secops', 'Security Operations', 'secops'),
                  ('appops', 'Application Operations', 'appops'),
                  ('dataops', 'Data Operations', 'dataops'),
                  ('netdev', 'Network Devices', 'netdev'),
                  ('voip', 'Voice/Video over IP (VoIP)', 'voip'),
                  ('printer', 'Printers', 'printer'),
                  ('infrastructure', 'Infrastructure', 'infrastructure'),
                  (None, 'Uncategorized', 'uncat'),
                  ('construction', 'Under Construction', 'construction'),
                  ('crap', 'Splash Pages', 'crap'),
                  ('empty', 'No Significant Content', 'empty'),
                  ('unauth', '401/403 Unauthorized', 'unauth'),
                  ('notfound', '404 Not Found', 'notfound'),
                  ('successfulLogin', 'Successful Logins', 'successfulLogin'),
                  ('identifiedLogin', 'Identified Logins', 'identifiedLogin'),
                  ('redirector', 'Redirecting Pages', 'redirector'),
                  ('badhost', 'Invalid Hostname', 'badhost'),
                  ('inerror', 'Internal Error', 'inerror'),
                  ('badreq', 'Bad Request', 'badreq'),
                  ('badgw', 'Bad Gateway', 'badgw'),
                  ('serviceunavailable', 'Service Unavailable', 'serviceunavailable'),
                  ]
    if total_results == 0:
        return
    # Initialize stuff we need
    pages = []
    toc = create_report_toc_head(cli_parsed.date, cli_parsed.time)
    toc_table = "<table class=\"table\">"
    web_index_head = create_web_index_head(cli_parsed.date, cli_parsed.time)
    table_head = create_table_head()
    counter = 1
    csv_request_data = "Protocol,Port,Domain,Request Status,Screenshot Path, Source Path"

    # Generate and write json log of requests
    for json_request in data:
        url = urllib.parse.urlparse(json_request._remote_system)

        # Determine protocol
        csv_request_data += "\n" + url.scheme + ","
        if url.port is not None:
            csv_request_data += str(url.port) + ","
        elif url.scheme == 'http':
            csv_request_data += "80,"
        elif url.scheme == 'https':
            csv_request_data += "443,"
        try:
            csv_request_data += url.hostname + ","
        except TypeError:
            print("Error when accessing a target's hostname (it's not existent)")
            print("Possible bad url (improperly formatted) in the URL list.")
            print("Fix your list and re-try. Killing EyeWitness....")
            sys.exit(1)
        if json_request._error_state == None:
            csv_request_data += "Successful,"
        else:
            csv_request_data += json_request._error_state + ","
        csv_request_data += json_request._screenshot_path + ","
        csv_request_data += json_request._source_path

    with open(os.path.join(cli_parsed.d, 'Requests.csv'), 'a') as f:
        f.write(csv_request_data)

    # Pre-filter error entries
    def key_lambda(k):
        if k.error_state is None:
            k.error_state = str(k.error_state)
        if k.page_title is None:
            k.page_title = str(k.page_title)
        return (k.error_state, k.page_title)
    errors = sorted([x for x in data if (x is not None) and (x.error_state is not None)],
                     key=key_lambda)
    data[:] = [x for x in data if x.error_state is None]
    data = sorted(data, key=lambda k: str(k.page_title))
    html = u""
    # Loop over our categories and populate HTML
    for cat in categories:
        grouped, toc, toc_table, html = process_group(
            data, cat[0], toc, toc_table, len(pages), cat[1], cat[2], html)
        if len(grouped) > 0:
            html += table_head
        pcount = 0
        for obj in grouped:
            pcount += 1
            html += obj.create_table_html()
            if (counter % cli_parsed.results == 0) or (counter == (total_results) -1):
                html = (web_index_head + "EW_REPLACEME" + html +
                        "</table><br>")
                pages.append(html)
                html = u""
                if pcount < len(grouped):
                    html += table_head
            counter += 1
        if len(grouped) > 0 and counter - 1 % cli_parsed.results != 0:
            html += "</table><br>"

    # Add our errors here (at the very very end)
    if len(errors) > 0:
        html += '<h2>Errors</h2>'
        html += table_head
        for obj in errors:
            html += obj.create_table_html()
            if (counter % cli_parsed.results == 0) or (counter == (total_results)):
                html = (web_index_head + "EW_REPLACEME" + html +
                        "</table><br>")
                pages.append(html)
                html = u"" + table_head
            counter += 1

    # Close out any stuff thats hanging
    toc += "</ul>"
    toc_table += "<tr><td>Errors</td><td>{0}</td></tr>".format(
        str(len(errors)))
    toc_table += "<tr><th>Total</th><td>{0}</td></tr>".format(total_results)
    toc_table += "</table>"

    if (html != u"") and (counter - total_results != 0):
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
        skip_last_dummy = False
        # Generate our header/footer data here
        for i in range(2, num_pages):
            badd_page = "</center>EW_REPLACEME<table border=\"1\">\n        <tr>\n        <th>Web Request Info</th>\n        <th>Web Screenshot</th>\n        </tr></table><br>"
            if badd_page in pages[i-1]:
                skip_last_dummy = True
                pass
            else:
                bottom_text += ("<a href=\"report_page{0}.html\"> Page {0}</a>").format(str(i))
        bottom_text += "</center>\n"
        top_text = bottom_text
        # Generate our next/previous page buttons
        if skip_last_dummy:
            amount = len(pages) - 1
        else:
            amount = len(pages)
        for i in range(0, amount):
            headfoot = "<h3>Page {0}</h3>".format(str(i+1))
            headfoot += "<center>"
            if i == 0:
                headfoot += ("<a href=\"report_page2.html\" id=\"next\"> Next Page "
                             "</a></center>")
            elif i == amount - 1:
                if i == 1:
                    headfoot += ("<a href=\"report.html\" id=\"previous\"> Previous Page "
                                 "</a></center>")
                else:
                    headfoot += ("<a href=\"report_page{0}.html\" id=\"previous\"> Previous Page "
                                 "</a></center>").format(str(i))
            elif i == 1:
                headfoot += ("<a href=\"report.html\" id=\"previous\">Previous Page</a>&nbsp"
                             "<a href=\"report_page{0}.html\" id=\"next\"> Next Page"
                             "</a></center>").format(str(i+2))
            else:
                headfoot += ("<a href=\"report_page{0}.html\" id=\"previous\">Previous Page</a>"
                             "&nbsp<a href=\"report_page{1}.html\" id=\"next\"> Next Page"
                             "</a></center>").format(str(i), str(i+2))
            # Finalize our pages by replacing placeholder stuff and writing out
            # the headers/footers
            pages[i] = pages[i].replace(
                'EW_REPLACEME', headfoot + top_text) + bottom_text + '<br>' + headfoot + '</body></html>'

        # Write out our report to disk!
        if len(pages) == 0:
            return
        with open(os.path.join(cli_parsed.d, 'report.html'), 'a') as f:
            f.write(toc)
            f.write(pages[0])
        write_out = len(pages)
        for i in range(2, write_out + 1):
            bad_page = "<table border=\"1\">\n        <tr>\n        <th>Web Request Info</th>\n        <th>Web Screenshot</th>\n        </tr></table><br>\n<center><br><a "
            badd_page2 = "</center>EW_REPLACEME<table border=\"1\">\n        <tr>\n        <th>Web Request Info</th>\n        <th>Web Screenshot</th>\n        </tr></table><br>"
            if (bad_page in pages[i-1]) or (badd_page2 in pages[i-1]):
                pass
            else:
                with open(os.path.join(cli_parsed.d, 'report_page{0}.html'.format(str(i))), 'w') as f:
                    f.write(pages[i - 1])


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
        <link rel=\"stylesheet\" href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css\" type=\"text/css\"/>
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

        document.onkeydown = function(event){{
            event = event || window.event;
            switch (event.keyCode){{
                case 37:
                    leftArrow();
                    break;
                case 39:
                    rightArrow();
                    break;
            }}
        }};
                
        function leftArrow(){{
            $('#previous')[0].click();
        }};

        function rightArrow(){{
            $('#next')[0].click();
        }};

        </script>
        </head>
        <body>
        <center>
        <center>Report Generated on {0} at {1}</center>""").format(date, time)


def search_index_head():
    return ("""<html>
        <head>
        <link rel=\"stylesheet\" href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css\" type=\"text/css\"/>
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
        """)


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


def search_report(cli_parsed, data, search_term):
    pages = []
    web_index_head = search_index_head()
    table_head = create_table_head()
    counter = 1

    data[:] = [x for x in data if x.error_state is None]
    data = sorted(data, key=lambda k: k.page_title)
    html = u""

    # Add our errors here (at the very very end)
    html += '<h2>Results for {0}</h2>'.format(search_term)
    html += table_head
    for obj in data:
        html += obj.create_table_html()
        if counter % cli_parsed.results == 0:
            html = (web_index_head + "EW_REPLACEME" + html +
                    "</table><br>")
            pages.append(html)
            html = u"" + table_head
        counter += 1

    if html != u"":
        html = (web_index_head + html + "</table><br>")
        pages.append(html)

    if len(pages) == 1:
        with open(os.path.join(cli_parsed.d, 'search.html'), 'a') as f:
            f.write(pages[0].replace('EW_REPLACEME', ''))
            f.write("</body>\n</html>")
    else:
        num_pages = len(pages) + 1
        bottom_text = "\n<center><br>"
        bottom_text += ("<a href=\"search.html\"> Page 1</a>")
        # Generate our header/footer data here
        for i in range(2, num_pages):
            bottom_text += ("<a href=\"search_page{0}.html\"> Page {0}</a>").format(
                str(i))
        bottom_text += "</center>\n"
        top_text = bottom_text
        # Generate our next/previous page buttons
        for i in range(0, len(pages)):
            headfoot = "<center>"
            if i == 0:
                headfoot += ("<a href=\"search_page2.html\"> Next Page "
                             "</a></center>")
            elif i == len(pages) - 1:
                if i == 1:
                    headfoot += ("<a href=\"search.html\"> Previous Page "
                                 "</a></center>")
                else:
                    headfoot += ("<a href=\"search_page{0}.html\"> Previous Page "
                                 "</a></center>").format(str(i))
            elif i == 1:
                headfoot += ("<a href=\"search.html\">Previous Page</a>&nbsp"
                             "<a href=\"search_page{0}.html\"> Next Page"
                             "</a></center>").format(str(i+2))
            else:
                headfoot += ("<a href=\"search_page{0}.html\">Previous Page</a>"
                             "&nbsp<a href=\"search_page{1}.html\"> Next Page"
                             "</a></center>").format(str(i), str(i+2))
            # Finalize our pages by replacing placeholder stuff and writing out
            # the headers/footers
            pages[i] = pages[i].replace(
                'EW_REPLACEME', headfoot + top_text) + bottom_text + '<br>' + headfoot + '</body></html>'

        # Write out our report to disk!
        if len(pages) == 0:
            return
        with open(os.path.join(cli_parsed.d, 'search.html'), 'a') as f:
            try:
                f.write(pages[0])
            except UnicodeEncodeError:
                f.write(pages[0].encode('utf-8'))
        for i in range(2, len(pages) + 1):
            with open(os.path.join(cli_parsed.d, 'search_page{0}.html'.format(str(i))), 'w') as f:
                try:
                    f.write(pages[i - 1])
                except UnicodeEncodeError:
                    f.write(pages[i - 1].encode('utf-8'))
