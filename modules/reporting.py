# -*- coding: utf-8 -*-
import cgi
import os
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from modules.helpers import default_creds_category

try:
    from fuzzywuzzy import fuzz
except ImportError:
    print '[*] fuzzywuzzy not found.'
    print '[*] Please run the script in the setup directory!'
    sys.exit()


def process_group(
        data, group, section, sectionid, html):
    """Retreives a group from the full data, and creates toc stuff

    Args:
        data (List): Full set of data containing all hosts
        group (String): String representing group to process
        toc (String): HTML for Table of Contents
        toc_table (String): HTML for Table in ToC
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
    if not group_data:
        return grouped_elements, html

    html += "<h2 id=\"{0}\">{1}</h2>".format(sectionid, section)
    unknowns = [x for x in group_data if x.page_title == 'Unknown']
    group_data = [x for x in group_data if x.page_title != 'Unknown']
    while group_data:
        test_element = group_data.pop(0)
        temp = [x for x in group_data if fuzz.token_sort_ratio(
            test_element.page_title, x.page_title) >= 70]
        temp.append(test_element)
        temp = sorted(temp, key=lambda (k): k.page_title)
        grouped_elements.extend(temp)
        group_data = [x for x in group_data if fuzz.token_sort_ratio(
            test_element.page_title, x.page_title) < 70]

    grouped_elements.extend(unknowns)
    return grouped_elements, html


def write_vnc_rdp_data(cli_parsed, data):
    """Writes the reports for VNC and RDP hosts

    Args:
        cli_parsed (ArgumentParser): CLI Options
        data (TYPE): Full set of VNC/RDP data
    """
    vncstuff = sorted([x for x in data if x.proto == 'vnc'],
                      key=lambda v: v.error_state)
    rdpstuff = sorted([x for x in data if x.proto == 'rdp'],
                      key=lambda v: v.error_state)

    for x in [x for x in [vncstuff, rdpstuff] if len(x) > 0]:
        if not x:
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
    # write dependencies
    write_report_deps(cli_parsed)
    table_data = []
    category_table = ''
    footer_script = ''
    # We'll be using this number for our table of contents
    total_results = len(data)
    categories = [('highval', 'High Value Targets', 'highval'),
                  ('dirlist', 'Directory Listings', 'dirlist'),
                  (None, 'Uncategorized', 'uncat'),
                  ('cms', 'Content Management System', 'cms'),
                  ('idrac', 'IDRAC or ILo Management Interfaces', 'idrac'),
                  ('nas', 'Network Attached Storage', 'nas'),
                  ('construction', 'Under Construction', 'construction'),
                  ('netdev', 'Network Devices', 'netdev'),
                  ('voip', 'Voice or Video over IP', 'voip'),
                  ('unauth', '401 or 403 Unauthorized', 'unauth'),
                  ('notfound', '404 Not Found', 'notfound'),
                  ('crap', 'Splash Pages', 'crap'),
                  ('printer', 'Printers', 'printer'),
                  ('successfulLogin', 'Successful Logins', 'successfulLogin'),
                  ('identifiedLogin', 'Identified Logins', 'identifiedLogin'),
                  ('infrastructure', 'Infrastructure', 'infrastructure'),
                  ('redirector', 'Redirecting Pages', 'redirector'),
                  ('badhost', 'Invalid Hostname', 'badhost'),
                  ('inerror', 'Internal Error', 'inerror'),
                  ('badreq', 'Bad Request', 'badreq'),
                  ('serviceunavailable', 'Service Unavailable', 'serviceunavailable'),
                 ]
    if total_results == 0:
        return
    # Create the header HTML code
    html_report_output = create_web_index_head(cli_parsed.date, cli_parsed.time)

    # Pre-filter error entries
    errors = sorted([x for x in data if x.error_state is not None],
                    key=lambda (k): (k.error_state, k.page_title))
    data[:] = [x for x in data if x.error_state is None]
    data = sorted(data, key=lambda (k): k.page_title)
    html = u""
    # Loop over our categories and populate HTML
    for cat in categories:
        grouped, html = process_group(
            data, cat[0], cat[1], cat[2], html)
        if grouped:
            cat_key = grouped[0]._category

            # Generate script code for the footer
            footer_script += '\n\t\t\t$(\'#' + cat[1].replace(' ', '-') + '-table\').DataTable( {\n'
            footer_script += """\t\t\t\t\'searching\': true,
                \'paging\': true,
                \'info\': true,
                \'stateSave\': true,
                \'autoWidth\': false,
                \'columnDefs\': [
                    { \'width\': \'30%\', \'targets\': 0 },
                    { \'width\': \'70%\', \'targets\': 1 }
                ]
            } );"""

            # build out link structure for top of report
            if cat[0] == cat_key:
                html_report_output += '\n\t\t\t\t<a href=\"#' + cat[1].replace(' ', '-') + '-header\">' + cat[1] + '</a><br />'
        
            # seems out of order, but I'm going to build out the html for each category here
            # Easiest rather than adding another loop. HTML will be reassembled in the proper order
            # further down in this function
            category_table += '\n\t\t\t<table id=\"' + cat[1].replace(' ', '-') + '-table\" class=\"table table-sm\" width=\"100%\">'
            category_table += '\n\t\t\t\t<h3 id=\"' + cat[1].replace(' ', '-') + '-header\" class=\"text-center\">' + cat[1] + '</h3>'
            category_table += '\n\t\t\t\t<thead>'
            category_table += '\n\t\t\t\t\t<tr>'
            category_table += '\n\t\t\t\t\t\t<th>Request Information</th>'
            category_table += '\n\t\t\t\t\t\t<th>Screenshot</th>'
            category_table += '\n\t\t\t\t\t</tr>'
            category_table += '\n\t\t\t\t</thead>\n'
            category_table += '\n\t\t\t\t<tbody>'
            for website in grouped:
                category_table += '\n\t\t\t\t\t<tr>'
                category_table += '\n\t\t\t\t\t\t<td>'
                category_table += '\n\t\t\t\t\t\t\t<a href=\"' + website._remote_system + '\">' + website._remote_system + '</a><br />'
                category_table += '\n\t\t\t\t\t\t\t<b>Resolved to:</b>' + website._resolved + '<br />'
                category_table += '\n\t\t\t\t\t\t\t<b>Page Title:</b>' + sanitize(website.page_title) + '<br />'
                for header, header_value in website.headers.iteritems():
                    category_table += '\n\t\t\t\t\t\t\t<b>' + sanitize(header) + ':</b>' + sanitize(header_value) + '<br />'
                category_table += '\n\t\t\t\t\t\t\t<a href=\"' + website._source_path.split('/')[-2] + '/' + website._source_path.split('/')[-1] + '\">Source Code</a><br /><br />'
                if website.default_creds is not None:
                    category_table += '\n\t\t\t\t\t\t\t<b>Default Creds:</b> ' + website.default_creds
                category_table += '\n\t\t\t\t\t\t</td>'
                category_table += '\n\t\t\t\t\t\t<td>'
                category_table += '\n\t\t\t\t\t\t\t<a href=\"' + website._screenshot_path.split('/')[-2] + '/' + website._screenshot_path.split('/')[-1] + '\"><img src=\"' + website._screenshot_path.split('/')[-2] + '/' + website._screenshot_path.split('/')[-1] + '\" height=\"100%\" width=\"100%\"></a>'
                category_table += '\n\t\t\t\t\t\t</td>'
                category_table += '\n\t\t\t\t\t</tr>'

            # End the table
            category_table += '\n\t\t\t\t</tbody>'
            category_table += '\n\t\t\t</table><br><br><hr align="center" color="#CC0000" width="75%"><br><br>\n'

    # Check if errors exist, if so, add to the end of TOC
    if errors:
        html_report_output += '\n\t\t\t\t<a href=\"#error-header">Errors</a><br />'
        category_table += '\n\t\t\t<table id=\"error-table\" class=\"table table-sm\" width=\"100%\">'
        category_table += '\n\t\t\t\t<h3 id=\"error-header\" class=\"text-center\">' + cat[1] + '</h3>'
        category_table += '\n\t\t\t\t<thead>'
        category_table += '\n\t\t\t\t\t<tr>'
        category_table += '\n\t\t\t\t\t\t<th>Request Information</th>'
        category_table += '\n\t\t\t\t\t\t<th>Error</th>'
        category_table += '\n\t\t\t\t\t</tr>'
        category_table += '\n\t\t\t\t</thead>\n'
        category_table += '\n\t\t\t\t<tbody>'
        for err_website in errors:
            category_table += '\n\t\t\t\t\t<tr>'
            category_table += '\n\t\t\t\t\t\t<td>'
            category_table += '\n\t\t\t\t\t\t\t<a href=\"' + err_website._remote_system + '\">' + err_website._remote_system + '</a><br />'
            category_table += '\n\t\t\t\t\t\t\t<b>Resolved to:</b>' + err_website._resolved + '<br />'
            category_table += '\n\t\t\t\t\t\t\t<b>Page Title:</b>' + sanitize(err_website._page_title).encode('utf-8') + '<br />'
            if type(err_website.headers) is not str:
                for header, header_value in err_website.headers.iteritems():
                    category_table += '\n\t\t\t\t\t\t\t<b>' + sanitize(header) + ':</b>' + sanitize(header_value) + '<br />'
            category_table += '\n\t\t\t\t\t\t</td>'
            category_table += '\n\t\t\t\t\t\t<td>'
            category_table += '\n\t\t\t\t\t\t\t' + sanitize(err_website._page_title)
            category_table += '\n\t\t\t\t\t\t</td>'
            category_table += '\n\t\t\t\t\t</tr>'

        # End the table
        category_table += '\n\t\t\t\t</tbody>'
        category_table += '\n\t\t\t</table>'

        footer_script += '\n\t\t\t$(\'#error-table\').DataTable( {\n'
        footer_script += """\t\t\t\t\'searching\': true,
                \'paging\': true,
                \'info\': true,
                \'stateSave\': true,
                \'autoWidth\': false,
                \'columnDefs\': [
                    { \'width\': \'30%\', \'targets\': 0 },
                    { \'width\': \'70%\', \'targets\': 1 }
                ]
            } );"""

        # Add error table to the end of the category table

    # Close the div class for the table of contents
    html_report_output += '\n\t\t\t</div>'

    # Reassemble html here, this takes the HTML code from the for loop above
    # and places it in the middle of the report
    # Then finish out report HTML
    html_report_output += category_table
    html_report_output += '\n\t\t</div><br />'
    html_report_output += '\n\t\t<script type=\"text/javascript\" src=\"jquery-3.2.1.min.js\"></script>'
    html_report_output += '\n\t\t<script type=\"text/javascript\" src=\"bootstrap.min.js\"></script>'
    html_report_output += '\n\t\t<script type=\"text/javascript\" src=\"jquery.dataTables.min.js\"></script>'
    html_report_output += '\n\t\t<script type=\"text/javascript\" src=\"dataTables.bootstrap4.min.js\"></script>'
    html_report_output += '\n\t\t<script>'
    html_report_output += footer_script
    html_report_output += """\n\t\t</script>
    </body>
</html>"""

    # Write out our report to disk!
    with open(os.path.join(cli_parsed.d, 'report.html'), 'a') as f:
        f.write(html_report_output)

def create_web_index_head(date, time):
    """Creates the header for a http report

    Args:
        date (String): Date of report start
        time (String): Time of report start

    Returns:
        String: HTTP Report Start html
    """
    ret_val = """<html>
    <head>
        <title>EyeWitness Report</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link rel="stylesheet" href="dataTables.bootstrap4.min.css">
        <link rel="stylesheet" href="bootstrap.min.css">
        <style>
            table.dataTable tbody td {
                word-break: break-all;
                vertical-align: top;
            }
        </style>
    </head>
    <body>
        <div class="container=fluid">
            <div class="text-center" style="padding: 20px;">
                <h2>Table of Contents</h2>"""
    ret_val += ('\n\t\t\t\t<center>Report Generated on ' + date + ' at ' + time + '</center>')
    return ret_val


def search_index_head():
    return """<html>
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
        """


def create_table_head():
    return """<table border=\"1\">
        <tr>
        <th>Web Request Info</th>
        <th>Web Screenshot</th>
        </tr>"""


def vnc_rdp_table_head():
    return """<table border=\"1\" align=\"center\">
    <tr>
    <th>IP / Screenshot</th>
    </tr>"""


def vnc_rdp_header(date, time):
    web_index_head = ("""<html>
    <head>
    <link rel=\"stylesheet\" href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css\" type=\"text/css\"/>
    <title>EyeWitness Report</title>
    </head>
    <body>
    <center>Report Generated on {0} at {1}</center>
    <br>""").format(date, time)
    return web_index_head


def sanitize(data):
	if data is not None:
	    return cgi.escape(data.decode('utf-8', errors='replace'), quote=True)
	else:
		return "No Data Captured"


def search_report(cli_parsed, data, search_term):
    pages = []
    web_index_head = search_index_head()
    table_head = create_table_head()
    counter = 1

    data[:] = [x for x in data if x.error_state is None]
    data = sorted(data, key=lambda (k): k.page_title)
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
        if not pages:
            return
        with open(os.path.join(cli_parsed.d, 'search.html'), 'a') as f:
            f.write(pages[0])
        for i in range(2, len(pages) + 1):
            with open(os.path.join(cli_parsed.d, 'search_page{0}.html'.format(str(i))), 'w') as f:
                f.write(pages[i - 1])

def write_report_deps(cmd_line_obj):
    # write out css and js supporting files
    rel_path = os.path.abspath(__file__).split('/')[1:-2]
    dep_dir = ''
    for file_path in rel_path:
        dep_dir += '/' + file_path
    dep_dir += '/bin/'

    with open(dep_dir + "dataTables.bootstrap4.min.js", 'r') as dtwut:
        file1 = dtwut.read()
        with open(cmd_line_obj.d + "/dataTables.bootstrap4.min.js", 'w') as dtwut_out:
            dtwut_out.write(file1)
    with open(dep_dir + "jquery.dataTables.min.js", 'r') as dtbootjs:
        file2 = dtbootjs.read()
        with open(cmd_line_obj.d + "/jquery.dataTables.min.js", 'w') as jqdtjs:
            jqdtjs.write(file2)
    with open(dep_dir + "jquery-3.2.1.min.js", 'r') as jquery1124js:
        file3 = jquery1124js.read()
        with open(cmd_line_obj.d + "/jquery-3.2.1.min.js", 'w') as jquery1124out:
            jquery1124out.write(file3)
    with open(dep_dir + "bootstrap.min.js", 'r') as bootstrpmin_rd:
        file4 = bootstrpmin_rd.read()
        with open(cmd_line_obj.d + "/bootstrap.min.js", 'w') as bootstrpmin_out:
            bootstrpmin_out.write(file4)
    with open(dep_dir + "bootstrap.min.css", 'r') as bootstrp_rd:
        file5 = bootstrp_rd.read()
        with open(cmd_line_obj.d + "/bootstrap.min.css", 'w') as bootstrp_out:
            bootstrp_out.write(file5)
    with open(dep_dir + "dataTables.bootstrap4.min.css", 'r') as bootstrpdt_rd:
        file6 = bootstrpdt_rd.read()
        with open(cmd_line_obj.d + "/dataTables.bootstrap4.min.css", 'w') as bootstrpdt_out:
            bootstrpdt_out.write(file6)
    return
