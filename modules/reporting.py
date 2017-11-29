import os
import sys

try:
    from fuzzywuzzy import fuzz
except ImportError:
    print '[*] fuzzywuzzy not found.'
    print '[*] Please run the script in the setup directory!'
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

    grouped_elements.extend(unknowns)
    toc_table += ("<tr><td>{0}</td><td>{1}</td>").format(section,
                                                         str(len(grouped_elements)))
    return grouped_elements, toc, toc_table, html


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
    # write dependencies
    write_report_deps(cli_parsed)
    # We'll be using this number for our table of contents
    total_results = len(data)
    categories = [('highval', 'High Value Targets', 'highval'),
                  ('dirlist', 'Directory Listings', 'dirlist'),
                  (None, 'Uncategorized', 'uncat'),
                  ('cms', 'Content Management System (CMS)', 'cms'),
                  ('idrac', 'IDRAC/ILo/Management Interfaces', 'idrac'),
                  ('nas', 'Network Attached Storage (NAS)', 'nas'),
                  ('construction', 'Under Construction', 'construction'),
                  ('netdev', 'Network Devices', 'netdev'),
                  ('voip', 'Voice/Video over IP (VoIP)', 'voip'),
                  ('unauth', '401/403 Unauthorized', 'unauth'),
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
    # Initialize stuff we need
    pages = []
    toc = create_report_toc_head(cli_parsed.date, cli_parsed.time)
    toc_table = "<table class=\"table\">"
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
        pcount = 0
        for obj in grouped:
            pcount += 1
            html += obj.create_table_html()
            if counter % cli_parsed.results == 0:
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
            if counter % cli_parsed.results == 0:
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
        for i in range(2, len(pages) + 1):
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
        <title>EyeWitness Report</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <!-- DataTables and Bootstrap CSS -->
        <link rel="stylesheet" href="bootstrap.min.css">
        <link rel="stylesheet" href="bootstrap.css">
        <link rel="stylesheet" href="dataTables.bootstrap4.min.css">
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


def vnc_rdp_table_head():
    return ("""<table border=\"1\" align=\"center\">
    <tr>
    <th>IP / Screenshot</th>
    </tr>""")


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
        if len(pages) == 0:
            return
        with open(os.path.join(cli_parsed.d, 'search.html'), 'a') as f:
            f.write(pages[0])
        for i in range(2, len(pages) + 1):
            with open(os.path.join(cli_parsed.d, 'search_page{0}.html'.format(str(i))), 'w') as f:
                f.write(pages[i - 1])

def write_report_deps(cmd_line_obj):
    bootstrap_min = """/*!
    * Bootstrap v4.0.0-alpha.6 (https://getbootstrap.com)
    * Copyright 2011-2017 The Bootstrap Authors
    * Copyright 2011-2017 Twitter, Inc.
    * Licensed under MIT (https://github.com/twbs/bootstrap/blob/master/LICENSE)
    *//*! normalize.css v5.0.0 | MIT License | github.com/necolas/normalize.css */html{font-family:sans-serif;line-height:1.15;-ms-text-size-adjust:100%;-webkit-text-size-adjust:100%}body{margin:0}article,aside,footer,header,nav,section{display:block}h1{font-size:2em;margin:.67em 0}figcaption,figure,main{display:block}figure{margin:1em 40px}hr{-webkit-box-sizing:content-box;box-sizing:content-box;height:0;overflow:visible}pre{font-family:monospace,monospace;font-size:1em}a{background-color:transparent;-webkit-text-decoration-skip:objects}a:active,a:hover{outline-width:0}abbr[title]{border-bottom:none;text-decoration:underline;text-decoration:underline dotted}b,strong{font-weight:inherit}b,strong{font-weight:bolder}code,kbd,samp{font-family:monospace,monospace;font-size:1em}dfn{font-style:italic}mark{background-color:#ff0;color:#000}small{font-size:80%}sub,sup{font-size:75%;line-height:0;position:relative;vertical-align:baseline}sub{bottom:-.25em}sup{top:-.5em}audio,video{display:inline-block}audio:not([controls]){display:none;height:0}img{border-style:none}svg:not(:root){overflow:hidden}button,input,optgroup,select,textarea{font-family:sans-serif;font-size:100%;line-height:1.15;margin:0}button,input{overflow:visible}button,select{text-transform:none}[type=reset],[type=submit],button,html [type=button]{-webkit-appearance:button}[type=button]::-moz-focus-inner,[type=reset]::-moz-focus-inner,[type=submit]::-moz-focus-inner,button::-moz-focus-inner{border-style:none;padding:0}[type=button]:-moz-focusring,[type=reset]:-moz-focusring,[type=submit]:-moz-focusring,button:-moz-focusring{outline:1px dotted ButtonText}fieldset{border:1px solid silver;margin:0 2px;padding:.35em .625em .75em}legend{-webkit-box-sizing:border-box;box-sizing:border-box;color:inherit;display:table;max-width:100%;padding:0;white-space:normal}progress{display:inline-block;vertical-align:baseline}textarea{overflow:auto}[type=checkbox],[type=radio]{-webkit-box-sizing:border-box;box-sizing:border-box;padding:0}[type=number]::-webkit-inner-spin-button,[type=number]::-webkit-outer-spin-button{height:auto}[type=search]{-webkit-appearance:textfield;outline-offset:-2px}[type=search]::-webkit-search-cancel-button,[type=search]::-webkit-search-decoration{-webkit-appearance:none}::-webkit-file-upload-button{-webkit-appearance:button;font:inherit}details,menu{display:block}summary{display:list-item}canvas{display:inline-block}template{display:none}[hidden]{display:none}@media print{*,::after,::before,blockquote::first-letter,blockquote::first-line,div::first-letter,div::first-line,li::first-letter,li::first-line,p::first-letter,p::first-line{text-shadow:none!important;-webkit-box-shadow:none!important;box-shadow:none!important}a,a:visited{text-decoration:underline}abbr[title]::after{content:" (" attr(title) ")"}pre{white-space:pre-wrap!important}blockquote,pre{border:1px solid #999;page-break-inside:avoid}thead{display:table-header-group}img,tr{page-break-inside:avoid}h2,h3,p{orphans:3;widows:3}h2,h3{page-break-after:avoid}.navbar{display:none}.badge{border:1px solid #000}.table{border-collapse:collapse!important}.table td,.table th{background-color:#fff!important}.table-bordered td,.table-bordered th{border:1px solid #ddd!important}}html{-webkit-box-sizing:border-box;box-sizing:border-box}*,::after,::before{-webkit-box-sizing:inherit;box-sizing:inherit}@-ms-viewport{width:device-width}html{-ms-overflow-style:scrollbar;-webkit-tap-highlight-color:transparent}body{font-family:-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-size:1rem;font-weight:400;line-height:1.5;color:#292b2c;background-color:#fff}[tabindex="-1"]:focus{outline:0!important}h1,h2,h3,h4,h5,h6{margin-top:0;margin-bottom:.5rem}p{margin-top:0;margin-bottom:1rem}abbr[data-original-title],abbr[title]{cursor:help}address{margin-bottom:1rem;font-style:normal;line-height:inherit}dl,ol,ul{margin-top:0;margin-bottom:1rem}ol ol,ol ul,ul ol,ul ul{margin-bottom:0}dt{font-weight:700}dd{margin-bottom:.5rem;margin-left:0}blockquote{margin:0 0 1rem}a{color:#0275d8;text-decoration:none}a:focus,a:hover{color:#014c8c;text-decoration:underline}a:not([href]):not([tabindex]){color:inherit;text-decoration:none}a:not([href]):not([tabindex]):focus,a:not([href]):not([tabindex]):hover{color:inherit;text-decoration:none}a:not([href]):not([tabindex]):focus{outline:0}pre{margin-top:0;margin-bottom:1rem;overflow:auto}figure{margin:0 0 1rem}img{vertical-align:middle}[role=button]{cursor:pointer}[role=button],a,area,button,input,label,select,summary,textarea{-ms-touch-action:manipulation;touch-action:manipulation}table{border-collapse:collapse;background-color:transparent}caption{padding-top:.75rem;padding-bottom:.75rem;color:#636c72;text-align:left;caption-side:bottom}th{text-align:left}label{display:inline-block;margin-bottom:.5rem}button:focus{outline:1px dotted;outline:5px auto -webkit-focus-ring-color}button,input,select,textarea{line-height:inherit}input[type=checkbox]:disabled,input[type=radio]:disabled{cursor:not-allowed}input[type=date],input[type=time],input[type=datetime-local],input[type=month]{-webkit-appearance:listbox}textarea{resize:vertical}fieldset{min-width:0;padding:0;margin:0;border:0}legend{display:block;width:100%;padding:0;margin-bottom:.5rem;font-size:1.5rem;line-height:inherit}input[type=search]{-webkit-appearance:none}output{display:inline-block}[hidden]{display:none!important}.h1,.h2,.h3,.h4,.h5,.h6,h1,h2,h3,h4,h5,h6{margin-bottom:.5rem;font-family:inherit;font-weight:500;line-height:1.1;color:inherit}.h1,h1{font-size:2.5rem}.h2,h2{font-size:2rem}.h3,h3{font-size:1.75rem}.h4,h4{font-size:1.5rem}.h5,h5{font-size:1.25rem}.h6,h6{font-size:1rem}.lead{font-size:1.25rem;font-weight:300}.display-1{font-size:6rem;font-weight:300;line-height:1.1}.display-2{font-size:5.5rem;font-weight:300;line-height:1.1}.display-3{font-size:4.5rem;font-weight:300;line-height:1.1}.display-4{font-size:3.5rem;font-weight:300;line-height:1.1}hr{margin-top:1rem;margin-bottom:1rem;border:0;border-top:1px solid rgba(0,0,0,.1)}.small,small{font-size:80%;font-weight:400}.mark,mark{padding:.2em;background-color:#fcf8e3}.list-unstyled{padding-left:0;list-style:none}.list-inline{padding-left:0;list-style:none}.list-inline-item{display:inline-block}.list-inline-item:not(:last-child){margin-right:5px}.initialism{font-size:90%;text-transform:uppercase}.blockquote{padding:.5rem 1rem;margin-bottom:1rem;font-size:1.25rem;border-left:.25rem solid #eceeef}.blockquote-footer{display:block;font-size:80%;color:#636c72}.blockquote-footer::before{content:"\2014 \00A0"}.blockquote-reverse{padding-right:1rem;padding-left:0;text-align:right;border-right:.25rem solid #eceeef;border-left:0}.blockquote-reverse .blockquote-footer::before{content:""}.blockquote-reverse .blockquote-footer::after{content:"\00A0 \2014"}.img-fluid{max-width:100%;height:auto}.img-thumbnail{padding:.25rem;background-color:#fff;border:1px solid #ddd;border-radius:.25rem;-webkit-transition:all .2s ease-in-out;-o-transition:all .2s ease-in-out;transition:all .2s ease-in-out;max-width:100%;height:auto}.figure{display:inline-block}.figure-img{margin-bottom:.5rem;line-height:1}.figure-caption{font-size:90%;color:#636c72}code,kbd,pre,samp{font-family:Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace}code{padding:.2rem .4rem;font-size:90%;color:#bd4147;background-color:#f7f7f9;border-radius:.25rem}a>code{padding:0;color:inherit;background-color:inherit}kbd{padding:.2rem .4rem;font-size:90%;color:#fff;background-color:#292b2c;border-radius:.2rem}kbd kbd{padding:0;font-size:100%;font-weight:700}pre{display:block;margin-top:0;margin-bottom:1rem;font-size:90%;color:#292b2c}pre code{padding:0;font-size:inherit;color:inherit;background-color:transparent;border-radius:0}.pre-scrollable{max-height:340px;overflow-y:scroll}.container{position:relative;margin-left:auto;margin-right:auto;padding-right:15px;padding-left:15px}@media (min-width:576px){.container{padding-right:15px;padding-left:15px}}@media (min-width:768px){.container{padding-right:15px;padding-left:15px}}@media (min-width:992px){.container{padding-right:15px;padding-left:15px}}@media (min-width:1200px){.container{padding-right:15px;padding-left:15px}}@media (min-width:576px){.container{width:540px;max-width:100%}}@media (min-width:768px){.container{width:720px;max-width:100%}}@media (min-width:992px){.container{width:960px;max-width:100%}}@media (min-width:1200px){.container{width:1140px;max-width:100%}}.container-fluid{position:relative;margin-left:auto;margin-right:auto;padding-right:15px;padding-left:15px}@media (min-width:576px){.container-fluid{padding-right:15px;padding-left:15px}}@media (min-width:768px){.container-fluid{padding-right:15px;padding-left:15px}}@media (min-width:992px){.container-fluid{padding-right:15px;padding-left:15px}}@media (min-width:1200px){.container-fluid{padding-right:15px;padding-left:15px}}.row{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-wrap:wrap;-ms-flex-wrap:wrap;flex-wrap:wrap;margin-right:-15px;margin-left:-15px}@media (min-width:576px){.row{margin-right:-15px;margin-left:-15px}}@media (min-width:768px){.row{margin-right:-15px;margin-left:-15px}}@media (min-width:992px){.row{margin-right:-15px;margin-left:-15px}}@media (min-width:1200px){.row{margin-right:-15px;margin-left:-15px}}.no-gutters{margin-right:0;margin-left:0}.no-gutters>.col,.no-gutters>[class*=col-]{padding-right:0;padding-left:0}.col,.col-1,.col-10,.col-11,.col-12,.col-2,.col-3,.col-4,.col-5,.col-6,.col-7,.col-8,.col-9,.col-lg,.col-lg-1,.col-lg-10,.col-lg-11,.col-lg-12,.col-lg-2,.col-lg-3,.col-lg-4,.col-lg-5,.col-lg-6,.col-lg-7,.col-lg-8,.col-lg-9,.col-md,.col-md-1,.col-md-10,.col-md-11,.col-md-12,.col-md-2,.col-md-3,.col-md-4,.col-md-5,.col-md-6,.col-md-7,.col-md-8,.col-md-9,.col-sm,.col-sm-1,.col-sm-10,.col-sm-11,.col-sm-12,.col-sm-2,.col-sm-3,.col-sm-4,.col-sm-5,.col-sm-6,.col-sm-7,.col-sm-8,.col-sm-9,.col-xl,.col-xl-1,.col-xl-10,.col-xl-11,.col-xl-12,.col-xl-2,.col-xl-3,.col-xl-4,.col-xl-5,.col-xl-6,.col-xl-7,.col-xl-8,.col-xl-9{position:relative;width:100%;min-height:1px;padding-right:15px;padding-left:15px}@media (min-width:576px){.col,.col-1,.col-10,.col-11,.col-12,.col-2,.col-3,.col-4,.col-5,.col-6,.col-7,.col-8,.col-9,.col-lg,.col-lg-1,.col-lg-10,.col-lg-11,.col-lg-12,.col-lg-2,.col-lg-3,.col-lg-4,.col-lg-5,.col-lg-6,.col-lg-7,.col-lg-8,.col-lg-9,.col-md,.col-md-1,.col-md-10,.col-md-11,.col-md-12,.col-md-2,.col-md-3,.col-md-4,.col-md-5,.col-md-6,.col-md-7,.col-md-8,.col-md-9,.col-sm,.col-sm-1,.col-sm-10,.col-sm-11,.col-sm-12,.col-sm-2,.col-sm-3,.col-sm-4,.col-sm-5,.col-sm-6,.col-sm-7,.col-sm-8,.col-sm-9,.col-xl,.col-xl-1,.col-xl-10,.col-xl-11,.col-xl-12,.col-xl-2,.col-xl-3,.col-xl-4,.col-xl-5,.col-xl-6,.col-xl-7,.col-xl-8,.col-xl-9{padding-right:15px;padding-left:15px}}@media (min-width:768px){.col,.col-1,.col-10,.col-11,.col-12,.col-2,.col-3,.col-4,.col-5,.col-6,.col-7,.col-8,.col-9,.col-lg,.col-lg-1,.col-lg-10,.col-lg-11,.col-lg-12,.col-lg-2,.col-lg-3,.col-lg-4,.col-lg-5,.col-lg-6,.col-lg-7,.col-lg-8,.col-lg-9,.col-md,.col-md-1,.col-md-10,.col-md-11,.col-md-12,.col-md-2,.col-md-3,.col-md-4,.col-md-5,.col-md-6,.col-md-7,.col-md-8,.col-md-9,.col-sm,.col-sm-1,.col-sm-10,.col-sm-11,.col-sm-12,.col-sm-2,.col-sm-3,.col-sm-4,.col-sm-5,.col-sm-6,.col-sm-7,.col-sm-8,.col-sm-9,.col-xl,.col-xl-1,.col-xl-10,.col-xl-11,.col-xl-12,.col-xl-2,.col-xl-3,.col-xl-4,.col-xl-5,.col-xl-6,.col-xl-7,.col-xl-8,.col-xl-9{padding-right:15px;padding-left:15px}}@media (min-width:992px){.col,.col-1,.col-10,.col-11,.col-12,.col-2,.col-3,.col-4,.col-5,.col-6,.col-7,.col-8,.col-9,.col-lg,.col-lg-1,.col-lg-10,.col-lg-11,.col-lg-12,.col-lg-2,.col-lg-3,.col-lg-4,.col-lg-5,.col-lg-6,.col-lg-7,.col-lg-8,.col-lg-9,.col-md,.col-md-1,.col-md-10,.col-md-11,.col-md-12,.col-md-2,.col-md-3,.col-md-4,.col-md-5,.col-md-6,.col-md-7,.col-md-8,.col-md-9,.col-sm,.col-sm-1,.col-sm-10,.col-sm-11,.col-sm-12,.col-sm-2,.col-sm-3,.col-sm-4,.col-sm-5,.col-sm-6,.col-sm-7,.col-sm-8,.col-sm-9,.col-xl,.col-xl-1,.col-xl-10,.col-xl-11,.col-xl-12,.col-xl-2,.col-xl-3,.col-xl-4,.col-xl-5,.col-xl-6,.col-xl-7,.col-xl-8,.col-xl-9{padding-right:15px;padding-left:15px}}@media (min-width:1200px){.col,.col-1,.col-10,.col-11,.col-12,.col-2,.col-3,.col-4,.col-5,.col-6,.col-7,.col-8,.col-9,.col-lg,.col-lg-1,.col-lg-10,.col-lg-11,.col-lg-12,.col-lg-2,.col-lg-3,.col-lg-4,.col-lg-5,.col-lg-6,.col-lg-7,.col-lg-8,.col-lg-9,.col-md,.col-md-1,.col-md-10,.col-md-11,.col-md-12,.col-md-2,.col-md-3,.col-md-4,.col-md-5,.col-md-6,.col-md-7,.col-md-8,.col-md-9,.col-sm,.col-sm-1,.col-sm-10,.col-sm-11,.col-sm-12,.col-sm-2,.col-sm-3,.col-sm-4,.col-sm-5,.col-sm-6,.col-sm-7,.col-sm-8,.col-sm-9,.col-xl,.col-xl-1,.col-xl-10,.col-xl-11,.col-xl-12,.col-xl-2,.col-xl-3,.col-xl-4,.col-xl-5,.col-xl-6,.col-xl-7,.col-xl-8,.col-xl-9{padding-right:15px;padding-left:15px}}.col{-webkit-flex-basis:0;-ms-flex-preferred-size:0;flex-basis:0;-webkit-box-flex:1;-webkit-flex-grow:1;-ms-flex-positive:1;flex-grow:1;max-width:100%}.col-auto{-webkit-box-flex:0;-webkit-flex:0 0 auto;-ms-flex:0 0 auto;flex:0 0 auto;width:auto}.col-1{-webkit-box-flex:0;-webkit-flex:0 0 8.333333%;-ms-flex:0 0 8.333333%;flex:0 0 8.333333%;max-width:8.333333%}.col-2{-webkit-box-flex:0;-webkit-flex:0 0 16.666667%;-ms-flex:0 0 16.666667%;flex:0 0 16.666667%;max-width:16.666667%}.col-3{-webkit-box-flex:0;-webkit-flex:0 0 25%;-ms-flex:0 0 25%;flex:0 0 25%;max-width:25%}.col-4{-webkit-box-flex:0;-webkit-flex:0 0 33.333333%;-ms-flex:0 0 33.333333%;flex:0 0 33.333333%;max-width:33.333333%}.col-5{-webkit-box-flex:0;-webkit-flex:0 0 41.666667%;-ms-flex:0 0 41.666667%;flex:0 0 41.666667%;max-width:41.666667%}.col-6{-webkit-box-flex:0;-webkit-flex:0 0 50%;-ms-flex:0 0 50%;flex:0 0 50%;max-width:50%}.col-7{-webkit-box-flex:0;-webkit-flex:0 0 58.333333%;-ms-flex:0 0 58.333333%;flex:0 0 58.333333%;max-width:58.333333%}.col-8{-webkit-box-flex:0;-webkit-flex:0 0 66.666667%;-ms-flex:0 0 66.666667%;flex:0 0 66.666667%;max-width:66.666667%}.col-9{-webkit-box-flex:0;-webkit-flex:0 0 75%;-ms-flex:0 0 75%;flex:0 0 75%;max-width:75%}.col-10{-webkit-box-flex:0;-webkit-flex:0 0 83.333333%;-ms-flex:0 0 83.333333%;flex:0 0 83.333333%;max-width:83.333333%}.col-11{-webkit-box-flex:0;-webkit-flex:0 0 91.666667%;-ms-flex:0 0 91.666667%;flex:0 0 91.666667%;max-width:91.666667%}.col-12{-webkit-box-flex:0;-webkit-flex:0 0 100%;-ms-flex:0 0 100%;flex:0 0 100%;max-width:100%}.pull-0{right:auto}.pull-1{right:8.333333%}.pull-2{right:16.666667%}.pull-3{right:25%}.pull-4{right:33.333333%}.pull-5{right:41.666667%}.pull-6{right:50%}.pull-7{right:58.333333%}.pull-8{right:66.666667%}.pull-9{right:75%}.pull-10{right:83.333333%}.pull-11{right:91.666667%}.pull-12{right:100%}.push-0{left:auto}.push-1{left:8.333333%}.push-2{left:16.666667%}.push-3{left:25%}.push-4{left:33.333333%}.push-5{left:41.666667%}.push-6{left:50%}.push-7{left:58.333333%}.push-8{left:66.666667%}.push-9{left:75%}.push-10{left:83.333333%}.push-11{left:91.666667%}.push-12{left:100%}.offset-1{margin-left:8.333333%}.offset-2{margin-left:16.666667%}.offset-3{margin-left:25%}.offset-4{margin-left:33.333333%}.offset-5{margin-left:41.666667%}.offset-6{margin-left:50%}.offset-7{margin-left:58.333333%}.offset-8{margin-left:66.666667%}.offset-9{margin-left:75%}.offset-10{margin-left:83.333333%}.offset-11{margin-left:91.666667%}@media (min-width:576px){.col-sm{-webkit-flex-basis:0;-ms-flex-preferred-size:0;flex-basis:0;-webkit-box-flex:1;-webkit-flex-grow:1;-ms-flex-positive:1;flex-grow:1;max-width:100%}.col-sm-auto{-webkit-box-flex:0;-webkit-flex:0 0 auto;-ms-flex:0 0 auto;flex:0 0 auto;width:auto}.col-sm-1{-webkit-box-flex:0;-webkit-flex:0 0 8.333333%;-ms-flex:0 0 8.333333%;flex:0 0 8.333333%;max-width:8.333333%}.col-sm-2{-webkit-box-flex:0;-webkit-flex:0 0 16.666667%;-ms-flex:0 0 16.666667%;flex:0 0 16.666667%;max-width:16.666667%}.col-sm-3{-webkit-box-flex:0;-webkit-flex:0 0 25%;-ms-flex:0 0 25%;flex:0 0 25%;max-width:25%}.col-sm-4{-webkit-box-flex:0;-webkit-flex:0 0 33.333333%;-ms-flex:0 0 33.333333%;flex:0 0 33.333333%;max-width:33.333333%}.col-sm-5{-webkit-box-flex:0;-webkit-flex:0 0 41.666667%;-ms-flex:0 0 41.666667%;flex:0 0 41.666667%;max-width:41.666667%}.col-sm-6{-webkit-box-flex:0;-webkit-flex:0 0 50%;-ms-flex:0 0 50%;flex:0 0 50%;max-width:50%}.col-sm-7{-webkit-box-flex:0;-webkit-flex:0 0 58.333333%;-ms-flex:0 0 58.333333%;flex:0 0 58.333333%;max-width:58.333333%}.col-sm-8{-webkit-box-flex:0;-webkit-flex:0 0 66.666667%;-ms-flex:0 0 66.666667%;flex:0 0 66.666667%;max-width:66.666667%}.col-sm-9{-webkit-box-flex:0;-webkit-flex:0 0 75%;-ms-flex:0 0 75%;flex:0 0 75%;max-width:75%}.col-sm-10{-webkit-box-flex:0;-webkit-flex:0 0 83.333333%;-ms-flex:0 0 83.333333%;flex:0 0 83.333333%;max-width:83.333333%}.col-sm-11{-webkit-box-flex:0;-webkit-flex:0 0 91.666667%;-ms-flex:0 0 91.666667%;flex:0 0 91.666667%;max-width:91.666667%}.col-sm-12{-webkit-box-flex:0;-webkit-flex:0 0 100%;-ms-flex:0 0 100%;flex:0 0 100%;max-width:100%}.pull-sm-0{right:auto}.pull-sm-1{right:8.333333%}.pull-sm-2{right:16.666667%}.pull-sm-3{right:25%}.pull-sm-4{right:33.333333%}.pull-sm-5{right:41.666667%}.pull-sm-6{right:50%}.pull-sm-7{right:58.333333%}.pull-sm-8{right:66.666667%}.pull-sm-9{right:75%}.pull-sm-10{right:83.333333%}.pull-sm-11{right:91.666667%}.pull-sm-12{right:100%}.push-sm-0{left:auto}.push-sm-1{left:8.333333%}.push-sm-2{left:16.666667%}.push-sm-3{left:25%}.push-sm-4{left:33.333333%}.push-sm-5{left:41.666667%}.push-sm-6{left:50%}.push-sm-7{left:58.333333%}.push-sm-8{left:66.666667%}.push-sm-9{left:75%}.push-sm-10{left:83.333333%}.push-sm-11{left:91.666667%}.push-sm-12{left:100%}.offset-sm-0{margin-left:0}.offset-sm-1{margin-left:8.333333%}.offset-sm-2{margin-left:16.666667%}.offset-sm-3{margin-left:25%}.offset-sm-4{margin-left:33.333333%}.offset-sm-5{margin-left:41.666667%}.offset-sm-6{margin-left:50%}.offset-sm-7{margin-left:58.333333%}.offset-sm-8{margin-left:66.666667%}.offset-sm-9{margin-left:75%}.offset-sm-10{margin-left:83.333333%}.offset-sm-11{margin-left:91.666667%}}@media (min-width:768px){.col-md{-webkit-flex-basis:0;-ms-flex-preferred-size:0;flex-basis:0;-webkit-box-flex:1;-webkit-flex-grow:1;-ms-flex-positive:1;flex-grow:1;max-width:100%}.col-md-auto{-webkit-box-flex:0;-webkit-flex:0 0 auto;-ms-flex:0 0 auto;flex:0 0 auto;width:auto}.col-md-1{-webkit-box-flex:0;-webkit-flex:0 0 8.333333%;-ms-flex:0 0 8.333333%;flex:0 0 8.333333%;max-width:8.333333%}.col-md-2{-webkit-box-flex:0;-webkit-flex:0 0 16.666667%;-ms-flex:0 0 16.666667%;flex:0 0 16.666667%;max-width:16.666667%}.col-md-3{-webkit-box-flex:0;-webkit-flex:0 0 25%;-ms-flex:0 0 25%;flex:0 0 25%;max-width:25%}.col-md-4{-webkit-box-flex:0;-webkit-flex:0 0 33.333333%;-ms-flex:0 0 33.333333%;flex:0 0 33.333333%;max-width:33.333333%}.col-md-5{-webkit-box-flex:0;-webkit-flex:0 0 41.666667%;-ms-flex:0 0 41.666667%;flex:0 0 41.666667%;max-width:41.666667%}.col-md-6{-webkit-box-flex:0;-webkit-flex:0 0 50%;-ms-flex:0 0 50%;flex:0 0 50%;max-width:50%}.col-md-7{-webkit-box-flex:0;-webkit-flex:0 0 58.333333%;-ms-flex:0 0 58.333333%;flex:0 0 58.333333%;max-width:58.333333%}.col-md-8{-webkit-box-flex:0;-webkit-flex:0 0 66.666667%;-ms-flex:0 0 66.666667%;flex:0 0 66.666667%;max-width:66.666667%}.col-md-9{-webkit-box-flex:0;-webkit-flex:0 0 75%;-ms-flex:0 0 75%;flex:0 0 75%;max-width:75%}.col-md-10{-webkit-box-flex:0;-webkit-flex:0 0 83.333333%;-ms-flex:0 0 83.333333%;flex:0 0 83.333333%;max-width:83.333333%}.col-md-11{-webkit-box-flex:0;-webkit-flex:0 0 91.666667%;-ms-flex:0 0 91.666667%;flex:0 0 91.666667%;max-width:91.666667%}.col-md-12{-webkit-box-flex:0;-webkit-flex:0 0 100%;-ms-flex:0 0 100%;flex:0 0 100%;max-width:100%}.pull-md-0{right:auto}.pull-md-1{right:8.333333%}.pull-md-2{right:16.666667%}.pull-md-3{right:25%}.pull-md-4{right:33.333333%}.pull-md-5{right:41.666667%}.pull-md-6{right:50%}.pull-md-7{right:58.333333%}.pull-md-8{right:66.666667%}.pull-md-9{right:75%}.pull-md-10{right:83.333333%}.pull-md-11{right:91.666667%}.pull-md-12{right:100%}.push-md-0{left:auto}.push-md-1{left:8.333333%}.push-md-2{left:16.666667%}.push-md-3{left:25%}.push-md-4{left:33.333333%}.push-md-5{left:41.666667%}.push-md-6{left:50%}.push-md-7{left:58.333333%}.push-md-8{left:66.666667%}.push-md-9{left:75%}.push-md-10{left:83.333333%}.push-md-11{left:91.666667%}.push-md-12{left:100%}.offset-md-0{margin-left:0}.offset-md-1{margin-left:8.333333%}.offset-md-2{margin-left:16.666667%}.offset-md-3{margin-left:25%}.offset-md-4{margin-left:33.333333%}.offset-md-5{margin-left:41.666667%}.offset-md-6{margin-left:50%}.offset-md-7{margin-left:58.333333%}.offset-md-8{margin-left:66.666667%}.offset-md-9{margin-left:75%}.offset-md-10{margin-left:83.333333%}.offset-md-11{margin-left:91.666667%}}@media (min-width:992px){.col-lg{-webkit-flex-basis:0;-ms-flex-preferred-size:0;flex-basis:0;-webkit-box-flex:1;-webkit-flex-grow:1;-ms-flex-positive:1;flex-grow:1;max-width:100%}.col-lg-auto{-webkit-box-flex:0;-webkit-flex:0 0 auto;-ms-flex:0 0 auto;flex:0 0 auto;width:auto}.col-lg-1{-webkit-box-flex:0;-webkit-flex:0 0 8.333333%;-ms-flex:0 0 8.333333%;flex:0 0 8.333333%;max-width:8.333333%}.col-lg-2{-webkit-box-flex:0;-webkit-flex:0 0 16.666667%;-ms-flex:0 0 16.666667%;flex:0 0 16.666667%;max-width:16.666667%}.col-lg-3{-webkit-box-flex:0;-webkit-flex:0 0 25%;-ms-flex:0 0 25%;flex:0 0 25%;max-width:25%}.col-lg-4{-webkit-box-flex:0;-webkit-flex:0 0 33.333333%;-ms-flex:0 0 33.333333%;flex:0 0 33.333333%;max-width:33.333333%}.col-lg-5{-webkit-box-flex:0;-webkit-flex:0 0 41.666667%;-ms-flex:0 0 41.666667%;flex:0 0 41.666667%;max-width:41.666667%}.col-lg-6{-webkit-box-flex:0;-webkit-flex:0 0 50%;-ms-flex:0 0 50%;flex:0 0 50%;max-width:50%}.col-lg-7{-webkit-box-flex:0;-webkit-flex:0 0 58.333333%;-ms-flex:0 0 58.333333%;flex:0 0 58.333333%;max-width:58.333333%}.col-lg-8{-webkit-box-flex:0;-webkit-flex:0 0 66.666667%;-ms-flex:0 0 66.666667%;flex:0 0 66.666667%;max-width:66.666667%}.col-lg-9{-webkit-box-flex:0;-webkit-flex:0 0 75%;-ms-flex:0 0 75%;flex:0 0 75%;max-width:75%}.col-lg-10{-webkit-box-flex:0;-webkit-flex:0 0 83.333333%;-ms-flex:0 0 83.333333%;flex:0 0 83.333333%;max-width:83.333333%}.col-lg-11{-webkit-box-flex:0;-webkit-flex:0 0 91.666667%;-ms-flex:0 0 91.666667%;flex:0 0 91.666667%;max-width:91.666667%}.col-lg-12{-webkit-box-flex:0;-webkit-flex:0 0 100%;-ms-flex:0 0 100%;flex:0 0 100%;max-width:100%}.pull-lg-0{right:auto}.pull-lg-1{right:8.333333%}.pull-lg-2{right:16.666667%}.pull-lg-3{right:25%}.pull-lg-4{right:33.333333%}.pull-lg-5{right:41.666667%}.pull-lg-6{right:50%}.pull-lg-7{right:58.333333%}.pull-lg-8{right:66.666667%}.pull-lg-9{right:75%}.pull-lg-10{right:83.333333%}.pull-lg-11{right:91.666667%}.pull-lg-12{right:100%}.push-lg-0{left:auto}.push-lg-1{left:8.333333%}.push-lg-2{left:16.666667%}.push-lg-3{left:25%}.push-lg-4{left:33.333333%}.push-lg-5{left:41.666667%}.push-lg-6{left:50%}.push-lg-7{left:58.333333%}.push-lg-8{left:66.666667%}.push-lg-9{left:75%}.push-lg-10{left:83.333333%}.push-lg-11{left:91.666667%}.push-lg-12{left:100%}.offset-lg-0{margin-left:0}.offset-lg-1{margin-left:8.333333%}.offset-lg-2{margin-left:16.666667%}.offset-lg-3{margin-left:25%}.offset-lg-4{margin-left:33.333333%}.offset-lg-5{margin-left:41.666667%}.offset-lg-6{margin-left:50%}.offset-lg-7{margin-left:58.333333%}.offset-lg-8{margin-left:66.666667%}.offset-lg-9{margin-left:75%}.offset-lg-10{margin-left:83.333333%}.offset-lg-11{margin-left:91.666667%}}@media (min-width:1200px){.col-xl{-webkit-flex-basis:0;-ms-flex-preferred-size:0;flex-basis:0;-webkit-box-flex:1;-webkit-flex-grow:1;-ms-flex-positive:1;flex-grow:1;max-width:100%}.col-xl-auto{-webkit-box-flex:0;-webkit-flex:0 0 auto;-ms-flex:0 0 auto;flex:0 0 auto;width:auto}.col-xl-1{-webkit-box-flex:0;-webkit-flex:0 0 8.333333%;-ms-flex:0 0 8.333333%;flex:0 0 8.333333%;max-width:8.333333%}.col-xl-2{-webkit-box-flex:0;-webkit-flex:0 0 16.666667%;-ms-flex:0 0 16.666667%;flex:0 0 16.666667%;max-width:16.666667%}.col-xl-3{-webkit-box-flex:0;-webkit-flex:0 0 25%;-ms-flex:0 0 25%;flex:0 0 25%;max-width:25%}.col-xl-4{-webkit-box-flex:0;-webkit-flex:0 0 33.333333%;-ms-flex:0 0 33.333333%;flex:0 0 33.333333%;max-width:33.333333%}.col-xl-5{-webkit-box-flex:0;-webkit-flex:0 0 41.666667%;-ms-flex:0 0 41.666667%;flex:0 0 41.666667%;max-width:41.666667%}.col-xl-6{-webkit-box-flex:0;-webkit-flex:0 0 50%;-ms-flex:0 0 50%;flex:0 0 50%;max-width:50%}.col-xl-7{-webkit-box-flex:0;-webkit-flex:0 0 58.333333%;-ms-flex:0 0 58.333333%;flex:0 0 58.333333%;max-width:58.333333%}.col-xl-8{-webkit-box-flex:0;-webkit-flex:0 0 66.666667%;-ms-flex:0 0 66.666667%;flex:0 0 66.666667%;max-width:66.666667%}.col-xl-9{-webkit-box-flex:0;-webkit-flex:0 0 75%;-ms-flex:0 0 75%;flex:0 0 75%;max-width:75%}.col-xl-10{-webkit-box-flex:0;-webkit-flex:0 0 83.333333%;-ms-flex:0 0 83.333333%;flex:0 0 83.333333%;max-width:83.333333%}.col-xl-11{-webkit-box-flex:0;-webkit-flex:0 0 91.666667%;-ms-flex:0 0 91.666667%;flex:0 0 91.666667%;max-width:91.666667%}.col-xl-12{-webkit-box-flex:0;-webkit-flex:0 0 100%;-ms-flex:0 0 100%;flex:0 0 100%;max-width:100%}.pull-xl-0{right:auto}.pull-xl-1{right:8.333333%}.pull-xl-2{right:16.666667%}.pull-xl-3{right:25%}.pull-xl-4{right:33.333333%}.pull-xl-5{right:41.666667%}.pull-xl-6{right:50%}.pull-xl-7{right:58.333333%}.pull-xl-8{right:66.666667%}.pull-xl-9{right:75%}.pull-xl-10{right:83.333333%}.pull-xl-11{right:91.666667%}.pull-xl-12{right:100%}.push-xl-0{left:auto}.push-xl-1{left:8.333333%}.push-xl-2{left:16.666667%}.push-xl-3{left:25%}.push-xl-4{left:33.333333%}.push-xl-5{left:41.666667%}.push-xl-6{left:50%}.push-xl-7{left:58.333333%}.push-xl-8{left:66.666667%}.push-xl-9{left:75%}.push-xl-10{left:83.333333%}.push-xl-11{left:91.666667%}.push-xl-12{left:100%}.offset-xl-0{margin-left:0}.offset-xl-1{margin-left:8.333333%}.offset-xl-2{margin-left:16.666667%}.offset-xl-3{margin-left:25%}.offset-xl-4{margin-left:33.333333%}.offset-xl-5{margin-left:41.666667%}.offset-xl-6{margin-left:50%}.offset-xl-7{margin-left:58.333333%}.offset-xl-8{margin-left:66.666667%}.offset-xl-9{margin-left:75%}.offset-xl-10{margin-left:83.333333%}.offset-xl-11{margin-left:91.666667%}}.table{width:100%;max-width:100%;margin-bottom:1rem}.table td,.table th{padding:.75rem;vertical-align:top;border-top:1px solid #eceeef}.table thead th{vertical-align:bottom;border-bottom:2px solid #eceeef}.table tbody+tbody{border-top:2px solid #eceeef}.table .table{background-color:#fff}.table-sm td,.table-sm th{padding:.3rem}.table-bordered{border:1px solid #eceeef}.table-bordered td,.table-bordered th{border:1px solid #eceeef}.table-bordered thead td,.table-bordered thead th{border-bottom-width:2px}.table-striped tbody tr:nth-of-type(odd){background-color:rgba(0,0,0,.05)}.table-hover tbody tr:hover{background-color:rgba(0,0,0,.075)}.table-active,.table-active>td,.table-active>th{background-color:rgba(0,0,0,.075)}.table-hover .table-active:hover{background-color:rgba(0,0,0,.075)}.table-hover .table-active:hover>td,.table-hover .table-active:hover>th{background-color:rgba(0,0,0,.075)}.table-success,.table-success>td,.table-success>th{background-color:#dff0d8}.table-hover .table-success:hover{background-color:#d0e9c6}.table-hover .table-success:hover>td,.table-hover .table-success:hover>th{background-color:#d0e9c6}.table-info,.table-info>td,.table-info>th{background-color:#d9edf7}.table-hover .table-info:hover{background-color:#c4e3f3}.table-hover .table-info:hover>td,.table-hover .table-info:hover>th{background-color:#c4e3f3}.table-warning,.table-warning>td,.table-warning>th{background-color:#fcf8e3}.table-hover .table-warning:hover{background-color:#faf2cc}.table-hover .table-warning:hover>td,.table-hover .table-warning:hover>th{background-color:#faf2cc}.table-danger,.table-danger>td,.table-danger>th{background-color:#f2dede}.table-hover .table-danger:hover{background-color:#ebcccc}.table-hover .table-danger:hover>td,.table-hover .table-danger:hover>th{background-color:#ebcccc}.thead-inverse th{color:#fff;background-color:#292b2c}.thead-default th{color:#464a4c;background-color:#eceeef}.table-inverse{color:#fff;background-color:#292b2c}.table-inverse td,.table-inverse th,.table-inverse thead th{border-color:#fff}.table-inverse.table-bordered{border:0}.table-responsive{display:block;width:100%;overflow-x:auto;-ms-overflow-style:-ms-autohiding-scrollbar}.table-responsive.table-bordered{border:0}.form-control{display:block;width:100%;padding:.5rem .75rem;font-size:1rem;line-height:1.25;color:#464a4c;background-color:#fff;background-image:none;-webkit-background-clip:padding-box;background-clip:padding-box;border:1px solid rgba(0,0,0,.15);border-radius:.25rem;-webkit-transition:border-color ease-in-out .15s,-webkit-box-shadow ease-in-out .15s;transition:border-color ease-in-out .15s,-webkit-box-shadow ease-in-out .15s;-o-transition:border-color ease-in-out .15s,box-shadow ease-in-out .15s;transition:border-color ease-in-out .15s,box-shadow ease-in-out .15s;transition:border-color ease-in-out .15s,box-shadow ease-in-out .15s,-webkit-box-shadow ease-in-out .15s}.form-control::-ms-expand{background-color:transparent;border:0}.form-control:focus{color:#464a4c;background-color:#fff;border-color:#5cb3fd;outline:0}.form-control::-webkit-input-placeholder{color:#636c72;opacity:1}.form-control::-moz-placeholder{color:#636c72;opacity:1}.form-control:-ms-input-placeholder{color:#636c72;opacity:1}.form-control::placeholder{color:#636c72;opacity:1}.form-control:disabled,.form-control[readonly]{background-color:#eceeef;opacity:1}.form-control:disabled{cursor:not-allowed}select.form-control:not([size]):not([multiple]){height:calc(2.25rem + 2px)}select.form-control:focus::-ms-value{color:#464a4c;background-color:#fff}.form-control-file,.form-control-range{display:block}.col-form-label{padding-top:calc(.5rem - 1px * 2);padding-bottom:calc(.5rem - 1px * 2);margin-bottom:0}.col-form-label-lg{padding-top:calc(.75rem - 1px * 2);padding-bottom:calc(.75rem - 1px * 2);font-size:1.25rem}.col-form-label-sm{padding-top:calc(.25rem - 1px * 2);padding-bottom:calc(.25rem - 1px * 2);font-size:.875rem}.col-form-legend{padding-top:.5rem;padding-bottom:.5rem;margin-bottom:0;font-size:1rem}.form-control-static{padding-top:.5rem;padding-bottom:.5rem;margin-bottom:0;line-height:1.25;border:solid transparent;border-width:1px 0}.form-control-static.form-control-lg,.form-control-static.form-control-sm,.input-group-lg>.form-control-static.form-control,.input-group-lg>.form-control-static.input-group-addon,.input-group-lg>.input-group-btn>.form-control-static.btn,.input-group-sm>.form-control-static.form-control,.input-group-sm>.form-control-static.input-group-addon,.input-group-sm>.input-group-btn>.form-control-static.btn{padding-right:0;padding-left:0}.form-control-sm,.input-group-sm>.form-control,.input-group-sm>.input-group-addon,.input-group-sm>.input-group-btn>.btn{padding:.25rem .5rem;font-size:.875rem;border-radius:.2rem}.input-group-sm>.input-group-btn>select.btn:not([size]):not([multiple]),.input-group-sm>select.form-control:not([size]):not([multiple]),.input-group-sm>select.input-group-addon:not([size]):not([multiple]),select.form-control-sm:not([size]):not([multiple]){height:1.8125rem}.form-control-lg,.input-group-lg>.form-control,.input-group-lg>.input-group-addon,.input-group-lg>.input-group-btn>.btn{padding:.75rem 1.5rem;font-size:1.25rem;border-radius:.3rem}.input-group-lg>.input-group-btn>select.btn:not([size]):not([multiple]),.input-group-lg>select.form-control:not([size]):not([multiple]),.input-group-lg>select.input-group-addon:not([size]):not([multiple]),select.form-control-lg:not([size]):not([multiple]){height:3.166667rem}.form-group{margin-bottom:1rem}.form-text{display:block;margin-top:.25rem}.form-check{position:relative;display:block;margin-bottom:.5rem}.form-check.disabled .form-check-label{color:#636c72;cursor:not-allowed}.form-check-label{padding-left:1.25rem;margin-bottom:0;cursor:pointer}.form-check-input{position:absolute;margin-top:.25rem;margin-left:-1.25rem}.form-check-input:only-child{position:static}.form-check-inline{display:inline-block}.form-check-inline .form-check-label{vertical-align:middle}.form-check-inline+.form-check-inline{margin-left:.75rem}.form-control-feedback{margin-top:.25rem}.form-control-danger,.form-control-success,.form-control-warning{padding-right:2.25rem;background-repeat:no-repeat;background-position:center right .5625rem;-webkit-background-size:1.125rem 1.125rem;background-size:1.125rem 1.125rem}.has-success .col-form-label,.has-success .custom-control,.has-success .form-check-label,.has-success .form-control-feedback,.has-success .form-control-label{color:#5cb85c}.has-success .form-control{border-color:#5cb85c}.has-success .input-group-addon{color:#5cb85c;border-color:#5cb85c;background-color:#eaf6ea}.has-success .form-control-success{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 8 8'%3E%3Cpath fill='%235cb85c' d='M2.3 6.73L.6 4.53c-.4-1.04.46-1.4 1.1-.8l1.1 1.4 3.4-3.8c.6-.63 1.6-.27 1.2.7l-4 4.6c-.43.5-.8.4-1.1.1z'/%3E%3C/svg%3E")}.has-warning .col-form-label,.has-warning .custom-control,.has-warning .form-check-label,.has-warning .form-control-feedback,.has-warning .form-control-label{color:#f0ad4e}.has-warning .form-control{border-color:#f0ad4e}.has-warning .input-group-addon{color:#f0ad4e;border-color:#f0ad4e;background-color:#fff}.has-warning .form-control-warning{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 8 8'%3E%3Cpath fill='%23f0ad4e' d='M4.4 5.324h-.8v-2.46h.8zm0 1.42h-.8V5.89h.8zM3.76.63L.04 7.075c-.115.2.016.425.26.426h7.397c.242 0 .372-.226.258-.426C6.726 4.924 5.47 2.79 4.253.63c-.113-.174-.39-.174-.494 0z'/%3E%3C/svg%3E")}.has-danger .col-form-label,.has-danger .custom-control,.has-danger .form-check-label,.has-danger .form-control-feedback,.has-danger .form-control-label{color:#d9534f}.has-danger .form-control{border-color:#d9534f}.has-danger .input-group-addon{color:#d9534f;border-color:#d9534f;background-color:#fdf7f7}.has-danger .form-control-danger{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23d9534f' viewBox='-2 -2 7 7'%3E%3Cpath stroke='%23d9534f' d='M0 0l3 3m0-3L0 3'/%3E%3Ccircle r='.5'/%3E%3Ccircle cx='3' r='.5'/%3E%3Ccircle cy='3' r='.5'/%3E%3Ccircle cx='3' cy='3' r='.5'/%3E%3C/svg%3E")}.form-inline{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-flow:row wrap;-ms-flex-flow:row wrap;flex-flow:row wrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.form-inline .form-check{width:100%}@media (min-width:576px){.form-inline label{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-webkit-justify-content:center;-ms-flex-pack:center;justify-content:center;margin-bottom:0}.form-inline .form-group{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-flex:0;-webkit-flex:0 0 auto;-ms-flex:0 0 auto;flex:0 0 auto;-webkit-flex-flow:row wrap;-ms-flex-flow:row wrap;flex-flow:row wrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center;margin-bottom:0}.form-inline .form-control{display:inline-block;width:auto;vertical-align:middle}.form-inline .form-control-static{display:inline-block}.form-inline .input-group{width:auto}.form-inline .form-control-label{margin-bottom:0;vertical-align:middle}.form-inline .form-check{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-webkit-justify-content:center;-ms-flex-pack:center;justify-content:center;width:auto;margin-top:0;margin-bottom:0}.form-inline .form-check-label{padding-left:0}.form-inline .form-check-input{position:relative;margin-top:0;margin-right:.25rem;margin-left:0}.form-inline .custom-control{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-webkit-justify-content:center;-ms-flex-pack:center;justify-content:center;padding-left:0}.form-inline .custom-control-indicator{position:static;display:inline-block;margin-right:.25rem;vertical-align:text-bottom}.form-inline .has-feedback .form-control-feedback{top:0}}.btn{display:inline-block;font-weight:400;line-height:1.25;text-align:center;white-space:nowrap;vertical-align:middle;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;border:1px solid transparent;padding:.5rem 1rem;font-size:1rem;border-radius:.25rem;-webkit-transition:all .2s ease-in-out;-o-transition:all .2s ease-in-out;transition:all .2s ease-in-out}.btn:focus,.btn:hover{text-decoration:none}.btn.focus,.btn:focus{outline:0;-webkit-box-shadow:0 0 0 2px rgba(2,117,216,.25);box-shadow:0 0 0 2px rgba(2,117,216,.25)}.btn.disabled,.btn:disabled{cursor:not-allowed;opacity:.65}.btn.active,.btn:active{background-image:none}a.btn.disabled,fieldset[disabled] a.btn{pointer-events:none}.btn-primary{color:#fff;background-color:#0275d8;border-color:#0275d8}.btn-primary:hover{color:#fff;background-color:#025aa5;border-color:#01549b}.btn-primary.focus,.btn-primary:focus{-webkit-box-shadow:0 0 0 2px rgba(2,117,216,.5);box-shadow:0 0 0 2px rgba(2,117,216,.5)}.btn-primary.disabled,.btn-primary:disabled{background-color:#0275d8;border-color:#0275d8}.btn-primary.active,.btn-primary:active,.show>.btn-primary.dropdown-toggle{color:#fff;background-color:#025aa5;background-image:none;border-color:#01549b}.btn-secondary{color:#292b2c;background-color:#fff;border-color:#ccc}.btn-secondary:hover{color:#292b2c;background-color:#e6e6e6;border-color:#adadad}.btn-secondary.focus,.btn-secondary:focus{-webkit-box-shadow:0 0 0 2px rgba(204,204,204,.5);box-shadow:0 0 0 2px rgba(204,204,204,.5)}.btn-secondary.disabled,.btn-secondary:disabled{background-color:#fff;border-color:#ccc}.btn-secondary.active,.btn-secondary:active,.show>.btn-secondary.dropdown-toggle{color:#292b2c;background-color:#e6e6e6;background-image:none;border-color:#adadad}.btn-info{color:#fff;background-color:#5bc0de;border-color:#5bc0de}.btn-info:hover{color:#fff;background-color:#31b0d5;border-color:#2aabd2}.btn-info.focus,.btn-info:focus{-webkit-box-shadow:0 0 0 2px rgba(91,192,222,.5);box-shadow:0 0 0 2px rgba(91,192,222,.5)}.btn-info.disabled,.btn-info:disabled{background-color:#5bc0de;border-color:#5bc0de}.btn-info.active,.btn-info:active,.show>.btn-info.dropdown-toggle{color:#fff;background-color:#31b0d5;background-image:none;border-color:#2aabd2}.btn-success{color:#fff;background-color:#5cb85c;border-color:#5cb85c}.btn-success:hover{color:#fff;background-color:#449d44;border-color:#419641}.btn-success.focus,.btn-success:focus{-webkit-box-shadow:0 0 0 2px rgba(92,184,92,.5);box-shadow:0 0 0 2px rgba(92,184,92,.5)}.btn-success.disabled,.btn-success:disabled{background-color:#5cb85c;border-color:#5cb85c}.btn-success.active,.btn-success:active,.show>.btn-success.dropdown-toggle{color:#fff;background-color:#449d44;background-image:none;border-color:#419641}.btn-warning{color:#fff;background-color:#f0ad4e;border-color:#f0ad4e}.btn-warning:hover{color:#fff;background-color:#ec971f;border-color:#eb9316}.btn-warning.focus,.btn-warning:focus{-webkit-box-shadow:0 0 0 2px rgba(240,173,78,.5);box-shadow:0 0 0 2px rgba(240,173,78,.5)}.btn-warning.disabled,.btn-warning:disabled{background-color:#f0ad4e;border-color:#f0ad4e}.btn-warning.active,.btn-warning:active,.show>.btn-warning.dropdown-toggle{color:#fff;background-color:#ec971f;background-image:none;border-color:#eb9316}.btn-danger{color:#fff;background-color:#d9534f;border-color:#d9534f}.btn-danger:hover{color:#fff;background-color:#c9302c;border-color:#c12e2a}.btn-danger.focus,.btn-danger:focus{-webkit-box-shadow:0 0 0 2px rgba(217,83,79,.5);box-shadow:0 0 0 2px rgba(217,83,79,.5)}.btn-danger.disabled,.btn-danger:disabled{background-color:#d9534f;border-color:#d9534f}.btn-danger.active,.btn-danger:active,.show>.btn-danger.dropdown-toggle{color:#fff;background-color:#c9302c;background-image:none;border-color:#c12e2a}.btn-outline-primary{color:#0275d8;background-image:none;background-color:transparent;border-color:#0275d8}.btn-outline-primary:hover{color:#fff;background-color:#0275d8;border-color:#0275d8}.btn-outline-primary.focus,.btn-outline-primary:focus{-webkit-box-shadow:0 0 0 2px rgba(2,117,216,.5);box-shadow:0 0 0 2px rgba(2,117,216,.5)}.btn-outline-primary.disabled,.btn-outline-primary:disabled{color:#0275d8;background-color:transparent}.btn-outline-primary.active,.btn-outline-primary:active,.show>.btn-outline-primary.dropdown-toggle{color:#fff;background-color:#0275d8;border-color:#0275d8}.btn-outline-secondary{color:#ccc;background-image:none;background-color:transparent;border-color:#ccc}.btn-outline-secondary:hover{color:#fff;background-color:#ccc;border-color:#ccc}.btn-outline-secondary.focus,.btn-outline-secondary:focus{-webkit-box-shadow:0 0 0 2px rgba(204,204,204,.5);box-shadow:0 0 0 2px rgba(204,204,204,.5)}.btn-outline-secondary.disabled,.btn-outline-secondary:disabled{color:#ccc;background-color:transparent}.btn-outline-secondary.active,.btn-outline-secondary:active,.show>.btn-outline-secondary.dropdown-toggle{color:#fff;background-color:#ccc;border-color:#ccc}.btn-outline-info{color:#5bc0de;background-image:none;background-color:transparent;border-color:#5bc0de}.btn-outline-info:hover{color:#fff;background-color:#5bc0de;border-color:#5bc0de}.btn-outline-info.focus,.btn-outline-info:focus{-webkit-box-shadow:0 0 0 2px rgba(91,192,222,.5);box-shadow:0 0 0 2px rgba(91,192,222,.5)}.btn-outline-info.disabled,.btn-outline-info:disabled{color:#5bc0de;background-color:transparent}.btn-outline-info.active,.btn-outline-info:active,.show>.btn-outline-info.dropdown-toggle{color:#fff;background-color:#5bc0de;border-color:#5bc0de}.btn-outline-success{color:#5cb85c;background-image:none;background-color:transparent;border-color:#5cb85c}.btn-outline-success:hover{color:#fff;background-color:#5cb85c;border-color:#5cb85c}.btn-outline-success.focus,.btn-outline-success:focus{-webkit-box-shadow:0 0 0 2px rgba(92,184,92,.5);box-shadow:0 0 0 2px rgba(92,184,92,.5)}.btn-outline-success.disabled,.btn-outline-success:disabled{color:#5cb85c;background-color:transparent}.btn-outline-success.active,.btn-outline-success:active,.show>.btn-outline-success.dropdown-toggle{color:#fff;background-color:#5cb85c;border-color:#5cb85c}.btn-outline-warning{color:#f0ad4e;background-image:none;background-color:transparent;border-color:#f0ad4e}.btn-outline-warning:hover{color:#fff;background-color:#f0ad4e;border-color:#f0ad4e}.btn-outline-warning.focus,.btn-outline-warning:focus{-webkit-box-shadow:0 0 0 2px rgba(240,173,78,.5);box-shadow:0 0 0 2px rgba(240,173,78,.5)}.btn-outline-warning.disabled,.btn-outline-warning:disabled{color:#f0ad4e;background-color:transparent}.btn-outline-warning.active,.btn-outline-warning:active,.show>.btn-outline-warning.dropdown-toggle{color:#fff;background-color:#f0ad4e;border-color:#f0ad4e}.btn-outline-danger{color:#d9534f;background-image:none;background-color:transparent;border-color:#d9534f}.btn-outline-danger:hover{color:#fff;background-color:#d9534f;border-color:#d9534f}.btn-outline-danger.focus,.btn-outline-danger:focus{-webkit-box-shadow:0 0 0 2px rgba(217,83,79,.5);box-shadow:0 0 0 2px rgba(217,83,79,.5)}.btn-outline-danger.disabled,.btn-outline-danger:disabled{color:#d9534f;background-color:transparent}.btn-outline-danger.active,.btn-outline-danger:active,.show>.btn-outline-danger.dropdown-toggle{color:#fff;background-color:#d9534f;border-color:#d9534f}.btn-link{font-weight:400;color:#0275d8;border-radius:0}.btn-link,.btn-link.active,.btn-link:active,.btn-link:disabled{background-color:transparent}.btn-link,.btn-link:active,.btn-link:focus{border-color:transparent}.btn-link:hover{border-color:transparent}.btn-link:focus,.btn-link:hover{color:#014c8c;text-decoration:underline;background-color:transparent}.btn-link:disabled{color:#636c72}.btn-link:disabled:focus,.btn-link:disabled:hover{text-decoration:none}.btn-group-lg>.btn,.btn-lg{padding:.75rem 1.5rem;font-size:1.25rem;border-radius:.3rem}.btn-group-sm>.btn,.btn-sm{padding:.25rem .5rem;font-size:.875rem;border-radius:.2rem}.btn-block{display:block;width:100%}.btn-block+.btn-block{margin-top:.5rem}input[type=button].btn-block,input[type=reset].btn-block,input[type=submit].btn-block{width:100%}.fade{opacity:0;-webkit-transition:opacity .15s linear;-o-transition:opacity .15s linear;transition:opacity .15s linear}.fade.show{opacity:1}.collapse{display:none}.collapse.show{display:block}tr.collapse.show{display:table-row}tbody.collapse.show{display:table-row-group}.collapsing{position:relative;height:0;overflow:hidden;-webkit-transition:height .35s ease;-o-transition:height .35s ease;transition:height .35s ease}.dropdown,.dropup{position:relative}.dropdown-toggle::after{display:inline-block;width:0;height:0;margin-left:.3em;vertical-align:middle;content:"";border-top:.3em solid;border-right:.3em solid transparent;border-left:.3em solid transparent}.dropdown-toggle:focus{outline:0}.dropup .dropdown-toggle::after{border-top:0;border-bottom:.3em solid}.dropdown-menu{position:absolute;top:100%;left:0;z-index:1000;display:none;float:left;min-width:10rem;padding:.5rem 0;margin:.125rem 0 0;font-size:1rem;color:#292b2c;text-align:left;list-style:none;background-color:#fff;-webkit-background-clip:padding-box;background-clip:padding-box;border:1px solid rgba(0,0,0,.15);border-radius:.25rem}.dropdown-divider{height:1px;margin:.5rem 0;overflow:hidden;background-color:#eceeef}.dropdown-item{display:block;width:100%;padding:3px 1.5rem;clear:both;font-weight:400;color:#292b2c;text-align:inherit;white-space:nowrap;background:0 0;border:0}.dropdown-item:focus,.dropdown-item:hover{color:#1d1e1f;text-decoration:none;background-color:#f7f7f9}.dropdown-item.active,.dropdown-item:active{color:#fff;text-decoration:none;background-color:#0275d8}.dropdown-item.disabled,.dropdown-item:disabled{color:#636c72;cursor:not-allowed;background-color:transparent}.show>.dropdown-menu{display:block}.show>a{outline:0}.dropdown-menu-right{right:0;left:auto}.dropdown-menu-left{right:auto;left:0}.dropdown-header{display:block;padding:.5rem 1.5rem;margin-bottom:0;font-size:.875rem;color:#636c72;white-space:nowrap}.dropdown-backdrop{position:fixed;top:0;right:0;bottom:0;left:0;z-index:990}.dropup .dropdown-menu{top:auto;bottom:100%;margin-bottom:.125rem}.btn-group,.btn-group-vertical{position:relative;display:-webkit-inline-box;display:-webkit-inline-flex;display:-ms-inline-flexbox;display:inline-flex;vertical-align:middle}.btn-group-vertical>.btn,.btn-group>.btn{position:relative;-webkit-box-flex:0;-webkit-flex:0 1 auto;-ms-flex:0 1 auto;flex:0 1 auto}.btn-group-vertical>.btn:hover,.btn-group>.btn:hover{z-index:2}.btn-group-vertical>.btn.active,.btn-group-vertical>.btn:active,.btn-group-vertical>.btn:focus,.btn-group>.btn.active,.btn-group>.btn:active,.btn-group>.btn:focus{z-index:2}.btn-group .btn+.btn,.btn-group .btn+.btn-group,.btn-group .btn-group+.btn,.btn-group .btn-group+.btn-group,.btn-group-vertical .btn+.btn,.btn-group-vertical .btn+.btn-group,.btn-group-vertical .btn-group+.btn,.btn-group-vertical .btn-group+.btn-group{margin-left:-1px}.btn-toolbar{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-pack:start;-webkit-justify-content:flex-start;-ms-flex-pack:start;justify-content:flex-start}.btn-toolbar .input-group{width:auto}.btn-group>.btn:not(:first-child):not(:last-child):not(.dropdown-toggle){border-radius:0}.btn-group>.btn:first-child{margin-left:0}.btn-group>.btn:first-child:not(:last-child):not(.dropdown-toggle){border-bottom-right-radius:0;border-top-right-radius:0}.btn-group>.btn:last-child:not(:first-child),.btn-group>.dropdown-toggle:not(:first-child){border-bottom-left-radius:0;border-top-left-radius:0}.btn-group>.btn-group{float:left}.btn-group>.btn-group:not(:first-child):not(:last-child)>.btn{border-radius:0}.btn-group>.btn-group:first-child:not(:last-child)>.btn:last-child,.btn-group>.btn-group:first-child:not(:last-child)>.dropdown-toggle{border-bottom-right-radius:0;border-top-right-radius:0}.btn-group>.btn-group:last-child:not(:first-child)>.btn:first-child{border-bottom-left-radius:0;border-top-left-radius:0}.btn-group .dropdown-toggle:active,.btn-group.open .dropdown-toggle{outline:0}.btn+.dropdown-toggle-split{padding-right:.75rem;padding-left:.75rem}.btn+.dropdown-toggle-split::after{margin-left:0}.btn-group-sm>.btn+.dropdown-toggle-split,.btn-sm+.dropdown-toggle-split{padding-right:.375rem;padding-left:.375rem}.btn-group-lg>.btn+.dropdown-toggle-split,.btn-lg+.dropdown-toggle-split{padding-right:1.125rem;padding-left:1.125rem}.btn-group-vertical{display:-webkit-inline-box;display:-webkit-inline-flex;display:-ms-inline-flexbox;display:inline-flex;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column;-webkit-box-align:start;-webkit-align-items:flex-start;-ms-flex-align:start;align-items:flex-start;-webkit-box-pack:center;-webkit-justify-content:center;-ms-flex-pack:center;justify-content:center}.btn-group-vertical .btn,.btn-group-vertical .btn-group{width:100%}.btn-group-vertical>.btn+.btn,.btn-group-vertical>.btn+.btn-group,.btn-group-vertical>.btn-group+.btn,.btn-group-vertical>.btn-group+.btn-group{margin-top:-1px;margin-left:0}.btn-group-vertical>.btn:not(:first-child):not(:last-child){border-radius:0}.btn-group-vertical>.btn:first-child:not(:last-child){border-bottom-right-radius:0;border-bottom-left-radius:0}.btn-group-vertical>.btn:last-child:not(:first-child){border-top-right-radius:0;border-top-left-radius:0}.btn-group-vertical>.btn-group:not(:first-child):not(:last-child)>.btn{border-radius:0}.btn-group-vertical>.btn-group:first-child:not(:last-child)>.btn:last-child,.btn-group-vertical>.btn-group:first-child:not(:last-child)>.dropdown-toggle{border-bottom-right-radius:0;border-bottom-left-radius:0}.btn-group-vertical>.btn-group:last-child:not(:first-child)>.btn:first-child{border-top-right-radius:0;border-top-left-radius:0}[data-toggle=buttons]>.btn input[type=checkbox],[data-toggle=buttons]>.btn input[type=radio],[data-toggle=buttons]>.btn-group>.btn input[type=checkbox],[data-toggle=buttons]>.btn-group>.btn input[type=radio]{position:absolute;clip:rect(0,0,0,0);pointer-events:none}.input-group{position:relative;display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;width:100%}.input-group .form-control{position:relative;z-index:2;-webkit-box-flex:1;-webkit-flex:1 1 auto;-ms-flex:1 1 auto;flex:1 1 auto;width:1%;margin-bottom:0}.input-group .form-control:active,.input-group .form-control:focus,.input-group .form-control:hover{z-index:3}.input-group .form-control,.input-group-addon,.input-group-btn{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column;-webkit-box-pack:center;-webkit-justify-content:center;-ms-flex-pack:center;justify-content:center}.input-group .form-control:not(:first-child):not(:last-child),.input-group-addon:not(:first-child):not(:last-child),.input-group-btn:not(:first-child):not(:last-child){border-radius:0}.input-group-addon,.input-group-btn{white-space:nowrap;vertical-align:middle}.input-group-addon{padding:.5rem .75rem;margin-bottom:0;font-size:1rem;font-weight:400;line-height:1.25;color:#464a4c;text-align:center;background-color:#eceeef;border:1px solid rgba(0,0,0,.15);border-radius:.25rem}.input-group-addon.form-control-sm,.input-group-sm>.input-group-addon,.input-group-sm>.input-group-btn>.input-group-addon.btn{padding:.25rem .5rem;font-size:.875rem;border-radius:.2rem}.input-group-addon.form-control-lg,.input-group-lg>.input-group-addon,.input-group-lg>.input-group-btn>.input-group-addon.btn{padding:.75rem 1.5rem;font-size:1.25rem;border-radius:.3rem}.input-group-addon input[type=checkbox],.input-group-addon input[type=radio]{margin-top:0}.input-group .form-control:not(:last-child),.input-group-addon:not(:last-child),.input-group-btn:not(:first-child)>.btn-group:not(:last-child)>.btn,.input-group-btn:not(:first-child)>.btn:not(:last-child):not(.dropdown-toggle),.input-group-btn:not(:last-child)>.btn,.input-group-btn:not(:last-child)>.btn-group>.btn,.input-group-btn:not(:last-child)>.dropdown-toggle{border-bottom-right-radius:0;border-top-right-radius:0}.input-group-addon:not(:last-child){border-right:0}.input-group .form-control:not(:first-child),.input-group-addon:not(:first-child),.input-group-btn:not(:first-child)>.btn,.input-group-btn:not(:first-child)>.btn-group>.btn,.input-group-btn:not(:first-child)>.dropdown-toggle,.input-group-btn:not(:last-child)>.btn-group:not(:first-child)>.btn,.input-group-btn:not(:last-child)>.btn:not(:first-child){border-bottom-left-radius:0;border-top-left-radius:0}.form-control+.input-group-addon:not(:first-child){border-left:0}.input-group-btn{position:relative;font-size:0;white-space:nowrap}.input-group-btn>.btn{position:relative;-webkit-box-flex:1;-webkit-flex:1 1 0%;-ms-flex:1 1 0%;flex:1 1 0%}.input-group-btn>.btn+.btn{margin-left:-1px}.input-group-btn>.btn:active,.input-group-btn>.btn:focus,.input-group-btn>.btn:hover{z-index:3}.input-group-btn:not(:last-child)>.btn,.input-group-btn:not(:last-child)>.btn-group{margin-right:-1px}.input-group-btn:not(:first-child)>.btn,.input-group-btn:not(:first-child)>.btn-group{z-index:2;margin-left:-1px}.input-group-btn:not(:first-child)>.btn-group:active,.input-group-btn:not(:first-child)>.btn-group:focus,.input-group-btn:not(:first-child)>.btn-group:hover,.input-group-btn:not(:first-child)>.btn:active,.input-group-btn:not(:first-child)>.btn:focus,.input-group-btn:not(:first-child)>.btn:hover{z-index:3}.custom-control{position:relative;display:-webkit-inline-box;display:-webkit-inline-flex;display:-ms-inline-flexbox;display:inline-flex;min-height:1.5rem;padding-left:1.5rem;margin-right:1rem;cursor:pointer}.custom-control-input{position:absolute;z-index:-1;opacity:0}.custom-control-input:checked~.custom-control-indicator{color:#fff;background-color:#0275d8}.custom-control-input:focus~.custom-control-indicator{-webkit-box-shadow:0 0 0 1px #fff,0 0 0 3px #0275d8;box-shadow:0 0 0 1px #fff,0 0 0 3px #0275d8}.custom-control-input:active~.custom-control-indicator{color:#fff;background-color:#8fcafe}.custom-control-input:disabled~.custom-control-indicator{cursor:not-allowed;background-color:#eceeef}.custom-control-input:disabled~.custom-control-description{color:#636c72;cursor:not-allowed}.custom-control-indicator{position:absolute;top:.25rem;left:0;display:block;width:1rem;height:1rem;pointer-events:none;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;background-color:#ddd;background-repeat:no-repeat;background-position:center center;-webkit-background-size:50% 50%;background-size:50% 50%}.custom-checkbox .custom-control-indicator{border-radius:.25rem}.custom-checkbox .custom-control-input:checked~.custom-control-indicator{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 8 8'%3E%3Cpath fill='%23fff' d='M6.564.75l-3.59 3.612-1.538-1.55L0 4.26 2.974 7.25 8 2.193z'/%3E%3C/svg%3E")}.custom-checkbox .custom-control-input:indeterminate~.custom-control-indicator{background-color:#0275d8;background-image:url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 4 4'%3E%3Cpath stroke='%23fff' d='M0 2h4'/%3E%3C/svg%3E")}.custom-radio .custom-control-indicator{border-radius:50%}.custom-radio .custom-control-input:checked~.custom-control-indicator{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3E%3Ccircle r='3' fill='%23fff'/%3E%3C/svg%3E")}.custom-controls-stacked{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column}.custom-controls-stacked .custom-control{margin-bottom:.25rem}.custom-controls-stacked .custom-control+.custom-control{margin-left:0}.custom-select{display:inline-block;max-width:100%;height:calc(2.25rem + 2px);padding:.375rem 1.75rem .375rem .75rem;line-height:1.25;color:#464a4c;vertical-align:middle;background:#fff url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 4 5'%3E%3Cpath fill='%23333' d='M2 0L0 2h4zm0 5L0 3h4z'/%3E%3C/svg%3E") no-repeat right .75rem center;-webkit-background-size:8px 10px;background-size:8px 10px;border:1px solid rgba(0,0,0,.15);border-radius:.25rem;-moz-appearance:none;-webkit-appearance:none}.custom-select:focus{border-color:#5cb3fd;outline:0}.custom-select:focus::-ms-value{color:#464a4c;background-color:#fff}.custom-select:disabled{color:#636c72;cursor:not-allowed;background-color:#eceeef}.custom-select::-ms-expand{opacity:0}.custom-select-sm{padding-top:.375rem;padding-bottom:.375rem;font-size:75%}.custom-file{position:relative;display:inline-block;max-width:100%;height:2.5rem;margin-bottom:0;cursor:pointer}.custom-file-input{min-width:14rem;max-width:100%;height:2.5rem;margin:0;filter:alpha(opacity=0);opacity:0}.custom-file-control{position:absolute;top:0;right:0;left:0;z-index:5;height:2.5rem;padding:.5rem 1rem;line-height:1.5;color:#464a4c;pointer-events:none;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;background-color:#fff;border:1px solid rgba(0,0,0,.15);border-radius:.25rem}.custom-file-control:lang(en)::after{content:"Choose file..."}.custom-file-control::before{position:absolute;top:-1px;right:-1px;bottom:-1px;z-index:6;display:block;height:2.5rem;padding:.5rem 1rem;line-height:1.5;color:#464a4c;background-color:#eceeef;border:1px solid rgba(0,0,0,.15);border-radius:0 .25rem .25rem 0}.custom-file-control:lang(en)::before{content:"Browse"}.nav{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;padding-left:0;margin-bottom:0;list-style:none}.nav-link{display:block;padding:.5em 1em}.nav-link:focus,.nav-link:hover{text-decoration:none}.nav-link.disabled{color:#636c72;cursor:not-allowed}.nav-tabs{border-bottom:1px solid #ddd}.nav-tabs .nav-item{margin-bottom:-1px}.nav-tabs .nav-link{border:1px solid transparent;border-top-right-radius:.25rem;border-top-left-radius:.25rem}.nav-tabs .nav-link:focus,.nav-tabs .nav-link:hover{border-color:#eceeef #eceeef #ddd}.nav-tabs .nav-link.disabled{color:#636c72;background-color:transparent;border-color:transparent}.nav-tabs .nav-item.show .nav-link,.nav-tabs .nav-link.active{color:#464a4c;background-color:#fff;border-color:#ddd #ddd #fff}.nav-tabs .dropdown-menu{margin-top:-1px;border-top-right-radius:0;border-top-left-radius:0}.nav-pills .nav-link{border-radius:.25rem}.nav-pills .nav-item.show .nav-link,.nav-pills .nav-link.active{color:#fff;cursor:default;background-color:#0275d8}.nav-fill .nav-item{-webkit-box-flex:1;-webkit-flex:1 1 auto;-ms-flex:1 1 auto;flex:1 1 auto;text-align:center}.nav-justified .nav-item{-webkit-box-flex:1;-webkit-flex:1 1 100%;-ms-flex:1 1 100%;flex:1 1 100%;text-align:center}.tab-content>.tab-pane{display:none}.tab-content>.active{display:block}.navbar{position:relative;display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column;padding:.5rem 1rem}.navbar-brand{display:inline-block;padding-top:.25rem;padding-bottom:.25rem;margin-right:1rem;font-size:1.25rem;line-height:inherit;white-space:nowrap}.navbar-brand:focus,.navbar-brand:hover{text-decoration:none}.navbar-nav{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column;padding-left:0;margin-bottom:0;list-style:none}.navbar-nav .nav-link{padding-right:0;padding-left:0}.navbar-text{display:inline-block;padding-top:.425rem;padding-bottom:.425rem}.navbar-toggler{-webkit-align-self:flex-start;-ms-flex-item-align:start;align-self:flex-start;padding:.25rem .75rem;font-size:1.25rem;line-height:1;background:0 0;border:1px solid transparent;border-radius:.25rem}.navbar-toggler:focus,.navbar-toggler:hover{text-decoration:none}.navbar-toggler-icon{display:inline-block;width:1.5em;height:1.5em;vertical-align:middle;content:"";background:no-repeat center center;-webkit-background-size:100% 100%;background-size:100% 100%}.navbar-toggler-left{position:absolute;left:1rem}.navbar-toggler-right{position:absolute;right:1rem}@media (max-width:575px){.navbar-toggleable .navbar-nav .dropdown-menu{position:static;float:none}.navbar-toggleable>.container{padding-right:0;padding-left:0}}@media (min-width:576px){.navbar-toggleable{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable .navbar-nav{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row}.navbar-toggleable .navbar-nav .nav-link{padding-right:.5rem;padding-left:.5rem}.navbar-toggleable>.container{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable .navbar-collapse{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important;width:100%}.navbar-toggleable .navbar-toggler{display:none}}@media (max-width:767px){.navbar-toggleable-sm .navbar-nav .dropdown-menu{position:static;float:none}.navbar-toggleable-sm>.container{padding-right:0;padding-left:0}}@media (min-width:768px){.navbar-toggleable-sm{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable-sm .navbar-nav{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row}.navbar-toggleable-sm .navbar-nav .nav-link{padding-right:.5rem;padding-left:.5rem}.navbar-toggleable-sm>.container{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable-sm .navbar-collapse{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important;width:100%}.navbar-toggleable-sm .navbar-toggler{display:none}}@media (max-width:991px){.navbar-toggleable-md .navbar-nav .dropdown-menu{position:static;float:none}.navbar-toggleable-md>.container{padding-right:0;padding-left:0}}@media (min-width:992px){.navbar-toggleable-md{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable-md .navbar-nav{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row}.navbar-toggleable-md .navbar-nav .nav-link{padding-right:.5rem;padding-left:.5rem}.navbar-toggleable-md>.container{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable-md .navbar-collapse{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important;width:100%}.navbar-toggleable-md .navbar-toggler{display:none}}@media (max-width:1199px){.navbar-toggleable-lg .navbar-nav .dropdown-menu{position:static;float:none}.navbar-toggleable-lg>.container{padding-right:0;padding-left:0}}@media (min-width:1200px){.navbar-toggleable-lg{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable-lg .navbar-nav{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row}.navbar-toggleable-lg .navbar-nav .nav-link{padding-right:.5rem;padding-left:.5rem}.navbar-toggleable-lg>.container{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable-lg .navbar-collapse{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important;width:100%}.navbar-toggleable-lg .navbar-toggler{display:none}}.navbar-toggleable-xl{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable-xl .navbar-nav .dropdown-menu{position:static;float:none}.navbar-toggleable-xl>.container{padding-right:0;padding-left:0}.navbar-toggleable-xl .navbar-nav{-webkit-box-orient:horizontal;-webkit-box-direction:normal;-webkit-flex-direction:row;-ms-flex-direction:row;flex-direction:row}.navbar-toggleable-xl .navbar-nav .nav-link{padding-right:.5rem;padding-left:.5rem}.navbar-toggleable-xl>.container{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-wrap:nowrap;-ms-flex-wrap:nowrap;flex-wrap:nowrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center}.navbar-toggleable-xl .navbar-collapse{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important;width:100%}.navbar-toggleable-xl .navbar-toggler{display:none}.navbar-light .navbar-brand,.navbar-light .navbar-toggler{color:rgba(0,0,0,.9)}.navbar-light .navbar-brand:focus,.navbar-light .navbar-brand:hover,.navbar-light .navbar-toggler:focus,.navbar-light .navbar-toggler:hover{color:rgba(0,0,0,.9)}.navbar-light .navbar-nav .nav-link{color:rgba(0,0,0,.5)}.navbar-light .navbar-nav .nav-link:focus,.navbar-light .navbar-nav .nav-link:hover{color:rgba(0,0,0,.7)}.navbar-light .navbar-nav .nav-link.disabled{color:rgba(0,0,0,.3)}.navbar-light .navbar-nav .active>.nav-link,.navbar-light .navbar-nav .nav-link.active,.navbar-light .navbar-nav .nav-link.open,.navbar-light .navbar-nav .open>.nav-link{color:rgba(0,0,0,.9)}.navbar-light .navbar-toggler{border-color:rgba(0,0,0,.1)}.navbar-light .navbar-toggler-icon{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg viewBox='0 0 32 32' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath stroke='rgba(0, 0, 0, 0.5)' stroke-width='2' stroke-linecap='round' stroke-miterlimit='10' d='M4 8h24M4 16h24M4 24h24'/%3E%3C/svg%3E")}.navbar-light .navbar-text{color:rgba(0,0,0,.5)}.navbar-inverse .navbar-brand,.navbar-inverse .navbar-toggler{color:#fff}.navbar-inverse .navbar-brand:focus,.navbar-inverse .navbar-brand:hover,.navbar-inverse .navbar-toggler:focus,.navbar-inverse .navbar-toggler:hover{color:#fff}.navbar-inverse .navbar-nav .nav-link{color:rgba(255,255,255,.5)}.navbar-inverse .navbar-nav .nav-link:focus,.navbar-inverse .navbar-nav .nav-link:hover{color:rgba(255,255,255,.75)}.navbar-inverse .navbar-nav .nav-link.disabled{color:rgba(255,255,255,.25)}.navbar-inverse .navbar-nav .active>.nav-link,.navbar-inverse .navbar-nav .nav-link.active,.navbar-inverse .navbar-nav .nav-link.open,.navbar-inverse .navbar-nav .open>.nav-link{color:#fff}.navbar-inverse .navbar-toggler{border-color:rgba(255,255,255,.1)}.navbar-inverse .navbar-toggler-icon{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg viewBox='0 0 32 32' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath stroke='rgba(255, 255, 255, 0.5)' stroke-width='2' stroke-linecap='round' stroke-miterlimit='10' d='M4 8h24M4 16h24M4 24h24'/%3E%3C/svg%3E")}.navbar-inverse .navbar-text{color:rgba(255,255,255,.5)}.card{position:relative;display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column;background-color:#fff;border:1px solid rgba(0,0,0,.125);border-radius:.25rem}.card-block{-webkit-box-flex:1;-webkit-flex:1 1 auto;-ms-flex:1 1 auto;flex:1 1 auto;padding:1.25rem}.card-title{margin-bottom:.75rem}.card-subtitle{margin-top:-.375rem;margin-bottom:0}.card-text:last-child{margin-bottom:0}.card-link:hover{text-decoration:none}.card-link+.card-link{margin-left:1.25rem}.card>.list-group:first-child .list-group-item:first-child{border-top-right-radius:.25rem;border-top-left-radius:.25rem}.card>.list-group:last-child .list-group-item:last-child{border-bottom-right-radius:.25rem;border-bottom-left-radius:.25rem}.card-header{padding:.75rem 1.25rem;margin-bottom:0;background-color:#f7f7f9;border-bottom:1px solid rgba(0,0,0,.125)}.card-header:first-child{border-radius:calc(.25rem - 1px) calc(.25rem - 1px) 0 0}.card-footer{padding:.75rem 1.25rem;background-color:#f7f7f9;border-top:1px solid rgba(0,0,0,.125)}.card-footer:last-child{border-radius:0 0 calc(.25rem - 1px) calc(.25rem - 1px)}.card-header-tabs{margin-right:-.625rem;margin-bottom:-.75rem;margin-left:-.625rem;border-bottom:0}.card-header-pills{margin-right:-.625rem;margin-left:-.625rem}.card-primary{background-color:#0275d8;border-color:#0275d8}.card-primary .card-footer,.card-primary .card-header{background-color:transparent}.card-success{background-color:#5cb85c;border-color:#5cb85c}.card-success .card-footer,.card-success .card-header{background-color:transparent}.card-info{background-color:#5bc0de;border-color:#5bc0de}.card-info .card-footer,.card-info .card-header{background-color:transparent}.card-warning{background-color:#f0ad4e;border-color:#f0ad4e}.card-warning .card-footer,.card-warning .card-header{background-color:transparent}.card-danger{background-color:#d9534f;border-color:#d9534f}.card-danger .card-footer,.card-danger .card-header{background-color:transparent}.card-outline-primary{background-color:transparent;border-color:#0275d8}.card-outline-secondary{background-color:transparent;border-color:#ccc}.card-outline-info{background-color:transparent;border-color:#5bc0de}.card-outline-success{background-color:transparent;border-color:#5cb85c}.card-outline-warning{background-color:transparent;border-color:#f0ad4e}.card-outline-danger{background-color:transparent;border-color:#d9534f}.card-inverse{color:rgba(255,255,255,.65)}.card-inverse .card-footer,.card-inverse .card-header{background-color:transparent;border-color:rgba(255,255,255,.2)}.card-inverse .card-blockquote,.card-inverse .card-footer,.card-inverse .card-header,.card-inverse .card-title{color:#fff}.card-inverse .card-blockquote .blockquote-footer,.card-inverse .card-link,.card-inverse .card-subtitle,.card-inverse .card-text{color:rgba(255,255,255,.65)}.card-inverse .card-link:focus,.card-inverse .card-link:hover{color:#fff}.card-blockquote{padding:0;margin-bottom:0;border-left:0}.card-img{border-radius:calc(.25rem - 1px)}.card-img-overlay{position:absolute;top:0;right:0;bottom:0;left:0;padding:1.25rem}.card-img-top{border-top-right-radius:calc(.25rem - 1px);border-top-left-radius:calc(.25rem - 1px)}.card-img-bottom{border-bottom-right-radius:calc(.25rem - 1px);border-bottom-left-radius:calc(.25rem - 1px)}@media (min-width:576px){.card-deck{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-flow:row wrap;-ms-flex-flow:row wrap;flex-flow:row wrap}.card-deck .card{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-flex:1;-webkit-flex:1 0 0%;-ms-flex:1 0 0%;flex:1 0 0%;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column}.card-deck .card:not(:first-child){margin-left:15px}.card-deck .card:not(:last-child){margin-right:15px}}@media (min-width:576px){.card-group{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-flow:row wrap;-ms-flex-flow:row wrap;flex-flow:row wrap}.card-group .card{-webkit-box-flex:1;-webkit-flex:1 0 0%;-ms-flex:1 0 0%;flex:1 0 0%}.card-group .card+.card{margin-left:0;border-left:0}.card-group .card:first-child{border-bottom-right-radius:0;border-top-right-radius:0}.card-group .card:first-child .card-img-top{border-top-right-radius:0}.card-group .card:first-child .card-img-bottom{border-bottom-right-radius:0}.card-group .card:last-child{border-bottom-left-radius:0;border-top-left-radius:0}.card-group .card:last-child .card-img-top{border-top-left-radius:0}.card-group .card:last-child .card-img-bottom{border-bottom-left-radius:0}.card-group .card:not(:first-child):not(:last-child){border-radius:0}.card-group .card:not(:first-child):not(:last-child) .card-img-bottom,.card-group .card:not(:first-child):not(:last-child) .card-img-top{border-radius:0}}@media (min-width:576px){.card-columns{-webkit-column-count:3;-moz-column-count:3;column-count:3;-webkit-column-gap:1.25rem;-moz-column-gap:1.25rem;column-gap:1.25rem}.card-columns .card{display:inline-block;width:100%;margin-bottom:.75rem}}.breadcrumb{padding:.75rem 1rem;margin-bottom:1rem;list-style:none;background-color:#eceeef;border-radius:.25rem}.breadcrumb::after{display:block;content:"";clear:both}.breadcrumb-item{float:left}.breadcrumb-item+.breadcrumb-item::before{display:inline-block;padding-right:.5rem;padding-left:.5rem;color:#636c72;content:"/"}.breadcrumb-item+.breadcrumb-item:hover::before{text-decoration:underline}.breadcrumb-item+.breadcrumb-item:hover::before{text-decoration:none}.breadcrumb-item.active{color:#636c72}.pagination{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;padding-left:0;list-style:none;border-radius:.25rem}.page-item:first-child .page-link{margin-left:0;border-bottom-left-radius:.25rem;border-top-left-radius:.25rem}.page-item:last-child .page-link{border-bottom-right-radius:.25rem;border-top-right-radius:.25rem}.page-item.active .page-link{z-index:2;color:#fff;background-color:#0275d8;border-color:#0275d8}.page-item.disabled .page-link{color:#636c72;pointer-events:none;cursor:not-allowed;background-color:#fff;border-color:#ddd}.page-link{position:relative;display:block;padding:.5rem .75rem;margin-left:-1px;line-height:1.25;color:#0275d8;background-color:#fff;border:1px solid #ddd}.page-link:focus,.page-link:hover{color:#014c8c;text-decoration:none;background-color:#eceeef;border-color:#ddd}.pagination-lg .page-link{padding:.75rem 1.5rem;font-size:1.25rem}.pagination-lg .page-item:first-child .page-link{border-bottom-left-radius:.3rem;border-top-left-radius:.3rem}.pagination-lg .page-item:last-child .page-link{border-bottom-right-radius:.3rem;border-top-right-radius:.3rem}.pagination-sm .page-link{padding:.25rem .5rem;font-size:.875rem}.pagination-sm .page-item:first-child .page-link{border-bottom-left-radius:.2rem;border-top-left-radius:.2rem}.pagination-sm .page-item:last-child .page-link{border-bottom-right-radius:.2rem;border-top-right-radius:.2rem}.badge{display:inline-block;padding:.25em .4em;font-size:75%;font-weight:700;line-height:1;color:#fff;text-align:center;white-space:nowrap;vertical-align:baseline;border-radius:.25rem}.badge:empty{display:none}.btn .badge{position:relative;top:-1px}a.badge:focus,a.badge:hover{color:#fff;text-decoration:none;cursor:pointer}.badge-pill{padding-right:.6em;padding-left:.6em;border-radius:10rem}.badge-default{background-color:#636c72}.badge-default[href]:focus,.badge-default[href]:hover{background-color:#4b5257}.badge-primary{background-color:#0275d8}.badge-primary[href]:focus,.badge-primary[href]:hover{background-color:#025aa5}.badge-success{background-color:#5cb85c}.badge-success[href]:focus,.badge-success[href]:hover{background-color:#449d44}.badge-info{background-color:#5bc0de}.badge-info[href]:focus,.badge-info[href]:hover{background-color:#31b0d5}.badge-warning{background-color:#f0ad4e}.badge-warning[href]:focus,.badge-warning[href]:hover{background-color:#ec971f}.badge-danger{background-color:#d9534f}.badge-danger[href]:focus,.badge-danger[href]:hover{background-color:#c9302c}.jumbotron{padding:2rem 1rem;margin-bottom:2rem;background-color:#eceeef;border-radius:.3rem}@media (min-width:576px){.jumbotron{padding:4rem 2rem}}.jumbotron-hr{border-top-color:#d0d5d8}.jumbotron-fluid{padding-right:0;padding-left:0;border-radius:0}.alert{padding:.75rem 1.25rem;margin-bottom:1rem;border:1px solid transparent;border-radius:.25rem}.alert-heading{color:inherit}.alert-link{font-weight:700}.alert-dismissible .close{position:relative;top:-.75rem;right:-1.25rem;padding:.75rem 1.25rem;color:inherit}.alert-success{background-color:#dff0d8;border-color:#d0e9c6;color:#3c763d}.alert-success hr{border-top-color:#c1e2b3}.alert-success .alert-link{color:#2b542c}.alert-info{background-color:#d9edf7;border-color:#bcdff1;color:#31708f}.alert-info hr{border-top-color:#a6d5ec}.alert-info .alert-link{color:#245269}.alert-warning{background-color:#fcf8e3;border-color:#faf2cc;color:#8a6d3b}.alert-warning hr{border-top-color:#f7ecb5}.alert-warning .alert-link{color:#66512c}.alert-danger{background-color:#f2dede;border-color:#ebcccc;color:#a94442}.alert-danger hr{border-top-color:#e4b9b9}.alert-danger .alert-link{color:#843534}@-webkit-keyframes progress-bar-stripes{from{background-position:1rem 0}to{background-position:0 0}}@-o-keyframes progress-bar-stripes{from{background-position:1rem 0}to{background-position:0 0}}@keyframes progress-bar-stripes{from{background-position:1rem 0}to{background-position:0 0}}.progress{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;overflow:hidden;font-size:.75rem;line-height:1rem;text-align:center;background-color:#eceeef;border-radius:.25rem}.progress-bar{height:1rem;color:#fff;background-color:#0275d8}.progress-bar-striped{background-image:-webkit-linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent);background-image:-o-linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent);background-image:linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent);-webkit-background-size:1rem 1rem;background-size:1rem 1rem}.progress-bar-animated{-webkit-animation:progress-bar-stripes 1s linear infinite;-o-animation:progress-bar-stripes 1s linear infinite;animation:progress-bar-stripes 1s linear infinite}.media{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-align:start;-webkit-align-items:flex-start;-ms-flex-align:start;align-items:flex-start}.media-body{-webkit-box-flex:1;-webkit-flex:1 1 0%;-ms-flex:1 1 0%;flex:1 1 0%}.list-group{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column;padding-left:0;margin-bottom:0}.list-group-item-action{width:100%;color:#464a4c;text-align:inherit}.list-group-item-action .list-group-item-heading{color:#292b2c}.list-group-item-action:focus,.list-group-item-action:hover{color:#464a4c;text-decoration:none;background-color:#f7f7f9}.list-group-item-action:active{color:#292b2c;background-color:#eceeef}.list-group-item{position:relative;display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-flex-flow:row wrap;-ms-flex-flow:row wrap;flex-flow:row wrap;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center;padding:.75rem 1.25rem;margin-bottom:-1px;background-color:#fff;border:1px solid rgba(0,0,0,.125)}.list-group-item:first-child{border-top-right-radius:.25rem;border-top-left-radius:.25rem}.list-group-item:last-child{margin-bottom:0;border-bottom-right-radius:.25rem;border-bottom-left-radius:.25rem}.list-group-item:focus,.list-group-item:hover{text-decoration:none}.list-group-item.disabled,.list-group-item:disabled{color:#636c72;cursor:not-allowed;background-color:#fff}.list-group-item.disabled .list-group-item-heading,.list-group-item:disabled .list-group-item-heading{color:inherit}.list-group-item.disabled .list-group-item-text,.list-group-item:disabled .list-group-item-text{color:#636c72}.list-group-item.active{z-index:2;color:#fff;background-color:#0275d8;border-color:#0275d8}.list-group-item.active .list-group-item-heading,.list-group-item.active .list-group-item-heading>.small,.list-group-item.active .list-group-item-heading>small{color:inherit}.list-group-item.active .list-group-item-text{color:#daeeff}.list-group-flush .list-group-item{border-right:0;border-left:0;border-radius:0}.list-group-flush:first-child .list-group-item:first-child{border-top:0}.list-group-flush:last-child .list-group-item:last-child{border-bottom:0}.list-group-item-success{color:#3c763d;background-color:#dff0d8}a.list-group-item-success,button.list-group-item-success{color:#3c763d}a.list-group-item-success .list-group-item-heading,button.list-group-item-success .list-group-item-heading{color:inherit}a.list-group-item-success:focus,a.list-group-item-success:hover,button.list-group-item-success:focus,button.list-group-item-success:hover{color:#3c763d;background-color:#d0e9c6}a.list-group-item-success.active,button.list-group-item-success.active{color:#fff;background-color:#3c763d;border-color:#3c763d}.list-group-item-info{color:#31708f;background-color:#d9edf7}a.list-group-item-info,button.list-group-item-info{color:#31708f}a.list-group-item-info .list-group-item-heading,button.list-group-item-info .list-group-item-heading{color:inherit}a.list-group-item-info:focus,a.list-group-item-info:hover,button.list-group-item-info:focus,button.list-group-item-info:hover{color:#31708f;background-color:#c4e3f3}a.list-group-item-info.active,button.list-group-item-info.active{color:#fff;background-color:#31708f;border-color:#31708f}.list-group-item-warning{color:#8a6d3b;background-color:#fcf8e3}a.list-group-item-warning,button.list-group-item-warning{color:#8a6d3b}a.list-group-item-warning .list-group-item-heading,button.list-group-item-warning .list-group-item-heading{color:inherit}a.list-group-item-warning:focus,a.list-group-item-warning:hover,button.list-group-item-warning:focus,button.list-group-item-warning:hover{color:#8a6d3b;background-color:#faf2cc}a.list-group-item-warning.active,button.list-group-item-warning.active{color:#fff;background-color:#8a6d3b;border-color:#8a6d3b}.list-group-item-danger{color:#a94442;background-color:#f2dede}a.list-group-item-danger,button.list-group-item-danger{color:#a94442}a.list-group-item-danger .list-group-item-heading,button.list-group-item-danger .list-group-item-heading{color:inherit}a.list-group-item-danger:focus,a.list-group-item-danger:hover,button.list-group-item-danger:focus,button.list-group-item-danger:hover{color:#a94442;background-color:#ebcccc}a.list-group-item-danger.active,button.list-group-item-danger.active{color:#fff;background-color:#a94442;border-color:#a94442}.embed-responsive{position:relative;display:block;width:100%;padding:0;overflow:hidden}.embed-responsive::before{display:block;content:""}.embed-responsive .embed-responsive-item,.embed-responsive embed,.embed-responsive iframe,.embed-responsive object,.embed-responsive video{position:absolute;top:0;bottom:0;left:0;width:100%;height:100%;border:0}.embed-responsive-21by9::before{padding-top:42.857143%}.embed-responsive-16by9::before{padding-top:56.25%}.embed-responsive-4by3::before{padding-top:75%}.embed-responsive-1by1::before{padding-top:100%}.close{float:right;font-size:1.5rem;font-weight:700;line-height:1;color:#000;text-shadow:0 1px 0 #fff;opacity:.5}.close:focus,.close:hover{color:#000;text-decoration:none;cursor:pointer;opacity:.75}button.close{padding:0;cursor:pointer;background:0 0;border:0;-webkit-appearance:none}.modal-open{overflow:hidden}.modal{position:fixed;top:0;right:0;bottom:0;left:0;z-index:1050;display:none;overflow:hidden;outline:0}.modal.fade .modal-dialog{-webkit-transition:-webkit-transform .3s ease-out;transition:-webkit-transform .3s ease-out;-o-transition:-o-transform .3s ease-out;transition:transform .3s ease-out;transition:transform .3s ease-out,-webkit-transform .3s ease-out,-o-transform .3s ease-out;-webkit-transform:translate(0,-25%);-o-transform:translate(0,-25%);transform:translate(0,-25%)}.modal.show .modal-dialog{-webkit-transform:translate(0,0);-o-transform:translate(0,0);transform:translate(0,0)}.modal-open .modal{overflow-x:hidden;overflow-y:auto}.modal-dialog{position:relative;width:auto;margin:10px}.modal-content{position:relative;display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-orient:vertical;-webkit-box-direction:normal;-webkit-flex-direction:column;-ms-flex-direction:column;flex-direction:column;background-color:#fff;-webkit-background-clip:padding-box;background-clip:padding-box;border:1px solid rgba(0,0,0,.2);border-radius:.3rem;outline:0}.modal-backdrop{position:fixed;top:0;right:0;bottom:0;left:0;z-index:1040;background-color:#000}.modal-backdrop.fade{opacity:0}.modal-backdrop.show{opacity:.5}.modal-header{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:justify;-webkit-justify-content:space-between;-ms-flex-pack:justify;justify-content:space-between;padding:15px;border-bottom:1px solid #eceeef}.modal-title{margin-bottom:0;line-height:1.5}.modal-body{position:relative;-webkit-box-flex:1;-webkit-flex:1 1 auto;-ms-flex:1 1 auto;flex:1 1 auto;padding:15px}.modal-footer{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:end;-webkit-justify-content:flex-end;-ms-flex-pack:end;justify-content:flex-end;padding:15px;border-top:1px solid #eceeef}.modal-footer>:not(:first-child){margin-left:.25rem}.modal-footer>:not(:last-child){margin-right:.25rem}.modal-scrollbar-measure{position:absolute;top:-9999px;width:50px;height:50px;overflow:scroll}@media (min-width:576px){.modal-dialog{max-width:500px;margin:30px auto}.modal-sm{max-width:300px}}@media (min-width:992px){.modal-lg{max-width:800px}}.tooltip{position:absolute;z-index:1070;display:block;font-family:-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-style:normal;font-weight:400;letter-spacing:normal;line-break:auto;line-height:1.5;text-align:left;text-align:start;text-decoration:none;text-shadow:none;text-transform:none;white-space:normal;word-break:normal;word-spacing:normal;font-size:.875rem;word-wrap:break-word;opacity:0}.tooltip.show{opacity:.9}.tooltip.bs-tether-element-attached-bottom,.tooltip.tooltip-top{padding:5px 0;margin-top:-3px}.tooltip.bs-tether-element-attached-bottom .tooltip-inner::before,.tooltip.tooltip-top .tooltip-inner::before{bottom:0;left:50%;margin-left:-5px;content:"";border-width:5px 5px 0;border-top-color:#000}.tooltip.bs-tether-element-attached-left,.tooltip.tooltip-right{padding:0 5px;margin-left:3px}.tooltip.bs-tether-element-attached-left .tooltip-inner::before,.tooltip.tooltip-right .tooltip-inner::before{top:50%;left:0;margin-top:-5px;content:"";border-width:5px 5px 5px 0;border-right-color:#000}.tooltip.bs-tether-element-attached-top,.tooltip.tooltip-bottom{padding:5px 0;margin-top:3px}.tooltip.bs-tether-element-attached-top .tooltip-inner::before,.tooltip.tooltip-bottom .tooltip-inner::before{top:0;left:50%;margin-left:-5px;content:"";border-width:0 5px 5px;border-bottom-color:#000}.tooltip.bs-tether-element-attached-right,.tooltip.tooltip-left{padding:0 5px;margin-left:-3px}.tooltip.bs-tether-element-attached-right .tooltip-inner::before,.tooltip.tooltip-left .tooltip-inner::before{top:50%;right:0;margin-top:-5px;content:"";border-width:5px 0 5px 5px;border-left-color:#000}.tooltip-inner{max-width:200px;padding:3px 8px;color:#fff;text-align:center;background-color:#000;border-radius:.25rem}.tooltip-inner::before{position:absolute;width:0;height:0;border-color:transparent;border-style:solid}.popover{position:absolute;top:0;left:0;z-index:1060;display:block;max-width:276px;padding:1px;font-family:-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-style:normal;font-weight:400;letter-spacing:normal;line-break:auto;line-height:1.5;text-align:left;text-align:start;text-decoration:none;text-shadow:none;text-transform:none;white-space:normal;word-break:normal;word-spacing:normal;font-size:.875rem;word-wrap:break-word;background-color:#fff;-webkit-background-clip:padding-box;background-clip:padding-box;border:1px solid rgba(0,0,0,.2);border-radius:.3rem}.popover.bs-tether-element-attached-bottom,.popover.popover-top{margin-top:-10px}.popover.bs-tether-element-attached-bottom::after,.popover.bs-tether-element-attached-bottom::before,.popover.popover-top::after,.popover.popover-top::before{left:50%;border-bottom-width:0}.popover.bs-tether-element-attached-bottom::before,.popover.popover-top::before{bottom:-11px;margin-left:-11px;border-top-color:rgba(0,0,0,.25)}.popover.bs-tether-element-attached-bottom::after,.popover.popover-top::after{bottom:-10px;margin-left:-10px;border-top-color:#fff}.popover.bs-tether-element-attached-left,.popover.popover-right{margin-left:10px}.popover.bs-tether-element-attached-left::after,.popover.bs-tether-element-attached-left::before,.popover.popover-right::after,.popover.popover-right::before{top:50%;border-left-width:0}.popover.bs-tether-element-attached-left::before,.popover.popover-right::before{left:-11px;margin-top:-11px;border-right-color:rgba(0,0,0,.25)}.popover.bs-tether-element-attached-left::after,.popover.popover-right::after{left:-10px;margin-top:-10px;border-right-color:#fff}.popover.bs-tether-element-attached-top,.popover.popover-bottom{margin-top:10px}.popover.bs-tether-element-attached-top::after,.popover.bs-tether-element-attached-top::before,.popover.popover-bottom::after,.popover.popover-bottom::before{left:50%;border-top-width:0}.popover.bs-tether-element-attached-top::before,.popover.popover-bottom::before{top:-11px;margin-left:-11px;border-bottom-color:rgba(0,0,0,.25)}.popover.bs-tether-element-attached-top::after,.popover.popover-bottom::after{top:-10px;margin-left:-10px;border-bottom-color:#f7f7f7}.popover.bs-tether-element-attached-top .popover-title::before,.popover.popover-bottom .popover-title::before{position:absolute;top:0;left:50%;display:block;width:20px;margin-left:-10px;content:"";border-bottom:1px solid #f7f7f7}.popover.bs-tether-element-attached-right,.popover.popover-left{margin-left:-10px}.popover.bs-tether-element-attached-right::after,.popover.bs-tether-element-attached-right::before,.popover.popover-left::after,.popover.popover-left::before{top:50%;border-right-width:0}.popover.bs-tether-element-attached-right::before,.popover.popover-left::before{right:-11px;margin-top:-11px;border-left-color:rgba(0,0,0,.25)}.popover.bs-tether-element-attached-right::after,.popover.popover-left::after{right:-10px;margin-top:-10px;border-left-color:#fff}.popover-title{padding:8px 14px;margin-bottom:0;font-size:1rem;background-color:#f7f7f7;border-bottom:1px solid #ebebeb;border-top-right-radius:calc(.3rem - 1px);border-top-left-radius:calc(.3rem - 1px)}.popover-title:empty{display:none}.popover-content{padding:9px 14px}.popover::after,.popover::before{position:absolute;display:block;width:0;height:0;border-color:transparent;border-style:solid}.popover::before{content:"";border-width:11px}.popover::after{content:"";border-width:10px}.carousel{position:relative}.carousel-inner{position:relative;width:100%;overflow:hidden}.carousel-item{position:relative;display:none;width:100%}@media (-webkit-transform-3d){.carousel-item{-webkit-transition:-webkit-transform .6s ease-in-out;transition:-webkit-transform .6s ease-in-out;-o-transition:-o-transform .6s ease-in-out;transition:transform .6s ease-in-out;transition:transform .6s ease-in-out,-webkit-transform .6s ease-in-out,-o-transform .6s ease-in-out;-webkit-backface-visibility:hidden;backface-visibility:hidden;-webkit-perspective:1000px;perspective:1000px}}@supports ((-webkit-transform:translate3d(0,0,0)) or (transform:translate3d(0,0,0))){.carousel-item{-webkit-transition:-webkit-transform .6s ease-in-out;transition:-webkit-transform .6s ease-in-out;-o-transition:-o-transform .6s ease-in-out;transition:transform .6s ease-in-out;transition:transform .6s ease-in-out,-webkit-transform .6s ease-in-out,-o-transform .6s ease-in-out;-webkit-backface-visibility:hidden;backface-visibility:hidden;-webkit-perspective:1000px;perspective:1000px}}.carousel-item-next,.carousel-item-prev,.carousel-item.active{display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex}.carousel-item-next,.carousel-item-prev{position:absolute;top:0}@media (-webkit-transform-3d){.carousel-item-next.carousel-item-left,.carousel-item-prev.carousel-item-right{-webkit-transform:translate3d(0,0,0);transform:translate3d(0,0,0)}.active.carousel-item-right,.carousel-item-next{-webkit-transform:translate3d(100%,0,0);transform:translate3d(100%,0,0)}.active.carousel-item-left,.carousel-item-prev{-webkit-transform:translate3d(-100%,0,0);transform:translate3d(-100%,0,0)}}@supports ((-webkit-transform:translate3d(0,0,0)) or (transform:translate3d(0,0,0))){.carousel-item-next.carousel-item-left,.carousel-item-prev.carousel-item-right{-webkit-transform:translate3d(0,0,0);transform:translate3d(0,0,0)}.active.carousel-item-right,.carousel-item-next{-webkit-transform:translate3d(100%,0,0);transform:translate3d(100%,0,0)}.active.carousel-item-left,.carousel-item-prev{-webkit-transform:translate3d(-100%,0,0);transform:translate3d(-100%,0,0)}}.carousel-control-next,.carousel-control-prev{position:absolute;top:0;bottom:0;display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-align:center;-webkit-align-items:center;-ms-flex-align:center;align-items:center;-webkit-box-pack:center;-webkit-justify-content:center;-ms-flex-pack:center;justify-content:center;width:15%;color:#fff;text-align:center;opacity:.5}.carousel-control-next:focus,.carousel-control-next:hover,.carousel-control-prev:focus,.carousel-control-prev:hover{color:#fff;text-decoration:none;outline:0;opacity:.9}.carousel-control-prev{left:0}.carousel-control-next{right:0}.carousel-control-next-icon,.carousel-control-prev-icon{display:inline-block;width:20px;height:20px;background:transparent no-repeat center center;-webkit-background-size:100% 100%;background-size:100% 100%}.carousel-control-prev-icon{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23fff' viewBox='0 0 8 8'%3E%3Cpath d='M4 0l-4 4 4 4 1.5-1.5-2.5-2.5 2.5-2.5-1.5-1.5z'/%3E%3C/svg%3E")}.carousel-control-next-icon{background-image:url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23fff' viewBox='0 0 8 8'%3E%3Cpath d='M1.5 0l-1.5 1.5 2.5 2.5-2.5 2.5 1.5 1.5 4-4-4-4z'/%3E%3C/svg%3E")}.carousel-indicators{position:absolute;right:0;bottom:10px;left:0;z-index:15;display:-webkit-box;display:-webkit-flex;display:-ms-flexbox;display:flex;-webkit-box-pack:center;-webkit-justify-content:center;-ms-flex-pack:center;justify-content:center;padding-left:0;margin-right:15%;margin-left:15%;list-style:none}.carousel-indicators li{position:relative;-webkit-box-flex:1;-webkit-flex:1 0 auto;-ms-flex:1 0 auto;flex:1 0 auto;max-width:30px;height:3px;margin-right:3px;margin-left:3px;text-indent:-999px;cursor:pointer;background-color:rgba(255,255,255,.5)}.carousel-indicators li::before{position:absolute;top:-10px;left:0;display:inline-block;width:100%;height:10px;content:""}.carousel-indicators li::after{position:absolute;bottom:-10px;left:0;display:inline-block;width:100%;height:10px;content:""}.carousel-indicators .active{background-color:#fff}.carousel-caption{position:absolute;right:15%;bottom:20px;left:15%;z-index:10;padding-top:20px;padding-bottom:20px;color:#fff;text-align:center}.align-baseline{vertical-align:baseline!important}.align-top{vertical-align:top!important}.align-middle{vertical-align:middle!important}.align-bottom{vertical-align:bottom!important}.align-text-bottom{vertical-align:text-bottom!important}.align-text-top{vertical-align:text-top!important}.bg-faded{background-color:#f7f7f7}.bg-primary{background-color:#0275d8!important}a.bg-primary:focus,a.bg-primary:hover{background-color:#025aa5!important}.bg-success{background-color:#5cb85c!important}a.bg-success:focus,a.bg-success:hover{background-color:#449d44!important}.bg-info{background-color:#5bc0de!important}a.bg-info:focus,a.bg-info:hover{background-color:#31b0d5!important}.bg-warning{background-color:#f0ad4e!important}a.bg-warning:focus,a.bg-warning:hover{background-color:#ec971f!important}.bg-danger{background-color:#d9534f!important}a.bg-danger:focus,a.bg-danger:hover{background-color:#c9302c!important}.bg-inverse{background-color:#292b2c!important}a.bg-inverse:focus,a.bg-inverse:hover{background-color:#101112!important}.border-0{border:0!important}.border-top-0{border-top:0!important}.border-right-0{border-right:0!important}.border-bottom-0{border-bottom:0!important}.border-left-0{border-left:0!important}.rounded{border-radius:.25rem}.rounded-top{border-top-right-radius:.25rem;border-top-left-radius:.25rem}.rounded-right{border-bottom-right-radius:.25rem;border-top-right-radius:.25rem}.rounded-bottom{border-bottom-right-radius:.25rem;border-bottom-left-radius:.25rem}.rounded-left{border-bottom-left-radius:.25rem;border-top-left-radius:.25rem}.rounded-circle{border-radius:50%}.rounded-0{border-radius:0}.clearfix::after{display:block;content:"";clear:both}.d-none{display:none!important}.d-inline{display:inline!important}.d-inline-block{display:inline-block!important}.d-block{display:block!important}.d-table{display:table!important}.d-table-cell{display:table-cell!important}.d-flex{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important}.d-inline-flex{display:-webkit-inline-box!important;display:-webkit-inline-flex!important;display:-ms-inline-flexbox!important;display:inline-flex!important}@media (min-width:576px){.d-sm-none{display:none!important}.d-sm-inline{display:inline!important}.d-sm-inline-block{display:inline-block!important}.d-sm-block{display:block!important}.d-sm-table{display:table!important}.d-sm-table-cell{display:table-cell!important}.d-sm-flex{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important}.d-sm-inline-flex{display:-webkit-inline-box!important;display:-webkit-inline-flex!important;display:-ms-inline-flexbox!important;display:inline-flex!important}}@media (min-width:768px){.d-md-none{display:none!important}.d-md-inline{display:inline!important}.d-md-inline-block{display:inline-block!important}.d-md-block{display:block!important}.d-md-table{display:table!important}.d-md-table-cell{display:table-cell!important}.d-md-flex{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important}.d-md-inline-flex{display:-webkit-inline-box!important;display:-webkit-inline-flex!important;display:-ms-inline-flexbox!important;display:inline-flex!important}}@media (min-width:992px){.d-lg-none{display:none!important}.d-lg-inline{display:inline!important}.d-lg-inline-block{display:inline-block!important}.d-lg-block{display:block!important}.d-lg-table{display:table!important}.d-lg-table-cell{display:table-cell!important}.d-lg-flex{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important}.d-lg-inline-flex{display:-webkit-inline-box!important;display:-webkit-inline-flex!important;display:-ms-inline-flexbox!important;display:inline-flex!important}}@media (min-width:1200px){.d-xl-none{display:none!important}.d-xl-inline{display:inline!important}.d-xl-inline-block{display:inline-block!important}.d-xl-block{display:block!important}.d-xl-table{display:table!important}.d-xl-table-cell{display:table-cell!important}.d-xl-flex{display:-webkit-box!important;display:-webkit-flex!important;display:-ms-flexbox!important;display:flex!important}.d-xl-inline-flex{display:-webkit-inline-box!important;display:-webkit-inline-flex!important;display:-ms-inline-flexbox!important;display:inline-flex!important}}.flex-first{-webkit-box-ordinal-group:0;-webkit-order:-1;-ms-flex-order:-1;order:-1}.flex-last{-webkit-box-ordinal-group:2;-webkit-order:1;-ms-flex-order:1;order:1}.flex-unordered{-webkit-box-ordinal-group:1;-webkit-order:0;-ms-flex-order:0;order:0}.flex-row{-webkit-box-orient:horizontal!important;-webkit-box-direction:normal!important;-webkit-flex-direction:row!important;-ms-flex-direction:row!important;flex-direction:row!important}.flex-column{-webkit-box-orient:vertical!important;-webkit-box-direction:normal!important;-webkit-flex-direction:column!important;-ms-flex-direction:column!important;flex-direction:column!important}.flex-row-reverse{-webkit-box-orient:horizontal!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:row-reverse!important;-ms-flex-direction:row-reverse!important;flex-direction:row-reverse!important}.flex-column-reverse{-webkit-box-orient:vertical!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:column-reverse!important;-ms-flex-direction:column-reverse!important;flex-direction:column-reverse!important}.flex-wrap{-webkit-flex-wrap:wrap!important;-ms-flex-wrap:wrap!important;flex-wrap:wrap!important}.flex-nowrap{-webkit-flex-wrap:nowrap!important;-ms-flex-wrap:nowrap!important;flex-wrap:nowrap!important}.flex-wrap-reverse{-webkit-flex-wrap:wrap-reverse!important;-ms-flex-wrap:wrap-reverse!important;flex-wrap:wrap-reverse!important}.justify-content-start{-webkit-box-pack:start!important;-webkit-justify-content:flex-start!important;-ms-flex-pack:start!important;justify-content:flex-start!important}.justify-content-end{-webkit-box-pack:end!important;-webkit-justify-content:flex-end!important;-ms-flex-pack:end!important;justify-content:flex-end!important}.justify-content-center{-webkit-box-pack:center!important;-webkit-justify-content:center!important;-ms-flex-pack:center!important;justify-content:center!important}.justify-content-between{-webkit-box-pack:justify!important;-webkit-justify-content:space-between!important;-ms-flex-pack:justify!important;justify-content:space-between!important}.justify-content-around{-webkit-justify-content:space-around!important;-ms-flex-pack:distribute!important;justify-content:space-around!important}.align-items-start{-webkit-box-align:start!important;-webkit-align-items:flex-start!important;-ms-flex-align:start!important;align-items:flex-start!important}.align-items-end{-webkit-box-align:end!important;-webkit-align-items:flex-end!important;-ms-flex-align:end!important;align-items:flex-end!important}.align-items-center{-webkit-box-align:center!important;-webkit-align-items:center!important;-ms-flex-align:center!important;align-items:center!important}.align-items-baseline{-webkit-box-align:baseline!important;-webkit-align-items:baseline!important;-ms-flex-align:baseline!important;align-items:baseline!important}.align-items-stretch{-webkit-box-align:stretch!important;-webkit-align-items:stretch!important;-ms-flex-align:stretch!important;align-items:stretch!important}.align-content-start{-webkit-align-content:flex-start!important;-ms-flex-line-pack:start!important;align-content:flex-start!important}.align-content-end{-webkit-align-content:flex-end!important;-ms-flex-line-pack:end!important;align-content:flex-end!important}.align-content-center{-webkit-align-content:center!important;-ms-flex-line-pack:center!important;align-content:center!important}.align-content-between{-webkit-align-content:space-between!important;-ms-flex-line-pack:justify!important;align-content:space-between!important}.align-content-around{-webkit-align-content:space-around!important;-ms-flex-line-pack:distribute!important;align-content:space-around!important}.align-content-stretch{-webkit-align-content:stretch!important;-ms-flex-line-pack:stretch!important;align-content:stretch!important}.align-self-auto{-webkit-align-self:auto!important;-ms-flex-item-align:auto!important;-ms-grid-row-align:auto!important;align-self:auto!important}.align-self-start{-webkit-align-self:flex-start!important;-ms-flex-item-align:start!important;align-self:flex-start!important}.align-self-end{-webkit-align-self:flex-end!important;-ms-flex-item-align:end!important;align-self:flex-end!important}.align-self-center{-webkit-align-self:center!important;-ms-flex-item-align:center!important;-ms-grid-row-align:center!important;align-self:center!important}.align-self-baseline{-webkit-align-self:baseline!important;-ms-flex-item-align:baseline!important;align-self:baseline!important}.align-self-stretch{-webkit-align-self:stretch!important;-ms-flex-item-align:stretch!important;-ms-grid-row-align:stretch!important;align-self:stretch!important}@media (min-width:576px){.flex-sm-first{-webkit-box-ordinal-group:0;-webkit-order:-1;-ms-flex-order:-1;order:-1}.flex-sm-last{-webkit-box-ordinal-group:2;-webkit-order:1;-ms-flex-order:1;order:1}.flex-sm-unordered{-webkit-box-ordinal-group:1;-webkit-order:0;-ms-flex-order:0;order:0}.flex-sm-row{-webkit-box-orient:horizontal!important;-webkit-box-direction:normal!important;-webkit-flex-direction:row!important;-ms-flex-direction:row!important;flex-direction:row!important}.flex-sm-column{-webkit-box-orient:vertical!important;-webkit-box-direction:normal!important;-webkit-flex-direction:column!important;-ms-flex-direction:column!important;flex-direction:column!important}.flex-sm-row-reverse{-webkit-box-orient:horizontal!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:row-reverse!important;-ms-flex-direction:row-reverse!important;flex-direction:row-reverse!important}.flex-sm-column-reverse{-webkit-box-orient:vertical!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:column-reverse!important;-ms-flex-direction:column-reverse!important;flex-direction:column-reverse!important}.flex-sm-wrap{-webkit-flex-wrap:wrap!important;-ms-flex-wrap:wrap!important;flex-wrap:wrap!important}.flex-sm-nowrap{-webkit-flex-wrap:nowrap!important;-ms-flex-wrap:nowrap!important;flex-wrap:nowrap!important}.flex-sm-wrap-reverse{-webkit-flex-wrap:wrap-reverse!important;-ms-flex-wrap:wrap-reverse!important;flex-wrap:wrap-reverse!important}.justify-content-sm-start{-webkit-box-pack:start!important;-webkit-justify-content:flex-start!important;-ms-flex-pack:start!important;justify-content:flex-start!important}.justify-content-sm-end{-webkit-box-pack:end!important;-webkit-justify-content:flex-end!important;-ms-flex-pack:end!important;justify-content:flex-end!important}.justify-content-sm-center{-webkit-box-pack:center!important;-webkit-justify-content:center!important;-ms-flex-pack:center!important;justify-content:center!important}.justify-content-sm-between{-webkit-box-pack:justify!important;-webkit-justify-content:space-between!important;-ms-flex-pack:justify!important;justify-content:space-between!important}.justify-content-sm-around{-webkit-justify-content:space-around!important;-ms-flex-pack:distribute!important;justify-content:space-around!important}.align-items-sm-start{-webkit-box-align:start!important;-webkit-align-items:flex-start!important;-ms-flex-align:start!important;align-items:flex-start!important}.align-items-sm-end{-webkit-box-align:end!important;-webkit-align-items:flex-end!important;-ms-flex-align:end!important;align-items:flex-end!important}.align-items-sm-center{-webkit-box-align:center!important;-webkit-align-items:center!important;-ms-flex-align:center!important;align-items:center!important}.align-items-sm-baseline{-webkit-box-align:baseline!important;-webkit-align-items:baseline!important;-ms-flex-align:baseline!important;align-items:baseline!important}.align-items-sm-stretch{-webkit-box-align:stretch!important;-webkit-align-items:stretch!important;-ms-flex-align:stretch!important;align-items:stretch!important}.align-content-sm-start{-webkit-align-content:flex-start!important;-ms-flex-line-pack:start!important;align-content:flex-start!important}.align-content-sm-end{-webkit-align-content:flex-end!important;-ms-flex-line-pack:end!important;align-content:flex-end!important}.align-content-sm-center{-webkit-align-content:center!important;-ms-flex-line-pack:center!important;align-content:center!important}.align-content-sm-between{-webkit-align-content:space-between!important;-ms-flex-line-pack:justify!important;align-content:space-between!important}.align-content-sm-around{-webkit-align-content:space-around!important;-ms-flex-line-pack:distribute!important;align-content:space-around!important}.align-content-sm-stretch{-webkit-align-content:stretch!important;-ms-flex-line-pack:stretch!important;align-content:stretch!important}.align-self-sm-auto{-webkit-align-self:auto!important;-ms-flex-item-align:auto!important;-ms-grid-row-align:auto!important;align-self:auto!important}.align-self-sm-start{-webkit-align-self:flex-start!important;-ms-flex-item-align:start!important;align-self:flex-start!important}.align-self-sm-end{-webkit-align-self:flex-end!important;-ms-flex-item-align:end!important;align-self:flex-end!important}.align-self-sm-center{-webkit-align-self:center!important;-ms-flex-item-align:center!important;-ms-grid-row-align:center!important;align-self:center!important}.align-self-sm-baseline{-webkit-align-self:baseline!important;-ms-flex-item-align:baseline!important;align-self:baseline!important}.align-self-sm-stretch{-webkit-align-self:stretch!important;-ms-flex-item-align:stretch!important;-ms-grid-row-align:stretch!important;align-self:stretch!important}}@media (min-width:768px){.flex-md-first{-webkit-box-ordinal-group:0;-webkit-order:-1;-ms-flex-order:-1;order:-1}.flex-md-last{-webkit-box-ordinal-group:2;-webkit-order:1;-ms-flex-order:1;order:1}.flex-md-unordered{-webkit-box-ordinal-group:1;-webkit-order:0;-ms-flex-order:0;order:0}.flex-md-row{-webkit-box-orient:horizontal!important;-webkit-box-direction:normal!important;-webkit-flex-direction:row!important;-ms-flex-direction:row!important;flex-direction:row!important}.flex-md-column{-webkit-box-orient:vertical!important;-webkit-box-direction:normal!important;-webkit-flex-direction:column!important;-ms-flex-direction:column!important;flex-direction:column!important}.flex-md-row-reverse{-webkit-box-orient:horizontal!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:row-reverse!important;-ms-flex-direction:row-reverse!important;flex-direction:row-reverse!important}.flex-md-column-reverse{-webkit-box-orient:vertical!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:column-reverse!important;-ms-flex-direction:column-reverse!important;flex-direction:column-reverse!important}.flex-md-wrap{-webkit-flex-wrap:wrap!important;-ms-flex-wrap:wrap!important;flex-wrap:wrap!important}.flex-md-nowrap{-webkit-flex-wrap:nowrap!important;-ms-flex-wrap:nowrap!important;flex-wrap:nowrap!important}.flex-md-wrap-reverse{-webkit-flex-wrap:wrap-reverse!important;-ms-flex-wrap:wrap-reverse!important;flex-wrap:wrap-reverse!important}.justify-content-md-start{-webkit-box-pack:start!important;-webkit-justify-content:flex-start!important;-ms-flex-pack:start!important;justify-content:flex-start!important}.justify-content-md-end{-webkit-box-pack:end!important;-webkit-justify-content:flex-end!important;-ms-flex-pack:end!important;justify-content:flex-end!important}.justify-content-md-center{-webkit-box-pack:center!important;-webkit-justify-content:center!important;-ms-flex-pack:center!important;justify-content:center!important}.justify-content-md-between{-webkit-box-pack:justify!important;-webkit-justify-content:space-between!important;-ms-flex-pack:justify!important;justify-content:space-between!important}.justify-content-md-around{-webkit-justify-content:space-around!important;-ms-flex-pack:distribute!important;justify-content:space-around!important}.align-items-md-start{-webkit-box-align:start!important;-webkit-align-items:flex-start!important;-ms-flex-align:start!important;align-items:flex-start!important}.align-items-md-end{-webkit-box-align:end!important;-webkit-align-items:flex-end!important;-ms-flex-align:end!important;align-items:flex-end!important}.align-items-md-center{-webkit-box-align:center!important;-webkit-align-items:center!important;-ms-flex-align:center!important;align-items:center!important}.align-items-md-baseline{-webkit-box-align:baseline!important;-webkit-align-items:baseline!important;-ms-flex-align:baseline!important;align-items:baseline!important}.align-items-md-stretch{-webkit-box-align:stretch!important;-webkit-align-items:stretch!important;-ms-flex-align:stretch!important;align-items:stretch!important}.align-content-md-start{-webkit-align-content:flex-start!important;-ms-flex-line-pack:start!important;align-content:flex-start!important}.align-content-md-end{-webkit-align-content:flex-end!important;-ms-flex-line-pack:end!important;align-content:flex-end!important}.align-content-md-center{-webkit-align-content:center!important;-ms-flex-line-pack:center!important;align-content:center!important}.align-content-md-between{-webkit-align-content:space-between!important;-ms-flex-line-pack:justify!important;align-content:space-between!important}.align-content-md-around{-webkit-align-content:space-around!important;-ms-flex-line-pack:distribute!important;align-content:space-around!important}.align-content-md-stretch{-webkit-align-content:stretch!important;-ms-flex-line-pack:stretch!important;align-content:stretch!important}.align-self-md-auto{-webkit-align-self:auto!important;-ms-flex-item-align:auto!important;-ms-grid-row-align:auto!important;align-self:auto!important}.align-self-md-start{-webkit-align-self:flex-start!important;-ms-flex-item-align:start!important;align-self:flex-start!important}.align-self-md-end{-webkit-align-self:flex-end!important;-ms-flex-item-align:end!important;align-self:flex-end!important}.align-self-md-center{-webkit-align-self:center!important;-ms-flex-item-align:center!important;-ms-grid-row-align:center!important;align-self:center!important}.align-self-md-baseline{-webkit-align-self:baseline!important;-ms-flex-item-align:baseline!important;align-self:baseline!important}.align-self-md-stretch{-webkit-align-self:stretch!important;-ms-flex-item-align:stretch!important;-ms-grid-row-align:stretch!important;align-self:stretch!important}}@media (min-width:992px){.flex-lg-first{-webkit-box-ordinal-group:0;-webkit-order:-1;-ms-flex-order:-1;order:-1}.flex-lg-last{-webkit-box-ordinal-group:2;-webkit-order:1;-ms-flex-order:1;order:1}.flex-lg-unordered{-webkit-box-ordinal-group:1;-webkit-order:0;-ms-flex-order:0;order:0}.flex-lg-row{-webkit-box-orient:horizontal!important;-webkit-box-direction:normal!important;-webkit-flex-direction:row!important;-ms-flex-direction:row!important;flex-direction:row!important}.flex-lg-column{-webkit-box-orient:vertical!important;-webkit-box-direction:normal!important;-webkit-flex-direction:column!important;-ms-flex-direction:column!important;flex-direction:column!important}.flex-lg-row-reverse{-webkit-box-orient:horizontal!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:row-reverse!important;-ms-flex-direction:row-reverse!important;flex-direction:row-reverse!important}.flex-lg-column-reverse{-webkit-box-orient:vertical!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:column-reverse!important;-ms-flex-direction:column-reverse!important;flex-direction:column-reverse!important}.flex-lg-wrap{-webkit-flex-wrap:wrap!important;-ms-flex-wrap:wrap!important;flex-wrap:wrap!important}.flex-lg-nowrap{-webkit-flex-wrap:nowrap!important;-ms-flex-wrap:nowrap!important;flex-wrap:nowrap!important}.flex-lg-wrap-reverse{-webkit-flex-wrap:wrap-reverse!important;-ms-flex-wrap:wrap-reverse!important;flex-wrap:wrap-reverse!important}.justify-content-lg-start{-webkit-box-pack:start!important;-webkit-justify-content:flex-start!important;-ms-flex-pack:start!important;justify-content:flex-start!important}.justify-content-lg-end{-webkit-box-pack:end!important;-webkit-justify-content:flex-end!important;-ms-flex-pack:end!important;justify-content:flex-end!important}.justify-content-lg-center{-webkit-box-pack:center!important;-webkit-justify-content:center!important;-ms-flex-pack:center!important;justify-content:center!important}.justify-content-lg-between{-webkit-box-pack:justify!important;-webkit-justify-content:space-between!important;-ms-flex-pack:justify!important;justify-content:space-between!important}.justify-content-lg-around{-webkit-justify-content:space-around!important;-ms-flex-pack:distribute!important;justify-content:space-around!important}.align-items-lg-start{-webkit-box-align:start!important;-webkit-align-items:flex-start!important;-ms-flex-align:start!important;align-items:flex-start!important}.align-items-lg-end{-webkit-box-align:end!important;-webkit-align-items:flex-end!important;-ms-flex-align:end!important;align-items:flex-end!important}.align-items-lg-center{-webkit-box-align:center!important;-webkit-align-items:center!important;-ms-flex-align:center!important;align-items:center!important}.align-items-lg-baseline{-webkit-box-align:baseline!important;-webkit-align-items:baseline!important;-ms-flex-align:baseline!important;align-items:baseline!important}.align-items-lg-stretch{-webkit-box-align:stretch!important;-webkit-align-items:stretch!important;-ms-flex-align:stretch!important;align-items:stretch!important}.align-content-lg-start{-webkit-align-content:flex-start!important;-ms-flex-line-pack:start!important;align-content:flex-start!important}.align-content-lg-end{-webkit-align-content:flex-end!important;-ms-flex-line-pack:end!important;align-content:flex-end!important}.align-content-lg-center{-webkit-align-content:center!important;-ms-flex-line-pack:center!important;align-content:center!important}.align-content-lg-between{-webkit-align-content:space-between!important;-ms-flex-line-pack:justify!important;align-content:space-between!important}.align-content-lg-around{-webkit-align-content:space-around!important;-ms-flex-line-pack:distribute!important;align-content:space-around!important}.align-content-lg-stretch{-webkit-align-content:stretch!important;-ms-flex-line-pack:stretch!important;align-content:stretch!important}.align-self-lg-auto{-webkit-align-self:auto!important;-ms-flex-item-align:auto!important;-ms-grid-row-align:auto!important;align-self:auto!important}.align-self-lg-start{-webkit-align-self:flex-start!important;-ms-flex-item-align:start!important;align-self:flex-start!important}.align-self-lg-end{-webkit-align-self:flex-end!important;-ms-flex-item-align:end!important;align-self:flex-end!important}.align-self-lg-center{-webkit-align-self:center!important;-ms-flex-item-align:center!important;-ms-grid-row-align:center!important;align-self:center!important}.align-self-lg-baseline{-webkit-align-self:baseline!important;-ms-flex-item-align:baseline!important;align-self:baseline!important}.align-self-lg-stretch{-webkit-align-self:stretch!important;-ms-flex-item-align:stretch!important;-ms-grid-row-align:stretch!important;align-self:stretch!important}}@media (min-width:1200px){.flex-xl-first{-webkit-box-ordinal-group:0;-webkit-order:-1;-ms-flex-order:-1;order:-1}.flex-xl-last{-webkit-box-ordinal-group:2;-webkit-order:1;-ms-flex-order:1;order:1}.flex-xl-unordered{-webkit-box-ordinal-group:1;-webkit-order:0;-ms-flex-order:0;order:0}.flex-xl-row{-webkit-box-orient:horizontal!important;-webkit-box-direction:normal!important;-webkit-flex-direction:row!important;-ms-flex-direction:row!important;flex-direction:row!important}.flex-xl-column{-webkit-box-orient:vertical!important;-webkit-box-direction:normal!important;-webkit-flex-direction:column!important;-ms-flex-direction:column!important;flex-direction:column!important}.flex-xl-row-reverse{-webkit-box-orient:horizontal!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:row-reverse!important;-ms-flex-direction:row-reverse!important;flex-direction:row-reverse!important}.flex-xl-column-reverse{-webkit-box-orient:vertical!important;-webkit-box-direction:reverse!important;-webkit-flex-direction:column-reverse!important;-ms-flex-direction:column-reverse!important;flex-direction:column-reverse!important}.flex-xl-wrap{-webkit-flex-wrap:wrap!important;-ms-flex-wrap:wrap!important;flex-wrap:wrap!important}.flex-xl-nowrap{-webkit-flex-wrap:nowrap!important;-ms-flex-wrap:nowrap!important;flex-wrap:nowrap!important}.flex-xl-wrap-reverse{-webkit-flex-wrap:wrap-reverse!important;-ms-flex-wrap:wrap-reverse!important;flex-wrap:wrap-reverse!important}.justify-content-xl-start{-webkit-box-pack:start!important;-webkit-justify-content:flex-start!important;-ms-flex-pack:start!important;justify-content:flex-start!important}.justify-content-xl-end{-webkit-box-pack:end!important;-webkit-justify-content:flex-end!important;-ms-flex-pack:end!important;justify-content:flex-end!important}.justify-content-xl-center{-webkit-box-pack:center!important;-webkit-justify-content:center!important;-ms-flex-pack:center!important;justify-content:center!important}.justify-content-xl-between{-webkit-box-pack:justify!important;-webkit-justify-content:space-between!important;-ms-flex-pack:justify!important;justify-content:space-between!important}.justify-content-xl-around{-webkit-justify-content:space-around!important;-ms-flex-pack:distribute!important;justify-content:space-around!important}.align-items-xl-start{-webkit-box-align:start!important;-webkit-align-items:flex-start!important;-ms-flex-align:start!important;align-items:flex-start!important}.align-items-xl-end{-webkit-box-align:end!important;-webkit-align-items:flex-end!important;-ms-flex-align:end!important;align-items:flex-end!important}.align-items-xl-center{-webkit-box-align:center!important;-webkit-align-items:center!important;-ms-flex-align:center!important;align-items:center!important}.align-items-xl-baseline{-webkit-box-align:baseline!important;-webkit-align-items:baseline!important;-ms-flex-align:baseline!important;align-items:baseline!important}.align-items-xl-stretch{-webkit-box-align:stretch!important;-webkit-align-items:stretch!important;-ms-flex-align:stretch!important;align-items:stretch!important}.align-content-xl-start{-webkit-align-content:flex-start!important;-ms-flex-line-pack:start!important;align-content:flex-start!important}.align-content-xl-end{-webkit-align-content:flex-end!important;-ms-flex-line-pack:end!important;align-content:flex-end!important}.align-content-xl-center{-webkit-align-content:center!important;-ms-flex-line-pack:center!important;align-content:center!important}.align-content-xl-between{-webkit-align-content:space-between!important;-ms-flex-line-pack:justify!important;align-content:space-between!important}.align-content-xl-around{-webkit-align-content:space-around!important;-ms-flex-line-pack:distribute!important;align-content:space-around!important}.align-content-xl-stretch{-webkit-align-content:stretch!important;-ms-flex-line-pack:stretch!important;align-content:stretch!important}.align-self-xl-auto{-webkit-align-self:auto!important;-ms-flex-item-align:auto!important;-ms-grid-row-align:auto!important;align-self:auto!important}.align-self-xl-start{-webkit-align-self:flex-start!important;-ms-flex-item-align:start!important;align-self:flex-start!important}.align-self-xl-end{-webkit-align-self:flex-end!important;-ms-flex-item-align:end!important;align-self:flex-end!important}.align-self-xl-center{-webkit-align-self:center!important;-ms-flex-item-align:center!important;-ms-grid-row-align:center!important;align-self:center!important}.align-self-xl-baseline{-webkit-align-self:baseline!important;-ms-flex-item-align:baseline!important;align-self:baseline!important}.align-self-xl-stretch{-webkit-align-self:stretch!important;-ms-flex-item-align:stretch!important;-ms-grid-row-align:stretch!important;align-self:stretch!important}}.float-left{float:left!important}.float-right{float:right!important}.float-none{float:none!important}@media (min-width:576px){.float-sm-left{float:left!important}.float-sm-right{float:right!important}.float-sm-none{float:none!important}}@media (min-width:768px){.float-md-left{float:left!important}.float-md-right{float:right!important}.float-md-none{float:none!important}}@media (min-width:992px){.float-lg-left{float:left!important}.float-lg-right{float:right!important}.float-lg-none{float:none!important}}@media (min-width:1200px){.float-xl-left{float:left!important}.float-xl-right{float:right!important}.float-xl-none{float:none!important}}.fixed-top{position:fixed;top:0;right:0;left:0;z-index:1030}.fixed-bottom{position:fixed;right:0;bottom:0;left:0;z-index:1030}.sticky-top{position:-webkit-sticky;position:sticky;top:0;z-index:1030}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}.sr-only-focusable:active,.sr-only-focusable:focus{position:static;width:auto;height:auto;margin:0;overflow:visible;clip:auto}.w-25{width:25%!important}.w-50{width:50%!important}.w-75{width:75%!important}.w-100{width:100%!important}.h-25{height:25%!important}.h-50{height:50%!important}.h-75{height:75%!important}.h-100{height:100%!important}.mw-100{max-width:100%!important}.mh-100{max-height:100%!important}.m-0{margin:0 0!important}.mt-0{margin-top:0!important}.mr-0{margin-right:0!important}.mb-0{margin-bottom:0!important}.ml-0{margin-left:0!important}.mx-0{margin-right:0!important;margin-left:0!important}.my-0{margin-top:0!important;margin-bottom:0!important}.m-1{margin:.25rem .25rem!important}.mt-1{margin-top:.25rem!important}.mr-1{margin-right:.25rem!important}.mb-1{margin-bottom:.25rem!important}.ml-1{margin-left:.25rem!important}.mx-1{margin-right:.25rem!important;margin-left:.25rem!important}.my-1{margin-top:.25rem!important;margin-bottom:.25rem!important}.m-2{margin:.5rem .5rem!important}.mt-2{margin-top:.5rem!important}.mr-2{margin-right:.5rem!important}.mb-2{margin-bottom:.5rem!important}.ml-2{margin-left:.5rem!important}.mx-2{margin-right:.5rem!important;margin-left:.5rem!important}.my-2{margin-top:.5rem!important;margin-bottom:.5rem!important}.m-3{margin:1rem 1rem!important}.mt-3{margin-top:1rem!important}.mr-3{margin-right:1rem!important}.mb-3{margin-bottom:1rem!important}.ml-3{margin-left:1rem!important}.mx-3{margin-right:1rem!important;margin-left:1rem!important}.my-3{margin-top:1rem!important;margin-bottom:1rem!important}.m-4{margin:1.5rem 1.5rem!important}.mt-4{margin-top:1.5rem!important}.mr-4{margin-right:1.5rem!important}.mb-4{margin-bottom:1.5rem!important}.ml-4{margin-left:1.5rem!important}.mx-4{margin-right:1.5rem!important;margin-left:1.5rem!important}.my-4{margin-top:1.5rem!important;margin-bottom:1.5rem!important}.m-5{margin:3rem 3rem!important}.mt-5{margin-top:3rem!important}.mr-5{margin-right:3rem!important}.mb-5{margin-bottom:3rem!important}.ml-5{margin-left:3rem!important}.mx-5{margin-right:3rem!important;margin-left:3rem!important}.my-5{margin-top:3rem!important;margin-bottom:3rem!important}.p-0{padding:0 0!important}.pt-0{padding-top:0!important}.pr-0{padding-right:0!important}.pb-0{padding-bottom:0!important}.pl-0{padding-left:0!important}.px-0{padding-right:0!important;padding-left:0!important}.py-0{padding-top:0!important;padding-bottom:0!important}.p-1{padding:.25rem .25rem!important}.pt-1{padding-top:.25rem!important}.pr-1{padding-right:.25rem!important}.pb-1{padding-bottom:.25rem!important}.pl-1{padding-left:.25rem!important}.px-1{padding-right:.25rem!important;padding-left:.25rem!important}.py-1{padding-top:.25rem!important;padding-bottom:.25rem!important}.p-2{padding:.5rem .5rem!important}.pt-2{padding-top:.5rem!important}.pr-2{padding-right:.5rem!important}.pb-2{padding-bottom:.5rem!important}.pl-2{padding-left:.5rem!important}.px-2{padding-right:.5rem!important;padding-left:.5rem!important}.py-2{padding-top:.5rem!important;padding-bottom:.5rem!important}.p-3{padding:1rem 1rem!important}.pt-3{padding-top:1rem!important}.pr-3{padding-right:1rem!important}.pb-3{padding-bottom:1rem!important}.pl-3{padding-left:1rem!important}.px-3{padding-right:1rem!important;padding-left:1rem!important}.py-3{padding-top:1rem!important;padding-bottom:1rem!important}.p-4{padding:1.5rem 1.5rem!important}.pt-4{padding-top:1.5rem!important}.pr-4{padding-right:1.5rem!important}.pb-4{padding-bottom:1.5rem!important}.pl-4{padding-left:1.5rem!important}.px-4{padding-right:1.5rem!important;padding-left:1.5rem!important}.py-4{padding-top:1.5rem!important;padding-bottom:1.5rem!important}.p-5{padding:3rem 3rem!important}.pt-5{padding-top:3rem!important}.pr-5{padding-right:3rem!important}.pb-5{padding-bottom:3rem!important}.pl-5{padding-left:3rem!important}.px-5{padding-right:3rem!important;padding-left:3rem!important}.py-5{padding-top:3rem!important;padding-bottom:3rem!important}.m-auto{margin:auto!important}.mt-auto{margin-top:auto!important}.mr-auto{margin-right:auto!important}.mb-auto{margin-bottom:auto!important}.ml-auto{margin-left:auto!important}.mx-auto{margin-right:auto!important;margin-left:auto!important}.my-auto{margin-top:auto!important;margin-bottom:auto!important}@media (min-width:576px){.m-sm-0{margin:0 0!important}.mt-sm-0{margin-top:0!important}.mr-sm-0{margin-right:0!important}.mb-sm-0{margin-bottom:0!important}.ml-sm-0{margin-left:0!important}.mx-sm-0{margin-right:0!important;margin-left:0!important}.my-sm-0{margin-top:0!important;margin-bottom:0!important}.m-sm-1{margin:.25rem .25rem!important}.mt-sm-1{margin-top:.25rem!important}.mr-sm-1{margin-right:.25rem!important}.mb-sm-1{margin-bottom:.25rem!important}.ml-sm-1{margin-left:.25rem!important}.mx-sm-1{margin-right:.25rem!important;margin-left:.25rem!important}.my-sm-1{margin-top:.25rem!important;margin-bottom:.25rem!important}.m-sm-2{margin:.5rem .5rem!important}.mt-sm-2{margin-top:.5rem!important}.mr-sm-2{margin-right:.5rem!important}.mb-sm-2{margin-bottom:.5rem!important}.ml-sm-2{margin-left:.5rem!important}.mx-sm-2{margin-right:.5rem!important;margin-left:.5rem!important}.my-sm-2{margin-top:.5rem!important;margin-bottom:.5rem!important}.m-sm-3{margin:1rem 1rem!important}.mt-sm-3{margin-top:1rem!important}.mr-sm-3{margin-right:1rem!important}.mb-sm-3{margin-bottom:1rem!important}.ml-sm-3{margin-left:1rem!important}.mx-sm-3{margin-right:1rem!important;margin-left:1rem!important}.my-sm-3{margin-top:1rem!important;margin-bottom:1rem!important}.m-sm-4{margin:1.5rem 1.5rem!important}.mt-sm-4{margin-top:1.5rem!important}.mr-sm-4{margin-right:1.5rem!important}.mb-sm-4{margin-bottom:1.5rem!important}.ml-sm-4{margin-left:1.5rem!important}.mx-sm-4{margin-right:1.5rem!important;margin-left:1.5rem!important}.my-sm-4{margin-top:1.5rem!important;margin-bottom:1.5rem!important}.m-sm-5{margin:3rem 3rem!important}.mt-sm-5{margin-top:3rem!important}.mr-sm-5{margin-right:3rem!important}.mb-sm-5{margin-bottom:3rem!important}.ml-sm-5{margin-left:3rem!important}.mx-sm-5{margin-right:3rem!important;margin-left:3rem!important}.my-sm-5{margin-top:3rem!important;margin-bottom:3rem!important}.p-sm-0{padding:0 0!important}.pt-sm-0{padding-top:0!important}.pr-sm-0{padding-right:0!important}.pb-sm-0{padding-bottom:0!important}.pl-sm-0{padding-left:0!important}.px-sm-0{padding-right:0!important;padding-left:0!important}.py-sm-0{padding-top:0!important;padding-bottom:0!important}.p-sm-1{padding:.25rem .25rem!important}.pt-sm-1{padding-top:.25rem!important}.pr-sm-1{padding-right:.25rem!important}.pb-sm-1{padding-bottom:.25rem!important}.pl-sm-1{padding-left:.25rem!important}.px-sm-1{padding-right:.25rem!important;padding-left:.25rem!important}.py-sm-1{padding-top:.25rem!important;padding-bottom:.25rem!important}.p-sm-2{padding:.5rem .5rem!important}.pt-sm-2{padding-top:.5rem!important}.pr-sm-2{padding-right:.5rem!important}.pb-sm-2{padding-bottom:.5rem!important}.pl-sm-2{padding-left:.5rem!important}.px-sm-2{padding-right:.5rem!important;padding-left:.5rem!important}.py-sm-2{padding-top:.5rem!important;padding-bottom:.5rem!important}.p-sm-3{padding:1rem 1rem!important}.pt-sm-3{padding-top:1rem!important}.pr-sm-3{padding-right:1rem!important}.pb-sm-3{padding-bottom:1rem!important}.pl-sm-3{padding-left:1rem!important}.px-sm-3{padding-right:1rem!important;padding-left:1rem!important}.py-sm-3{padding-top:1rem!important;padding-bottom:1rem!important}.p-sm-4{padding:1.5rem 1.5rem!important}.pt-sm-4{padding-top:1.5rem!important}.pr-sm-4{padding-right:1.5rem!important}.pb-sm-4{padding-bottom:1.5rem!important}.pl-sm-4{padding-left:1.5rem!important}.px-sm-4{padding-right:1.5rem!important;padding-left:1.5rem!important}.py-sm-4{padding-top:1.5rem!important;padding-bottom:1.5rem!important}.p-sm-5{padding:3rem 3rem!important}.pt-sm-5{padding-top:3rem!important}.pr-sm-5{padding-right:3rem!important}.pb-sm-5{padding-bottom:3rem!important}.pl-sm-5{padding-left:3rem!important}.px-sm-5{padding-right:3rem!important;padding-left:3rem!important}.py-sm-5{padding-top:3rem!important;padding-bottom:3rem!important}.m-sm-auto{margin:auto!important}.mt-sm-auto{margin-top:auto!important}.mr-sm-auto{margin-right:auto!important}.mb-sm-auto{margin-bottom:auto!important}.ml-sm-auto{margin-left:auto!important}.mx-sm-auto{margin-right:auto!important;margin-left:auto!important}.my-sm-auto{margin-top:auto!important;margin-bottom:auto!important}}@media (min-width:768px){.m-md-0{margin:0 0!important}.mt-md-0{margin-top:0!important}.mr-md-0{margin-right:0!important}.mb-md-0{margin-bottom:0!important}.ml-md-0{margin-left:0!important}.mx-md-0{margin-right:0!important;margin-left:0!important}.my-md-0{margin-top:0!important;margin-bottom:0!important}.m-md-1{margin:.25rem .25rem!important}.mt-md-1{margin-top:.25rem!important}.mr-md-1{margin-right:.25rem!important}.mb-md-1{margin-bottom:.25rem!important}.ml-md-1{margin-left:.25rem!important}.mx-md-1{margin-right:.25rem!important;margin-left:.25rem!important}.my-md-1{margin-top:.25rem!important;margin-bottom:.25rem!important}.m-md-2{margin:.5rem .5rem!important}.mt-md-2{margin-top:.5rem!important}.mr-md-2{margin-right:.5rem!important}.mb-md-2{margin-bottom:.5rem!important}.ml-md-2{margin-left:.5rem!important}.mx-md-2{margin-right:.5rem!important;margin-left:.5rem!important}.my-md-2{margin-top:.5rem!important;margin-bottom:.5rem!important}.m-md-3{margin:1rem 1rem!important}.mt-md-3{margin-top:1rem!important}.mr-md-3{margin-right:1rem!important}.mb-md-3{margin-bottom:1rem!important}.ml-md-3{margin-left:1rem!important}.mx-md-3{margin-right:1rem!important;margin-left:1rem!important}.my-md-3{margin-top:1rem!important;margin-bottom:1rem!important}.m-md-4{margin:1.5rem 1.5rem!important}.mt-md-4{margin-top:1.5rem!important}.mr-md-4{margin-right:1.5rem!important}.mb-md-4{margin-bottom:1.5rem!important}.ml-md-4{margin-left:1.5rem!important}.mx-md-4{margin-right:1.5rem!important;margin-left:1.5rem!important}.my-md-4{margin-top:1.5rem!important;margin-bottom:1.5rem!important}.m-md-5{margin:3rem 3rem!important}.mt-md-5{margin-top:3rem!important}.mr-md-5{margin-right:3rem!important}.mb-md-5{margin-bottom:3rem!important}.ml-md-5{margin-left:3rem!important}.mx-md-5{margin-right:3rem!important;margin-left:3rem!important}.my-md-5{margin-top:3rem!important;margin-bottom:3rem!important}.p-md-0{padding:0 0!important}.pt-md-0{padding-top:0!important}.pr-md-0{padding-right:0!important}.pb-md-0{padding-bottom:0!important}.pl-md-0{padding-left:0!important}.px-md-0{padding-right:0!important;padding-left:0!important}.py-md-0{padding-top:0!important;padding-bottom:0!important}.p-md-1{padding:.25rem .25rem!important}.pt-md-1{padding-top:.25rem!important}.pr-md-1{padding-right:.25rem!important}.pb-md-1{padding-bottom:.25rem!important}.pl-md-1{padding-left:.25rem!important}.px-md-1{padding-right:.25rem!important;padding-left:.25rem!important}.py-md-1{padding-top:.25rem!important;padding-bottom:.25rem!important}.p-md-2{padding:.5rem .5rem!important}.pt-md-2{padding-top:.5rem!important}.pr-md-2{padding-right:.5rem!important}.pb-md-2{padding-bottom:.5rem!important}.pl-md-2{padding-left:.5rem!important}.px-md-2{padding-right:.5rem!important;padding-left:.5rem!important}.py-md-2{padding-top:.5rem!important;padding-bottom:.5rem!important}.p-md-3{padding:1rem 1rem!important}.pt-md-3{padding-top:1rem!important}.pr-md-3{padding-right:1rem!important}.pb-md-3{padding-bottom:1rem!important}.pl-md-3{padding-left:1rem!important}.px-md-3{padding-right:1rem!important;padding-left:1rem!important}.py-md-3{padding-top:1rem!important;padding-bottom:1rem!important}.p-md-4{padding:1.5rem 1.5rem!important}.pt-md-4{padding-top:1.5rem!important}.pr-md-4{padding-right:1.5rem!important}.pb-md-4{padding-bottom:1.5rem!important}.pl-md-4{padding-left:1.5rem!important}.px-md-4{padding-right:1.5rem!important;padding-left:1.5rem!important}.py-md-4{padding-top:1.5rem!important;padding-bottom:1.5rem!important}.p-md-5{padding:3rem 3rem!important}.pt-md-5{padding-top:3rem!important}.pr-md-5{padding-right:3rem!important}.pb-md-5{padding-bottom:3rem!important}.pl-md-5{padding-left:3rem!important}.px-md-5{padding-right:3rem!important;padding-left:3rem!important}.py-md-5{padding-top:3rem!important;padding-bottom:3rem!important}.m-md-auto{margin:auto!important}.mt-md-auto{margin-top:auto!important}.mr-md-auto{margin-right:auto!important}.mb-md-auto{margin-bottom:auto!important}.ml-md-auto{margin-left:auto!important}.mx-md-auto{margin-right:auto!important;margin-left:auto!important}.my-md-auto{margin-top:auto!important;margin-bottom:auto!important}}@media (min-width:992px){.m-lg-0{margin:0 0!important}.mt-lg-0{margin-top:0!important}.mr-lg-0{margin-right:0!important}.mb-lg-0{margin-bottom:0!important}.ml-lg-0{margin-left:0!important}.mx-lg-0{margin-right:0!important;margin-left:0!important}.my-lg-0{margin-top:0!important;margin-bottom:0!important}.m-lg-1{margin:.25rem .25rem!important}.mt-lg-1{margin-top:.25rem!important}.mr-lg-1{margin-right:.25rem!important}.mb-lg-1{margin-bottom:.25rem!important}.ml-lg-1{margin-left:.25rem!important}.mx-lg-1{margin-right:.25rem!important;margin-left:.25rem!important}.my-lg-1{margin-top:.25rem!important;margin-bottom:.25rem!important}.m-lg-2{margin:.5rem .5rem!important}.mt-lg-2{margin-top:.5rem!important}.mr-lg-2{margin-right:.5rem!important}.mb-lg-2{margin-bottom:.5rem!important}.ml-lg-2{margin-left:.5rem!important}.mx-lg-2{margin-right:.5rem!important;margin-left:.5rem!important}.my-lg-2{margin-top:.5rem!important;margin-bottom:.5rem!important}.m-lg-3{margin:1rem 1rem!important}.mt-lg-3{margin-top:1rem!important}.mr-lg-3{margin-right:1rem!important}.mb-lg-3{margin-bottom:1rem!important}.ml-lg-3{margin-left:1rem!important}.mx-lg-3{margin-right:1rem!important;margin-left:1rem!important}.my-lg-3{margin-top:1rem!important;margin-bottom:1rem!important}.m-lg-4{margin:1.5rem 1.5rem!important}.mt-lg-4{margin-top:1.5rem!important}.mr-lg-4{margin-right:1.5rem!important}.mb-lg-4{margin-bottom:1.5rem!important}.ml-lg-4{margin-left:1.5rem!important}.mx-lg-4{margin-right:1.5rem!important;margin-left:1.5rem!important}.my-lg-4{margin-top:1.5rem!important;margin-bottom:1.5rem!important}.m-lg-5{margin:3rem 3rem!important}.mt-lg-5{margin-top:3rem!important}.mr-lg-5{margin-right:3rem!important}.mb-lg-5{margin-bottom:3rem!important}.ml-lg-5{margin-left:3rem!important}.mx-lg-5{margin-right:3rem!important;margin-left:3rem!important}.my-lg-5{margin-top:3rem!important;margin-bottom:3rem!important}.p-lg-0{padding:0 0!important}.pt-lg-0{padding-top:0!important}.pr-lg-0{padding-right:0!important}.pb-lg-0{padding-bottom:0!important}.pl-lg-0{padding-left:0!important}.px-lg-0{padding-right:0!important;padding-left:0!important}.py-lg-0{padding-top:0!important;padding-bottom:0!important}.p-lg-1{padding:.25rem .25rem!important}.pt-lg-1{padding-top:.25rem!important}.pr-lg-1{padding-right:.25rem!important}.pb-lg-1{padding-bottom:.25rem!important}.pl-lg-1{padding-left:.25rem!important}.px-lg-1{padding-right:.25rem!important;padding-left:.25rem!important}.py-lg-1{padding-top:.25rem!important;padding-bottom:.25rem!important}.p-lg-2{padding:.5rem .5rem!important}.pt-lg-2{padding-top:.5rem!important}.pr-lg-2{padding-right:.5rem!important}.pb-lg-2{padding-bottom:.5rem!important}.pl-lg-2{padding-left:.5rem!important}.px-lg-2{padding-right:.5rem!important;padding-left:.5rem!important}.py-lg-2{padding-top:.5rem!important;padding-bottom:.5rem!important}.p-lg-3{padding:1rem 1rem!important}.pt-lg-3{padding-top:1rem!important}.pr-lg-3{padding-right:1rem!important}.pb-lg-3{padding-bottom:1rem!important}.pl-lg-3{padding-left:1rem!important}.px-lg-3{padding-right:1rem!important;padding-left:1rem!important}.py-lg-3{padding-top:1rem!important;padding-bottom:1rem!important}.p-lg-4{padding:1.5rem 1.5rem!important}.pt-lg-4{padding-top:1.5rem!important}.pr-lg-4{padding-right:1.5rem!important}.pb-lg-4{padding-bottom:1.5rem!important}.pl-lg-4{padding-left:1.5rem!important}.px-lg-4{padding-right:1.5rem!important;padding-left:1.5rem!important}.py-lg-4{padding-top:1.5rem!important;padding-bottom:1.5rem!important}.p-lg-5{padding:3rem 3rem!important}.pt-lg-5{padding-top:3rem!important}.pr-lg-5{padding-right:3rem!important}.pb-lg-5{padding-bottom:3rem!important}.pl-lg-5{padding-left:3rem!important}.px-lg-5{padding-right:3rem!important;padding-left:3rem!important}.py-lg-5{padding-top:3rem!important;padding-bottom:3rem!important}.m-lg-auto{margin:auto!important}.mt-lg-auto{margin-top:auto!important}.mr-lg-auto{margin-right:auto!important}.mb-lg-auto{margin-bottom:auto!important}.ml-lg-auto{margin-left:auto!important}.mx-lg-auto{margin-right:auto!important;margin-left:auto!important}.my-lg-auto{margin-top:auto!important;margin-bottom:auto!important}}@media (min-width:1200px){.m-xl-0{margin:0 0!important}.mt-xl-0{margin-top:0!important}.mr-xl-0{margin-right:0!important}.mb-xl-0{margin-bottom:0!important}.ml-xl-0{margin-left:0!important}.mx-xl-0{margin-right:0!important;margin-left:0!important}.my-xl-0{margin-top:0!important;margin-bottom:0!important}.m-xl-1{margin:.25rem .25rem!important}.mt-xl-1{margin-top:.25rem!important}.mr-xl-1{margin-right:.25rem!important}.mb-xl-1{margin-bottom:.25rem!important}.ml-xl-1{margin-left:.25rem!important}.mx-xl-1{margin-right:.25rem!important;margin-left:.25rem!important}.my-xl-1{margin-top:.25rem!important;margin-bottom:.25rem!important}.m-xl-2{margin:.5rem .5rem!important}.mt-xl-2{margin-top:.5rem!important}.mr-xl-2{margin-right:.5rem!important}.mb-xl-2{margin-bottom:.5rem!important}.ml-xl-2{margin-left:.5rem!important}.mx-xl-2{margin-right:.5rem!important;margin-left:.5rem!important}.my-xl-2{margin-top:.5rem!important;margin-bottom:.5rem!important}.m-xl-3{margin:1rem 1rem!important}.mt-xl-3{margin-top:1rem!important}.mr-xl-3{margin-right:1rem!important}.mb-xl-3{margin-bottom:1rem!important}.ml-xl-3{margin-left:1rem!important}.mx-xl-3{margin-right:1rem!important;margin-left:1rem!important}.my-xl-3{margin-top:1rem!important;margin-bottom:1rem!important}.m-xl-4{margin:1.5rem 1.5rem!important}.mt-xl-4{margin-top:1.5rem!important}.mr-xl-4{margin-right:1.5rem!important}.mb-xl-4{margin-bottom:1.5rem!important}.ml-xl-4{margin-left:1.5rem!important}.mx-xl-4{margin-right:1.5rem!important;margin-left:1.5rem!important}.my-xl-4{margin-top:1.5rem!important;margin-bottom:1.5rem!important}.m-xl-5{margin:3rem 3rem!important}.mt-xl-5{margin-top:3rem!important}.mr-xl-5{margin-right:3rem!important}.mb-xl-5{margin-bottom:3rem!important}.ml-xl-5{margin-left:3rem!important}.mx-xl-5{margin-right:3rem!important;margin-left:3rem!important}.my-xl-5{margin-top:3rem!important;margin-bottom:3rem!important}.p-xl-0{padding:0 0!important}.pt-xl-0{padding-top:0!important}.pr-xl-0{padding-right:0!important}.pb-xl-0{padding-bottom:0!important}.pl-xl-0{padding-left:0!important}.px-xl-0{padding-right:0!important;padding-left:0!important}.py-xl-0{padding-top:0!important;padding-bottom:0!important}.p-xl-1{padding:.25rem .25rem!important}.pt-xl-1{padding-top:.25rem!important}.pr-xl-1{padding-right:.25rem!important}.pb-xl-1{padding-bottom:.25rem!important}.pl-xl-1{padding-left:.25rem!important}.px-xl-1{padding-right:.25rem!important;padding-left:.25rem!important}.py-xl-1{padding-top:.25rem!important;padding-bottom:.25rem!important}.p-xl-2{padding:.5rem .5rem!important}.pt-xl-2{padding-top:.5rem!important}.pr-xl-2{padding-right:.5rem!important}.pb-xl-2{padding-bottom:.5rem!important}.pl-xl-2{padding-left:.5rem!important}.px-xl-2{padding-right:.5rem!important;padding-left:.5rem!important}.py-xl-2{padding-top:.5rem!important;padding-bottom:.5rem!important}.p-xl-3{padding:1rem 1rem!important}.pt-xl-3{padding-top:1rem!important}.pr-xl-3{padding-right:1rem!important}.pb-xl-3{padding-bottom:1rem!important}.pl-xl-3{padding-left:1rem!important}.px-xl-3{padding-right:1rem!important;padding-left:1rem!important}.py-xl-3{padding-top:1rem!important;padding-bottom:1rem!important}.p-xl-4{padding:1.5rem 1.5rem!important}.pt-xl-4{padding-top:1.5rem!important}.pr-xl-4{padding-right:1.5rem!important}.pb-xl-4{padding-bottom:1.5rem!important}.pl-xl-4{padding-left:1.5rem!important}.px-xl-4{padding-right:1.5rem!important;padding-left:1.5rem!important}.py-xl-4{padding-top:1.5rem!important;padding-bottom:1.5rem!important}.p-xl-5{padding:3rem 3rem!important}.pt-xl-5{padding-top:3rem!important}.pr-xl-5{padding-right:3rem!important}.pb-xl-5{padding-bottom:3rem!important}.pl-xl-5{padding-left:3rem!important}.px-xl-5{padding-right:3rem!important;padding-left:3rem!important}.py-xl-5{padding-top:3rem!important;padding-bottom:3rem!important}.m-xl-auto{margin:auto!important}.mt-xl-auto{margin-top:auto!important}.mr-xl-auto{margin-right:auto!important}.mb-xl-auto{margin-bottom:auto!important}.ml-xl-auto{margin-left:auto!important}.mx-xl-auto{margin-right:auto!important;margin-left:auto!important}.my-xl-auto{margin-top:auto!important;margin-bottom:auto!important}}.text-justify{text-align:justify!important}.text-nowrap{white-space:nowrap!important}.text-truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.text-left{text-align:left!important}.text-right{text-align:right!important}.text-center{text-align:center!important}@media (min-width:576px){.text-sm-left{text-align:left!important}.text-sm-right{text-align:right!important}.text-sm-center{text-align:center!important}}@media (min-width:768px){.text-md-left{text-align:left!important}.text-md-right{text-align:right!important}.text-md-center{text-align:center!important}}@media (min-width:992px){.text-lg-left{text-align:left!important}.text-lg-right{text-align:right!important}.text-lg-center{text-align:center!important}}@media (min-width:1200px){.text-xl-left{text-align:left!important}.text-xl-right{text-align:right!important}.text-xl-center{text-align:center!important}}.text-lowercase{text-transform:lowercase!important}.text-uppercase{text-transform:uppercase!important}.text-capitalize{text-transform:capitalize!important}.font-weight-normal{font-weight:400}.font-weight-bold{font-weight:700}.font-italic{font-style:italic}.text-white{color:#fff!important}.text-muted{color:#636c72!important}a.text-muted:focus,a.text-muted:hover{color:#4b5257!important}.text-primary{color:#0275d8!important}a.text-primary:focus,a.text-primary:hover{color:#025aa5!important}.text-success{color:#5cb85c!important}a.text-success:focus,a.text-success:hover{color:#449d44!important}.text-info{color:#5bc0de!important}a.text-info:focus,a.text-info:hover{color:#31b0d5!important}.text-warning{color:#f0ad4e!important}a.text-warning:focus,a.text-warning:hover{color:#ec971f!important}.text-danger{color:#d9534f!important}a.text-danger:focus,a.text-danger:hover{color:#c9302c!important}.text-gray-dark{color:#292b2c!important}a.text-gray-dark:focus,a.text-gray-dark:hover{color:#101112!important}.text-hide{font:0/0 a;color:transparent;text-shadow:none;background-color:transparent;border:0}.invisible{visibility:hidden!important}.hidden-xs-up{display:none!important}@media (max-width:575px){.hidden-xs-down{display:none!important}}@media (min-width:576px){.hidden-sm-up{display:none!important}}@media (max-width:767px){.hidden-sm-down{display:none!important}}@media (min-width:768px){.hidden-md-up{display:none!important}}@media (max-width:991px){.hidden-md-down{display:none!important}}@media (min-width:992px){.hidden-lg-up{display:none!important}}@media (max-width:1199px){.hidden-lg-down{display:none!important}}@media (min-width:1200px){.hidden-xl-up{display:none!important}}.hidden-xl-down{display:none!important}.visible-print-block{display:none!important}@media print{.visible-print-block{display:block!important}}.visible-print-inline{display:none!important}@media print{.visible-print-inline{display:inline!important}}.visible-print-inline-block{display:none!important}@media print{.visible-print-inline-block{display:inline-block!important}}@media print{.hidden-print{display:none!important}}/*# sourceMappingURL=bootstrap.min.css.map */
    """
    bootstrap = """/*!
    * Bootstrap v4.0.0-beta (https://getbootstrap.com)
    * Copyright 2011-2017 The Bootstrap Authors
    * Copyright 2011-2017 Twitter, Inc.
    * Licensed under MIT (https://github.com/twbs/bootstrap/blob/master/LICENSE)
    */
    @media print {
    *,
    *::before,
    *::after {
        text-shadow: none !important;
        box-shadow: none !important;
    }
    a,
    a:visited {
        text-decoration: underline;
    }
    abbr[title]::after {
        content: " (" attr(title) ")";
    }
    pre {
        white-space: pre-wrap !important;
    }
    pre,
    blockquote {
        border: 1px solid #999;
        page-break-inside: avoid;
    }
    thead {
        display: table-header-group;
    }
    tr,
    img {
        page-break-inside: avoid;
    }
    p,
    h2,
    h3 {
        orphans: 3;
        widows: 3;
    }
    h2,
    h3 {
        page-break-after: avoid;
    }
    .navbar {
        display: none;
    }
    .badge {
        border: 1px solid #000;
    }
    .table {
        border-collapse: collapse !important;
    }
    .table td,
    .table th {
        background-color: #fff !important;
    }
    .table-bordered th,
    .table-bordered td {
        border: 1px solid #ddd !important;
    }
    }

    html {
    box-sizing: border-box;
    font-family: sans-serif;
    line-height: 1.15;
    -webkit-text-size-adjust: 100%;
    -ms-text-size-adjust: 100%;
    -ms-overflow-style: scrollbar;
    -webkit-tap-highlight-color: transparent;
    }

    *,
    *::before,
    *::after {
    box-sizing: inherit;
    }

    @-ms-viewport {
    width: device-width;
    }

    article, aside, dialog, figcaption, figure, footer, header, hgroup, main, nav, section {
    display: block;
    }

    body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 1rem;
    font-weight: normal;
    line-height: 1.5;
    color: #212529;
    background-color: #fff;
    }

    [tabindex="-1"]:focus {
    outline: none !important;
    }

    hr {
    box-sizing: content-box;
    height: 0;
    overflow: visible;
    }

    h1, h2, h3, h4, h5, h6 {
    margin-top: 0;
    margin-bottom: .5rem;
    }

    p {
    margin-top: 0;
    margin-bottom: 1rem;
    }

    abbr[title],
    abbr[data-original-title] {
    text-decoration: underline;
    -webkit-text-decoration: underline dotted;
            text-decoration: underline dotted;
    cursor: help;
    border-bottom: 0;
    }

    address {
    margin-bottom: 1rem;
    font-style: normal;
    line-height: inherit;
    }

    ol,
    ul,
    dl {
    margin-top: 0;
    margin-bottom: 1rem;
    }

    ol ol,
    ul ul,
    ol ul,
    ul ol {
    margin-bottom: 0;
    }

    dt {
    font-weight: bold;
    }

    dd {
    margin-bottom: .5rem;
    margin-left: 0;
    }

    blockquote {
    margin: 0 0 1rem;
    }

    dfn {
    font-style: italic;
    }

    b,
    strong {
    font-weight: bolder;
    }

    small {
    font-size: 80%;
    }

    sub,
    sup {
    position: relative;
    font-size: 75%;
    line-height: 0;
    vertical-align: baseline;
    }

    sub {
    bottom: -.25em;
    }

    sup {
    top: -.5em;
    }

    a {
    color: #007bff;
    text-decoration: none;
    background-color: transparent;
    -webkit-text-decoration-skip: objects;
    }

    a:hover {
    color: #0056b3;
    text-decoration: underline;
    }

    a:not([href]):not([tabindex]) {
    color: inherit;
    text-decoration: none;
    }

    a:not([href]):not([tabindex]):focus, a:not([href]):not([tabindex]):hover {
    color: inherit;
    text-decoration: none;
    }

    a:not([href]):not([tabindex]):focus {
    outline: 0;
    }

    pre,
    code,
    kbd,
    samp {
    font-family: monospace, monospace;
    font-size: 1em;
    }

    pre {
    margin-top: 0;
    margin-bottom: 1rem;
    overflow: auto;
    }

    figure {
    margin: 0 0 1rem;
    }

    img {
    vertical-align: middle;
    border-style: none;
    }

    svg:not(:root) {
    overflow: hidden;
    }

    a,
    area,
    button,
    [role="button"],
    input,
    label,
    select,
    summary,
    textarea {
    -ms-touch-action: manipulation;
        touch-action: manipulation;
    }

    table {
    border-collapse: collapse;
    }

    caption {
    padding-top: 0.75rem;
    padding-bottom: 0.75rem;
    color: #868e96;
    text-align: left;
    caption-side: bottom;
    }

    th {
    text-align: left;
    }

    label {
    display: inline-block;
    margin-bottom: .5rem;
    }

    button:focus {
    outline: 1px dotted;
    outline: 5px auto -webkit-focus-ring-color;
    }

    input,
    button,
    select,
    optgroup,
    textarea {
    margin: 0;
    font-family: inherit;
    font-size: inherit;
    line-height: inherit;
    }

    button,
    input {
    overflow: visible;
    }

    button,
    select {
    text-transform: none;
    }

    button,
    html [type="button"],
    [type="reset"],
    [type="submit"] {
    -webkit-appearance: button;
    }

    button::-moz-focus-inner,
    [type="button"]::-moz-focus-inner,
    [type="reset"]::-moz-focus-inner,
    [type="submit"]::-moz-focus-inner {
    padding: 0;
    border-style: none;
    }

    input[type="radio"],
    input[type="checkbox"] {
    box-sizing: border-box;
    padding: 0;
    }

    input[type="date"],
    input[type="time"],
    input[type="datetime-local"],
    input[type="month"] {
    -webkit-appearance: listbox;
    }

    textarea {
    overflow: auto;
    resize: vertical;
    }

    fieldset {
    min-width: 0;
    padding: 0;
    margin: 0;
    border: 0;
    }

    legend {
    display: block;
    width: 100%;
    max-width: 100%;
    padding: 0;
    margin-bottom: .5rem;
    font-size: 1.5rem;
    line-height: inherit;
    color: inherit;
    white-space: normal;
    }

    progress {
    vertical-align: baseline;
    }

    [type="number"]::-webkit-inner-spin-button,
    [type="number"]::-webkit-outer-spin-button {
    height: auto;
    }

    [type="search"] {
    outline-offset: -2px;
    -webkit-appearance: none;
    }

    [type="search"]::-webkit-search-cancel-button,
    [type="search"]::-webkit-search-decoration {
    -webkit-appearance: none;
    }

    ::-webkit-file-upload-button {
    font: inherit;
    -webkit-appearance: button;
    }

    output {
    display: inline-block;
    }

    summary {
    display: list-item;
    }

    template {
    display: none;
    }

    [hidden] {
    display: none !important;
    }

    h1, h2, h3, h4, h5, h6,
    .h1, .h2, .h3, .h4, .h5, .h6 {
    margin-bottom: 0.5rem;
    font-family: inherit;
    font-weight: 500;
    line-height: 1.1;
    color: inherit;
    }

    h1, .h1 {
    font-size: 2.5rem;
    }

    h2, .h2 {
    font-size: 2rem;
    }

    h3, .h3 {
    font-size: 1.75rem;
    }

    h4, .h4 {
    font-size: 1.5rem;
    }

    h5, .h5 {
    font-size: 1.25rem;
    }

    h6, .h6 {
    font-size: 1rem;
    }

    .lead {
    font-size: 1.25rem;
    font-weight: 300;
    }

    .display-1 {
    font-size: 6rem;
    font-weight: 300;
    line-height: 1.1;
    }

    .display-2 {
    font-size: 5.5rem;
    font-weight: 300;
    line-height: 1.1;
    }

    .display-3 {
    font-size: 4.5rem;
    font-weight: 300;
    line-height: 1.1;
    }

    .display-4 {
    font-size: 3.5rem;
    font-weight: 300;
    line-height: 1.1;
    }

    hr {
    margin-top: 1rem;
    margin-bottom: 1rem;
    border: 0;
    border-top: 1px solid rgba(0, 0, 0, 0.1);
    }

    small,
    .small {
    font-size: 80%;
    font-weight: normal;
    }

    mark,
    .mark {
    padding: 0.2em;
    background-color: #fcf8e3;
    }

    .list-unstyled {
    padding-left: 0;
    list-style: none;
    }

    .list-inline {
    padding-left: 0;
    list-style: none;
    }

    .list-inline-item {
    display: inline-block;
    }

    .list-inline-item:not(:last-child) {
    margin-right: 5px;
    }

    .initialism {
    font-size: 90%;
    text-transform: uppercase;
    }

    .blockquote {
    margin-bottom: 1rem;
    font-size: 1.25rem;
    }

    .blockquote-footer {
    display: block;
    font-size: 80%;
    color: #868e96;
    }

    .blockquote-footer::before {
    content: "\2014 \00A0";
    }

    .img-fluid {
    max-width: 100%;
    height: auto;
    }

    .img-thumbnail {
    padding: 0.25rem;
    background-color: #fff;
    border: 1px solid #ddd;
    border-radius: 0.25rem;
    transition: all 0.2s ease-in-out;
    max-width: 100%;
    height: auto;
    }

    .figure {
    display: inline-block;
    }

    .figure-img {
    margin-bottom: 0.5rem;
    line-height: 1;
    }

    .figure-caption {
    font-size: 90%;
    color: #868e96;
    }

    code,
    kbd,
    pre,
    samp {
    font-family: Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }

    code {
    padding: 0.2rem 0.4rem;
    font-size: 90%;
    color: #bd4147;
    background-color: #f8f9fa;
    border-radius: 0.25rem;
    }

    a > code {
    padding: 0;
    color: inherit;
    background-color: inherit;
    }

    kbd {
    padding: 0.2rem 0.4rem;
    font-size: 90%;
    color: #fff;
    background-color: #212529;
    border-radius: 0.2rem;
    }

    kbd kbd {
    padding: 0;
    font-size: 100%;
    font-weight: bold;
    }

    pre {
    display: block;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 90%;
    color: #212529;
    }

    pre code {
    padding: 0;
    font-size: inherit;
    color: inherit;
    background-color: transparent;
    border-radius: 0;
    }

    .pre-scrollable {
    max-height: 340px;
    overflow-y: scroll;
    }

    .container {
    margin-right: auto;
    margin-left: auto;
    padding-right: 15px;
    padding-left: 15px;
    width: 100%;
    }

    @media (min-width: 576px) {
    .container {
        max-width: 540px;
    }
    }

    @media (min-width: 768px) {
    .container {
        max-width: 720px;
    }
    }

    @media (min-width: 992px) {
    .container {
        max-width: 960px;
    }
    }

    @media (min-width: 1200px) {
    .container {
        max-width: 1140px;
    }
    }

    .container-fluid {
    width: 100%;
    margin-right: auto;
    margin-left: auto;
    padding-right: 15px;
    padding-left: 15px;
    width: 100%;
    }

    .row {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-wrap: wrap;
        flex-wrap: wrap;
    margin-right: -15px;
    margin-left: -15px;
    }

    .no-gutters {
    margin-right: 0;
    margin-left: 0;
    }

    .no-gutters > .col,
    .no-gutters > [class*="col-"] {
    padding-right: 0;
    padding-left: 0;
    }

    .col-1, .col-2, .col-3, .col-4, .col-5, .col-6, .col-7, .col-8, .col-9, .col-10, .col-11, .col-12, .col,
    .col-auto, .col-sm-1, .col-sm-2, .col-sm-3, .col-sm-4, .col-sm-5, .col-sm-6, .col-sm-7, .col-sm-8, .col-sm-9, .col-sm-10, .col-sm-11, .col-sm-12, .col-sm,
    .col-sm-auto, .col-md-1, .col-md-2, .col-md-3, .col-md-4, .col-md-5, .col-md-6, .col-md-7, .col-md-8, .col-md-9, .col-md-10, .col-md-11, .col-md-12, .col-md,
    .col-md-auto, .col-lg-1, .col-lg-2, .col-lg-3, .col-lg-4, .col-lg-5, .col-lg-6, .col-lg-7, .col-lg-8, .col-lg-9, .col-lg-10, .col-lg-11, .col-lg-12, .col-lg,
    .col-lg-auto, .col-xl-1, .col-xl-2, .col-xl-3, .col-xl-4, .col-xl-5, .col-xl-6, .col-xl-7, .col-xl-8, .col-xl-9, .col-xl-10, .col-xl-11, .col-xl-12, .col-xl,
    .col-xl-auto {
    position: relative;
    width: 100%;
    min-height: 1px;
    padding-right: 15px;
    padding-left: 15px;
    }

    .col {
    -ms-flex-preferred-size: 0;
        flex-basis: 0;
    -ms-flex-positive: 1;
        flex-grow: 1;
    max-width: 100%;
    }

    .col-auto {
    -ms-flex: 0 0 auto;
        flex: 0 0 auto;
    width: auto;
    max-width: none;
    }

    .col-1 {
    -ms-flex: 0 0 8.333333%;
        flex: 0 0 8.333333%;
    max-width: 8.333333%;
    }

    .col-2 {
    -ms-flex: 0 0 16.666667%;
        flex: 0 0 16.666667%;
    max-width: 16.666667%;
    }

    .col-3 {
    -ms-flex: 0 0 25%;
        flex: 0 0 25%;
    max-width: 25%;
    }

    .col-4 {
    -ms-flex: 0 0 33.333333%;
        flex: 0 0 33.333333%;
    max-width: 33.333333%;
    }

    .col-5 {
    -ms-flex: 0 0 41.666667%;
        flex: 0 0 41.666667%;
    max-width: 41.666667%;
    }

    .col-6 {
    -ms-flex: 0 0 50%;
        flex: 0 0 50%;
    max-width: 50%;
    }

    .col-7 {
    -ms-flex: 0 0 58.333333%;
        flex: 0 0 58.333333%;
    max-width: 58.333333%;
    }

    .col-8 {
    -ms-flex: 0 0 66.666667%;
        flex: 0 0 66.666667%;
    max-width: 66.666667%;
    }

    .col-9 {
    -ms-flex: 0 0 75%;
        flex: 0 0 75%;
    max-width: 75%;
    }

    .col-10 {
    -ms-flex: 0 0 83.333333%;
        flex: 0 0 83.333333%;
    max-width: 83.333333%;
    }

    .col-11 {
    -ms-flex: 0 0 91.666667%;
        flex: 0 0 91.666667%;
    max-width: 91.666667%;
    }

    .col-12 {
    -ms-flex: 0 0 100%;
        flex: 0 0 100%;
    max-width: 100%;
    }

    .order-1 {
    -ms-flex-order: 1;
        order: 1;
    }

    .order-2 {
    -ms-flex-order: 2;
        order: 2;
    }

    .order-3 {
    -ms-flex-order: 3;
        order: 3;
    }

    .order-4 {
    -ms-flex-order: 4;
        order: 4;
    }

    .order-5 {
    -ms-flex-order: 5;
        order: 5;
    }

    .order-6 {
    -ms-flex-order: 6;
        order: 6;
    }

    .order-7 {
    -ms-flex-order: 7;
        order: 7;
    }

    .order-8 {
    -ms-flex-order: 8;
        order: 8;
    }

    .order-9 {
    -ms-flex-order: 9;
        order: 9;
    }

    .order-10 {
    -ms-flex-order: 10;
        order: 10;
    }

    .order-11 {
    -ms-flex-order: 11;
        order: 11;
    }

    .order-12 {
    -ms-flex-order: 12;
        order: 12;
    }

    @media (min-width: 576px) {
    .col-sm {
        -ms-flex-preferred-size: 0;
            flex-basis: 0;
        -ms-flex-positive: 1;
            flex-grow: 1;
        max-width: 100%;
    }
    .col-sm-auto {
        -ms-flex: 0 0 auto;
            flex: 0 0 auto;
        width: auto;
        max-width: none;
    }
    .col-sm-1 {
        -ms-flex: 0 0 8.333333%;
            flex: 0 0 8.333333%;
        max-width: 8.333333%;
    }
    .col-sm-2 {
        -ms-flex: 0 0 16.666667%;
            flex: 0 0 16.666667%;
        max-width: 16.666667%;
    }
    .col-sm-3 {
        -ms-flex: 0 0 25%;
            flex: 0 0 25%;
        max-width: 25%;
    }
    .col-sm-4 {
        -ms-flex: 0 0 33.333333%;
            flex: 0 0 33.333333%;
        max-width: 33.333333%;
    }
    .col-sm-5 {
        -ms-flex: 0 0 41.666667%;
            flex: 0 0 41.666667%;
        max-width: 41.666667%;
    }
    .col-sm-6 {
        -ms-flex: 0 0 50%;
            flex: 0 0 50%;
        max-width: 50%;
    }
    .col-sm-7 {
        -ms-flex: 0 0 58.333333%;
            flex: 0 0 58.333333%;
        max-width: 58.333333%;
    }
    .col-sm-8 {
        -ms-flex: 0 0 66.666667%;
            flex: 0 0 66.666667%;
        max-width: 66.666667%;
    }
    .col-sm-9 {
        -ms-flex: 0 0 75%;
            flex: 0 0 75%;
        max-width: 75%;
    }
    .col-sm-10 {
        -ms-flex: 0 0 83.333333%;
            flex: 0 0 83.333333%;
        max-width: 83.333333%;
    }
    .col-sm-11 {
        -ms-flex: 0 0 91.666667%;
            flex: 0 0 91.666667%;
        max-width: 91.666667%;
    }
    .col-sm-12 {
        -ms-flex: 0 0 100%;
            flex: 0 0 100%;
        max-width: 100%;
    }
    .order-sm-1 {
        -ms-flex-order: 1;
            order: 1;
    }
    .order-sm-2 {
        -ms-flex-order: 2;
            order: 2;
    }
    .order-sm-3 {
        -ms-flex-order: 3;
            order: 3;
    }
    .order-sm-4 {
        -ms-flex-order: 4;
            order: 4;
    }
    .order-sm-5 {
        -ms-flex-order: 5;
            order: 5;
    }
    .order-sm-6 {
        -ms-flex-order: 6;
            order: 6;
    }
    .order-sm-7 {
        -ms-flex-order: 7;
            order: 7;
    }
    .order-sm-8 {
        -ms-flex-order: 8;
            order: 8;
    }
    .order-sm-9 {
        -ms-flex-order: 9;
            order: 9;
    }
    .order-sm-10 {
        -ms-flex-order: 10;
            order: 10;
    }
    .order-sm-11 {
        -ms-flex-order: 11;
            order: 11;
    }
    .order-sm-12 {
        -ms-flex-order: 12;
            order: 12;
    }
    }

    @media (min-width: 768px) {
    .col-md {
        -ms-flex-preferred-size: 0;
            flex-basis: 0;
        -ms-flex-positive: 1;
            flex-grow: 1;
        max-width: 100%;
    }
    .col-md-auto {
        -ms-flex: 0 0 auto;
            flex: 0 0 auto;
        width: auto;
        max-width: none;
    }
    .col-md-1 {
        -ms-flex: 0 0 8.333333%;
            flex: 0 0 8.333333%;
        max-width: 8.333333%;
    }
    .col-md-2 {
        -ms-flex: 0 0 16.666667%;
            flex: 0 0 16.666667%;
        max-width: 16.666667%;
    }
    .col-md-3 {
        -ms-flex: 0 0 25%;
            flex: 0 0 25%;
        max-width: 25%;
    }
    .col-md-4 {
        -ms-flex: 0 0 33.333333%;
            flex: 0 0 33.333333%;
        max-width: 33.333333%;
    }
    .col-md-5 {
        -ms-flex: 0 0 41.666667%;
            flex: 0 0 41.666667%;
        max-width: 41.666667%;
    }
    .col-md-6 {
        -ms-flex: 0 0 50%;
            flex: 0 0 50%;
        max-width: 50%;
    }
    .col-md-7 {
        -ms-flex: 0 0 58.333333%;
            flex: 0 0 58.333333%;
        max-width: 58.333333%;
    }
    .col-md-8 {
        -ms-flex: 0 0 66.666667%;
            flex: 0 0 66.666667%;
        max-width: 66.666667%;
    }
    .col-md-9 {
        -ms-flex: 0 0 75%;
            flex: 0 0 75%;
        max-width: 75%;
    }
    .col-md-10 {
        -ms-flex: 0 0 83.333333%;
            flex: 0 0 83.333333%;
        max-width: 83.333333%;
    }
    .col-md-11 {
        -ms-flex: 0 0 91.666667%;
            flex: 0 0 91.666667%;
        max-width: 91.666667%;
    }
    .col-md-12 {
        -ms-flex: 0 0 100%;
            flex: 0 0 100%;
        max-width: 100%;
    }
    .order-md-1 {
        -ms-flex-order: 1;
            order: 1;
    }
    .order-md-2 {
        -ms-flex-order: 2;
            order: 2;
    }
    .order-md-3 {
        -ms-flex-order: 3;
            order: 3;
    }
    .order-md-4 {
        -ms-flex-order: 4;
            order: 4;
    }
    .order-md-5 {
        -ms-flex-order: 5;
            order: 5;
    }
    .order-md-6 {
        -ms-flex-order: 6;
            order: 6;
    }
    .order-md-7 {
        -ms-flex-order: 7;
            order: 7;
    }
    .order-md-8 {
        -ms-flex-order: 8;
            order: 8;
    }
    .order-md-9 {
        -ms-flex-order: 9;
            order: 9;
    }
    .order-md-10 {
        -ms-flex-order: 10;
            order: 10;
    }
    .order-md-11 {
        -ms-flex-order: 11;
            order: 11;
    }
    .order-md-12 {
        -ms-flex-order: 12;
            order: 12;
    }
    }

    @media (min-width: 992px) {
    .col-lg {
        -ms-flex-preferred-size: 0;
            flex-basis: 0;
        -ms-flex-positive: 1;
            flex-grow: 1;
        max-width: 100%;
    }
    .col-lg-auto {
        -ms-flex: 0 0 auto;
            flex: 0 0 auto;
        width: auto;
        max-width: none;
    }
    .col-lg-1 {
        -ms-flex: 0 0 8.333333%;
            flex: 0 0 8.333333%;
        max-width: 8.333333%;
    }
    .col-lg-2 {
        -ms-flex: 0 0 16.666667%;
            flex: 0 0 16.666667%;
        max-width: 16.666667%;
    }
    .col-lg-3 {
        -ms-flex: 0 0 25%;
            flex: 0 0 25%;
        max-width: 25%;
    }
    .col-lg-4 {
        -ms-flex: 0 0 33.333333%;
            flex: 0 0 33.333333%;
        max-width: 33.333333%;
    }
    .col-lg-5 {
        -ms-flex: 0 0 41.666667%;
            flex: 0 0 41.666667%;
        max-width: 41.666667%;
    }
    .col-lg-6 {
        -ms-flex: 0 0 50%;
            flex: 0 0 50%;
        max-width: 50%;
    }
    .col-lg-7 {
        -ms-flex: 0 0 58.333333%;
            flex: 0 0 58.333333%;
        max-width: 58.333333%;
    }
    .col-lg-8 {
        -ms-flex: 0 0 66.666667%;
            flex: 0 0 66.666667%;
        max-width: 66.666667%;
    }
    .col-lg-9 {
        -ms-flex: 0 0 75%;
            flex: 0 0 75%;
        max-width: 75%;
    }
    .col-lg-10 {
        -ms-flex: 0 0 83.333333%;
            flex: 0 0 83.333333%;
        max-width: 83.333333%;
    }
    .col-lg-11 {
        -ms-flex: 0 0 91.666667%;
            flex: 0 0 91.666667%;
        max-width: 91.666667%;
    }
    .col-lg-12 {
        -ms-flex: 0 0 100%;
            flex: 0 0 100%;
        max-width: 100%;
    }
    .order-lg-1 {
        -ms-flex-order: 1;
            order: 1;
    }
    .order-lg-2 {
        -ms-flex-order: 2;
            order: 2;
    }
    .order-lg-3 {
        -ms-flex-order: 3;
            order: 3;
    }
    .order-lg-4 {
        -ms-flex-order: 4;
            order: 4;
    }
    .order-lg-5 {
        -ms-flex-order: 5;
            order: 5;
    }
    .order-lg-6 {
        -ms-flex-order: 6;
            order: 6;
    }
    .order-lg-7 {
        -ms-flex-order: 7;
            order: 7;
    }
    .order-lg-8 {
        -ms-flex-order: 8;
            order: 8;
    }
    .order-lg-9 {
        -ms-flex-order: 9;
            order: 9;
    }
    .order-lg-10 {
        -ms-flex-order: 10;
            order: 10;
    }
    .order-lg-11 {
        -ms-flex-order: 11;
            order: 11;
    }
    .order-lg-12 {
        -ms-flex-order: 12;
            order: 12;
    }
    }

    @media (min-width: 1200px) {
    .col-xl {
        -ms-flex-preferred-size: 0;
            flex-basis: 0;
        -ms-flex-positive: 1;
            flex-grow: 1;
        max-width: 100%;
    }
    .col-xl-auto {
        -ms-flex: 0 0 auto;
            flex: 0 0 auto;
        width: auto;
        max-width: none;
    }
    .col-xl-1 {
        -ms-flex: 0 0 8.333333%;
            flex: 0 0 8.333333%;
        max-width: 8.333333%;
    }
    .col-xl-2 {
        -ms-flex: 0 0 16.666667%;
            flex: 0 0 16.666667%;
        max-width: 16.666667%;
    }
    .col-xl-3 {
        -ms-flex: 0 0 25%;
            flex: 0 0 25%;
        max-width: 25%;
    }
    .col-xl-4 {
        -ms-flex: 0 0 33.333333%;
            flex: 0 0 33.333333%;
        max-width: 33.333333%;
    }
    .col-xl-5 {
        -ms-flex: 0 0 41.666667%;
            flex: 0 0 41.666667%;
        max-width: 41.666667%;
    }
    .col-xl-6 {
        -ms-flex: 0 0 50%;
            flex: 0 0 50%;
        max-width: 50%;
    }
    .col-xl-7 {
        -ms-flex: 0 0 58.333333%;
            flex: 0 0 58.333333%;
        max-width: 58.333333%;
    }
    .col-xl-8 {
        -ms-flex: 0 0 66.666667%;
            flex: 0 0 66.666667%;
        max-width: 66.666667%;
    }
    .col-xl-9 {
        -ms-flex: 0 0 75%;
            flex: 0 0 75%;
        max-width: 75%;
    }
    .col-xl-10 {
        -ms-flex: 0 0 83.333333%;
            flex: 0 0 83.333333%;
        max-width: 83.333333%;
    }
    .col-xl-11 {
        -ms-flex: 0 0 91.666667%;
            flex: 0 0 91.666667%;
        max-width: 91.666667%;
    }
    .col-xl-12 {
        -ms-flex: 0 0 100%;
            flex: 0 0 100%;
        max-width: 100%;
    }
    .order-xl-1 {
        -ms-flex-order: 1;
            order: 1;
    }
    .order-xl-2 {
        -ms-flex-order: 2;
            order: 2;
    }
    .order-xl-3 {
        -ms-flex-order: 3;
            order: 3;
    }
    .order-xl-4 {
        -ms-flex-order: 4;
            order: 4;
    }
    .order-xl-5 {
        -ms-flex-order: 5;
            order: 5;
    }
    .order-xl-6 {
        -ms-flex-order: 6;
            order: 6;
    }
    .order-xl-7 {
        -ms-flex-order: 7;
            order: 7;
    }
    .order-xl-8 {
        -ms-flex-order: 8;
            order: 8;
    }
    .order-xl-9 {
        -ms-flex-order: 9;
            order: 9;
    }
    .order-xl-10 {
        -ms-flex-order: 10;
            order: 10;
    }
    .order-xl-11 {
        -ms-flex-order: 11;
            order: 11;
    }
    .order-xl-12 {
        -ms-flex-order: 12;
            order: 12;
    }
    }

    .table {
    width: 100%;
    max-width: 100%;
    margin-bottom: 1rem;
    background-color: transparent;
    }

    .table th,
    .table td {
    padding: 0.75rem;
    vertical-align: top;
    border-top: 1px solid #e9ecef;
    }

    .table thead th {
    vertical-align: bottom;
    border-bottom: 2px solid #e9ecef;
    }

    .table tbody + tbody {
    border-top: 2px solid #e9ecef;
    }

    .table .table {
    background-color: #fff;
    }

    .table-sm th,
    .table-sm td {
    padding: 0.3rem;
    }

    .table-bordered {
    border: 1px solid #e9ecef;
    }

    .table-bordered th,
    .table-bordered td {
    border: 1px solid #e9ecef;
    }

    .table-bordered thead th,
    .table-bordered thead td {
    border-bottom-width: 2px;
    }

    .table-striped tbody tr:nth-of-type(odd) {
    background-color: rgba(0, 0, 0, 0.05);
    }

    .table-hover tbody tr:hover {
    background-color: rgba(0, 0, 0, 0.075);
    }

    .table-primary,
    .table-primary > th,
    .table-primary > td {
    background-color: #b8daff;
    }

    .table-hover .table-primary:hover {
    background-color: #9fcdff;
    }

    .table-hover .table-primary:hover > td,
    .table-hover .table-primary:hover > th {
    background-color: #9fcdff;
    }

    .table-secondary,
    .table-secondary > th,
    .table-secondary > td {
    background-color: #dddfe2;
    }

    .table-hover .table-secondary:hover {
    background-color: #cfd2d6;
    }

    .table-hover .table-secondary:hover > td,
    .table-hover .table-secondary:hover > th {
    background-color: #cfd2d6;
    }

    .table-success,
    .table-success > th,
    .table-success > td {
    background-color: #c3e6cb;
    }

    .table-hover .table-success:hover {
    background-color: #b1dfbb;
    }

    .table-hover .table-success:hover > td,
    .table-hover .table-success:hover > th {
    background-color: #b1dfbb;
    }

    .table-info,
    .table-info > th,
    .table-info > td {
    background-color: #bee5eb;
    }

    .table-hover .table-info:hover {
    background-color: #abdde5;
    }

    .table-hover .table-info:hover > td,
    .table-hover .table-info:hover > th {
    background-color: #abdde5;
    }

    .table-warning,
    .table-warning > th,
    .table-warning > td {
    background-color: #ffeeba;
    }

    .table-hover .table-warning:hover {
    background-color: #ffe8a1;
    }

    .table-hover .table-warning:hover > td,
    .table-hover .table-warning:hover > th {
    background-color: #ffe8a1;
    }

    .table-danger,
    .table-danger > th,
    .table-danger > td {
    background-color: #f5c6cb;
    }

    .table-hover .table-danger:hover {
    background-color: #f1b0b7;
    }

    .table-hover .table-danger:hover > td,
    .table-hover .table-danger:hover > th {
    background-color: #f1b0b7;
    }

    .table-light,
    .table-light > th,
    .table-light > td {
    background-color: #fdfdfe;
    }

    .table-hover .table-light:hover {
    background-color: #ececf6;
    }

    .table-hover .table-light:hover > td,
    .table-hover .table-light:hover > th {
    background-color: #ececf6;
    }

    .table-dark,
    .table-dark > th,
    .table-dark > td {
    background-color: #c6c8ca;
    }

    .table-hover .table-dark:hover {
    background-color: #b9bbbe;
    }

    .table-hover .table-dark:hover > td,
    .table-hover .table-dark:hover > th {
    background-color: #b9bbbe;
    }

    .table-active,
    .table-active > th,
    .table-active > td {
    background-color: rgba(0, 0, 0, 0.075);
    }

    .table-hover .table-active:hover {
    background-color: rgba(0, 0, 0, 0.075);
    }

    .table-hover .table-active:hover > td,
    .table-hover .table-active:hover > th {
    background-color: rgba(0, 0, 0, 0.075);
    }

    .thead-inverse th {
    color: #fff;
    background-color: #212529;
    }

    .thead-default th {
    color: #495057;
    background-color: #e9ecef;
    }

    .table-inverse {
    color: #fff;
    background-color: #212529;
    }

    .table-inverse th,
    .table-inverse td,
    .table-inverse thead th {
    border-color: #32383e;
    }

    .table-inverse.table-bordered {
    border: 0;
    }

    .table-inverse.table-striped tbody tr:nth-of-type(odd) {
    background-color: rgba(255, 255, 255, 0.05);
    }

    .table-inverse.table-hover tbody tr:hover {
    background-color: rgba(255, 255, 255, 0.075);
    }

    @media (max-width: 991px) {
    .table-responsive {
        display: block;
        width: 100%;
        overflow-x: auto;
        -ms-overflow-style: -ms-autohiding-scrollbar;
    }
    .table-responsive.table-bordered {
        border: 0;
    }
    }

    .form-control {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    font-size: 1rem;
    line-height: 1.25;
    color: #495057;
    background-color: #fff;
    background-image: none;
    background-clip: padding-box;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 0.25rem;
    transition: border-color ease-in-out 0.15s, box-shadow ease-in-out 0.15s;
    }

    .form-control::-ms-expand {
    background-color: transparent;
    border: 0;
    }

    .form-control:focus {
    color: #495057;
    background-color: #fff;
    border-color: #80bdff;
    outline: none;
    }

    .form-control::-webkit-input-placeholder {
    color: #868e96;
    opacity: 1;
    }

    .form-control:-ms-input-placeholder {
    color: #868e96;
    opacity: 1;
    }

    .form-control::placeholder {
    color: #868e96;
    opacity: 1;
    }

    .form-control:disabled, .form-control[readonly] {
    background-color: #e9ecef;
    opacity: 1;
    }

    select.form-control:not([size]):not([multiple]) {
    height: calc(2.25rem + 2px);
    }

    select.form-control:focus::-ms-value {
    color: #495057;
    background-color: #fff;
    }

    .form-control-file,
    .form-control-range {
    display: block;
    }

    .col-form-label {
    padding-top: calc(0.5rem - 1px * 2);
    padding-bottom: calc(0.5rem - 1px * 2);
    margin-bottom: 0;
    }

    .col-form-label-lg {
    padding-top: calc(0.5rem - 1px * 2);
    padding-bottom: calc(0.5rem - 1px * 2);
    font-size: 1.25rem;
    }

    .col-form-label-sm {
    padding-top: calc(0.25rem - 1px * 2);
    padding-bottom: calc(0.25rem - 1px * 2);
    font-size: 0.875rem;
    }

    .col-form-legend {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
    margin-bottom: 0;
    font-size: 1rem;
    }

    .form-control-plaintext {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
    margin-bottom: 0;
    line-height: 1.25;
    border: solid transparent;
    border-width: 1px 0;
    }

    .form-control-plaintext.form-control-sm, .input-group-sm > .form-control-plaintext.form-control,
    .input-group-sm > .form-control-plaintext.input-group-addon,
    .input-group-sm > .input-group-btn > .form-control-plaintext.btn, .form-control-plaintext.form-control-lg, .input-group-lg > .form-control-plaintext.form-control,
    .input-group-lg > .form-control-plaintext.input-group-addon,
    .input-group-lg > .input-group-btn > .form-control-plaintext.btn {
    padding-right: 0;
    padding-left: 0;
    }

    .form-control-sm, .input-group-sm > .form-control,
    .input-group-sm > .input-group-addon,
    .input-group-sm > .input-group-btn > .btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    line-height: 1.5;
    border-radius: 0.2rem;
    }

    select.form-control-sm:not([size]):not([multiple]), .input-group-sm > select.form-control:not([size]):not([multiple]),
    .input-group-sm > select.input-group-addon:not([size]):not([multiple]),
    .input-group-sm > .input-group-btn > select.btn:not([size]):not([multiple]) {
    height: calc(1.8125rem + 2px);
    }

    .form-control-lg, .input-group-lg > .form-control,
    .input-group-lg > .input-group-addon,
    .input-group-lg > .input-group-btn > .btn {
    padding: 0.5rem 1rem;
    font-size: 1.25rem;
    line-height: 1.5;
    border-radius: 0.3rem;
    }

    select.form-control-lg:not([size]):not([multiple]), .input-group-lg > select.form-control:not([size]):not([multiple]),
    .input-group-lg > select.input-group-addon:not([size]):not([multiple]),
    .input-group-lg > .input-group-btn > select.btn:not([size]):not([multiple]) {
    height: calc(2.3125rem + 2px);
    }

    .form-group {
    margin-bottom: 1rem;
    }

    .form-text {
    display: block;
    margin-top: 0.25rem;
    }

    .form-row {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-wrap: wrap;
        flex-wrap: wrap;
    margin-right: -5px;
    margin-left: -5px;
    }

    .form-row > .col,
    .form-row > [class*="col-"] {
    padding-right: 5px;
    padding-left: 5px;
    }

    .form-check {
    position: relative;
    display: block;
    margin-bottom: 0.5rem;
    }

    .form-check.disabled .form-check-label {
    color: #868e96;
    }

    .form-check-label {
    padding-left: 1.25rem;
    margin-bottom: 0;
    }

    .form-check-input {
    position: absolute;
    margin-top: 0.25rem;
    margin-left: -1.25rem;
    }

    .form-check-input:only-child {
    position: static;
    }

    .form-check-inline {
    display: inline-block;
    }

    .form-check-inline .form-check-label {
    vertical-align: middle;
    }

    .form-check-inline + .form-check-inline {
    margin-left: 0.75rem;
    }

    .invalid-feedback {
    display: none;
    margin-top: .25rem;
    font-size: .875rem;
    color: #dc3545;
    }

    .invalid-tooltip {
    position: absolute;
    top: 100%;
    z-index: 5;
    display: none;
    width: 250px;
    padding: .5rem;
    margin-top: .1rem;
    font-size: .875rem;
    line-height: 1;
    color: #fff;
    background-color: rgba(220, 53, 69, 0.8);
    border-radius: .2rem;
    }

    .was-validated .form-control:valid, .form-control.is-valid, .was-validated
    .custom-select:valid,
    .custom-select.is-valid {
    border-color: #28a745;
    }

    .was-validated .form-control:valid:focus, .form-control.is-valid:focus, .was-validated
    .custom-select:valid:focus,
    .custom-select.is-valid:focus {
    box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25);
    }

    .was-validated .form-control:valid ~ .invalid-feedback,
    .was-validated .form-control:valid ~ .invalid-tooltip, .form-control.is-valid ~ .invalid-feedback,
    .form-control.is-valid ~ .invalid-tooltip, .was-validated
    .custom-select:valid ~ .invalid-feedback,
    .was-validated
    .custom-select:valid ~ .invalid-tooltip,
    .custom-select.is-valid ~ .invalid-feedback,
    .custom-select.is-valid ~ .invalid-tooltip {
    display: block;
    }

    .was-validated .form-check-input:valid + .form-check-label, .form-check-input.is-valid + .form-check-label {
    color: #28a745;
    }

    .was-validated .custom-control-input:valid ~ .custom-control-indicator, .custom-control-input.is-valid ~ .custom-control-indicator {
    background-color: rgba(40, 167, 69, 0.25);
    }

    .was-validated .custom-control-input:valid ~ .custom-control-description, .custom-control-input.is-valid ~ .custom-control-description {
    color: #28a745;
    }

    .was-validated .custom-file-input:valid ~ .custom-file-control, .custom-file-input.is-valid ~ .custom-file-control {
    border-color: #28a745;
    }

    .was-validated .custom-file-input:valid ~ .custom-file-control::before, .custom-file-input.is-valid ~ .custom-file-control::before {
    border-color: inherit;
    }

    .was-validated .custom-file-input:valid:focus, .custom-file-input.is-valid:focus {
    box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25);
    }

    .was-validated .form-control:invalid, .form-control.is-invalid, .was-validated
    .custom-select:invalid,
    .custom-select.is-invalid {
    border-color: #dc3545;
    }

    .was-validated .form-control:invalid:focus, .form-control.is-invalid:focus, .was-validated
    .custom-select:invalid:focus,
    .custom-select.is-invalid:focus {
    box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
    }

    .was-validated .form-control:invalid ~ .invalid-feedback,
    .was-validated .form-control:invalid ~ .invalid-tooltip, .form-control.is-invalid ~ .invalid-feedback,
    .form-control.is-invalid ~ .invalid-tooltip, .was-validated
    .custom-select:invalid ~ .invalid-feedback,
    .was-validated
    .custom-select:invalid ~ .invalid-tooltip,
    .custom-select.is-invalid ~ .invalid-feedback,
    .custom-select.is-invalid ~ .invalid-tooltip {
    display: block;
    }

    .was-validated .form-check-input:invalid + .form-check-label, .form-check-input.is-invalid + .form-check-label {
    color: #dc3545;
    }

    .was-validated .custom-control-input:invalid ~ .custom-control-indicator, .custom-control-input.is-invalid ~ .custom-control-indicator {
    background-color: rgba(220, 53, 69, 0.25);
    }

    .was-validated .custom-control-input:invalid ~ .custom-control-description, .custom-control-input.is-invalid ~ .custom-control-description {
    color: #dc3545;
    }

    .was-validated .custom-file-input:invalid ~ .custom-file-control, .custom-file-input.is-invalid ~ .custom-file-control {
    border-color: #dc3545;
    }

    .was-validated .custom-file-input:invalid ~ .custom-file-control::before, .custom-file-input.is-invalid ~ .custom-file-control::before {
    border-color: inherit;
    }

    .was-validated .custom-file-input:invalid:focus, .custom-file-input.is-invalid:focus {
    box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
    }

    .form-inline {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-flow: row wrap;
        flex-flow: row wrap;
    -ms-flex-align: center;
        align-items: center;
    }

    .form-inline .form-check {
    width: 100%;
    }

    @media (min-width: 576px) {
    .form-inline label {
        display: -ms-flexbox;
        display: flex;
        -ms-flex-align: center;
            align-items: center;
        -ms-flex-pack: center;
            justify-content: center;
        margin-bottom: 0;
    }
    .form-inline .form-group {
        display: -ms-flexbox;
        display: flex;
        -ms-flex: 0 0 auto;
            flex: 0 0 auto;
        -ms-flex-flow: row wrap;
            flex-flow: row wrap;
        -ms-flex-align: center;
            align-items: center;
        margin-bottom: 0;
    }
    .form-inline .form-control {
        display: inline-block;
        width: auto;
        vertical-align: middle;
    }
    .form-inline .form-control-plaintext {
        display: inline-block;
    }
    .form-inline .input-group {
        width: auto;
    }
    .form-inline .form-control-label {
        margin-bottom: 0;
        vertical-align: middle;
    }
    .form-inline .form-check {
        display: -ms-flexbox;
        display: flex;
        -ms-flex-align: center;
            align-items: center;
        -ms-flex-pack: center;
            justify-content: center;
        width: auto;
        margin-top: 0;
        margin-bottom: 0;
    }
    .form-inline .form-check-label {
        padding-left: 0;
    }
    .form-inline .form-check-input {
        position: relative;
        margin-top: 0;
        margin-right: 0.25rem;
        margin-left: 0;
    }
    .form-inline .custom-control {
        display: -ms-flexbox;
        display: flex;
        -ms-flex-align: center;
            align-items: center;
        -ms-flex-pack: center;
            justify-content: center;
        padding-left: 0;
    }
    .form-inline .custom-control-indicator {
        position: static;
        display: inline-block;
        margin-right: 0.25rem;
        vertical-align: text-bottom;
    }
    .form-inline .has-feedback .form-control-feedback {
        top: 0;
    }
    }

    .btn {
    display: inline-block;
    font-weight: normal;
    text-align: center;
    white-space: nowrap;
    vertical-align: middle;
    -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
            user-select: none;
    border: 1px solid transparent;
    padding: 0.5rem 0.75rem;
    font-size: 1rem;
    line-height: 1.25;
    border-radius: 0.25rem;
    transition: all 0.15s ease-in-out;
    }

    .btn:focus, .btn:hover {
    text-decoration: none;
    }

    .btn:focus, .btn.focus {
    outline: 0;
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.25);
    }

    .btn.disabled, .btn:disabled {
    opacity: .65;
    }

    .btn:active, .btn.active {
    background-image: none;
    }

    a.btn.disabled,
    fieldset[disabled] a.btn {
    pointer-events: none;
    }

    .btn-primary {
    color: #fff;
    background-color: #007bff;
    border-color: #007bff;
    }

    .btn-primary:hover {
    color: #fff;
    background-color: #0069d9;
    border-color: #0062cc;
    }

    .btn-primary:focus, .btn-primary.focus {
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.5);
    }

    .btn-primary.disabled, .btn-primary:disabled {
    background-color: #007bff;
    border-color: #007bff;
    }

    .btn-primary:active, .btn-primary.active,
    .show > .btn-primary.dropdown-toggle {
    background-color: #0069d9;
    background-image: none;
    border-color: #0062cc;
    }

    .btn-secondary {
    color: #fff;
    background-color: #868e96;
    border-color: #868e96;
    }

    .btn-secondary:hover {
    color: #fff;
    background-color: #727b84;
    border-color: #6c757d;
    }

    .btn-secondary:focus, .btn-secondary.focus {
    box-shadow: 0 0 0 3px rgba(134, 142, 150, 0.5);
    }

    .btn-secondary.disabled, .btn-secondary:disabled {
    background-color: #868e96;
    border-color: #868e96;
    }

    .btn-secondary:active, .btn-secondary.active,
    .show > .btn-secondary.dropdown-toggle {
    background-color: #727b84;
    background-image: none;
    border-color: #6c757d;
    }

    .btn-success {
    color: #fff;
    background-color: #28a745;
    border-color: #28a745;
    }

    .btn-success:hover {
    color: #fff;
    background-color: #218838;
    border-color: #1e7e34;
    }

    .btn-success:focus, .btn-success.focus {
    box-shadow: 0 0 0 3px rgba(40, 167, 69, 0.5);
    }

    .btn-success.disabled, .btn-success:disabled {
    background-color: #28a745;
    border-color: #28a745;
    }

    .btn-success:active, .btn-success.active,
    .show > .btn-success.dropdown-toggle {
    background-color: #218838;
    background-image: none;
    border-color: #1e7e34;
    }

    .btn-info {
    color: #fff;
    background-color: #17a2b8;
    border-color: #17a2b8;
    }

    .btn-info:hover {
    color: #fff;
    background-color: #138496;
    border-color: #117a8b;
    }

    .btn-info:focus, .btn-info.focus {
    box-shadow: 0 0 0 3px rgba(23, 162, 184, 0.5);
    }

    .btn-info.disabled, .btn-info:disabled {
    background-color: #17a2b8;
    border-color: #17a2b8;
    }

    .btn-info:active, .btn-info.active,
    .show > .btn-info.dropdown-toggle {
    background-color: #138496;
    background-image: none;
    border-color: #117a8b;
    }

    .btn-warning {
    color: #111;
    background-color: #ffc107;
    border-color: #ffc107;
    }

    .btn-warning:hover {
    color: #111;
    background-color: #e0a800;
    border-color: #d39e00;
    }

    .btn-warning:focus, .btn-warning.focus {
    box-shadow: 0 0 0 3px rgba(255, 193, 7, 0.5);
    }

    .btn-warning.disabled, .btn-warning:disabled {
    background-color: #ffc107;
    border-color: #ffc107;
    }

    .btn-warning:active, .btn-warning.active,
    .show > .btn-warning.dropdown-toggle {
    background-color: #e0a800;
    background-image: none;
    border-color: #d39e00;
    }

    .btn-danger {
    color: #fff;
    background-color: #dc3545;
    border-color: #dc3545;
    }

    .btn-danger:hover {
    color: #fff;
    background-color: #c82333;
    border-color: #bd2130;
    }

    .btn-danger:focus, .btn-danger.focus {
    box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.5);
    }

    .btn-danger.disabled, .btn-danger:disabled {
    background-color: #dc3545;
    border-color: #dc3545;
    }

    .btn-danger:active, .btn-danger.active,
    .show > .btn-danger.dropdown-toggle {
    background-color: #c82333;
    background-image: none;
    border-color: #bd2130;
    }

    .btn-light {
    color: #111;
    background-color: #f8f9fa;
    border-color: #f8f9fa;
    }

    .btn-light:hover {
    color: #111;
    background-color: #e2e6ea;
    border-color: #dae0e5;
    }

    .btn-light:focus, .btn-light.focus {
    box-shadow: 0 0 0 3px rgba(248, 249, 250, 0.5);
    }

    .btn-light.disabled, .btn-light:disabled {
    background-color: #f8f9fa;
    border-color: #f8f9fa;
    }

    .btn-light:active, .btn-light.active,
    .show > .btn-light.dropdown-toggle {
    background-color: #e2e6ea;
    background-image: none;
    border-color: #dae0e5;
    }

    .btn-dark {
    color: #fff;
    background-color: #343a40;
    border-color: #343a40;
    }

    .btn-dark:hover {
    color: #fff;
    background-color: #23272b;
    border-color: #1d2124;
    }

    .btn-dark:focus, .btn-dark.focus {
    box-shadow: 0 0 0 3px rgba(52, 58, 64, 0.5);
    }

    .btn-dark.disabled, .btn-dark:disabled {
    background-color: #343a40;
    border-color: #343a40;
    }

    .btn-dark:active, .btn-dark.active,
    .show > .btn-dark.dropdown-toggle {
    background-color: #23272b;
    background-image: none;
    border-color: #1d2124;
    }

    .btn-outline-primary {
    color: #007bff;
    background-color: transparent;
    background-image: none;
    border-color: #007bff;
    }

    .btn-outline-primary:hover {
    color: #fff;
    background-color: #007bff;
    border-color: #007bff;
    }

    .btn-outline-primary:focus, .btn-outline-primary.focus {
    box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.5);
    }

    .btn-outline-primary.disabled, .btn-outline-primary:disabled {
    color: #007bff;
    background-color: transparent;
    }

    .btn-outline-primary:active, .btn-outline-primary.active,
    .show > .btn-outline-primary.dropdown-toggle {
    color: #fff;
    background-color: #007bff;
    border-color: #007bff;
    }

    .btn-outline-secondary {
    color: #868e96;
    background-color: transparent;
    background-image: none;
    border-color: #868e96;
    }

    .btn-outline-secondary:hover {
    color: #fff;
    background-color: #868e96;
    border-color: #868e96;
    }

    .btn-outline-secondary:focus, .btn-outline-secondary.focus {
    box-shadow: 0 0 0 3px rgba(134, 142, 150, 0.5);
    }

    .btn-outline-secondary.disabled, .btn-outline-secondary:disabled {
    color: #868e96;
    background-color: transparent;
    }

    .btn-outline-secondary:active, .btn-outline-secondary.active,
    .show > .btn-outline-secondary.dropdown-toggle {
    color: #fff;
    background-color: #868e96;
    border-color: #868e96;
    }

    .btn-outline-success {
    color: #28a745;
    background-color: transparent;
    background-image: none;
    border-color: #28a745;
    }

    .btn-outline-success:hover {
    color: #fff;
    background-color: #28a745;
    border-color: #28a745;
    }

    .btn-outline-success:focus, .btn-outline-success.focus {
    box-shadow: 0 0 0 3px rgba(40, 167, 69, 0.5);
    }

    .btn-outline-success.disabled, .btn-outline-success:disabled {
    color: #28a745;
    background-color: transparent;
    }

    .btn-outline-success:active, .btn-outline-success.active,
    .show > .btn-outline-success.dropdown-toggle {
    color: #fff;
    background-color: #28a745;
    border-color: #28a745;
    }

    .btn-outline-info {
    color: #17a2b8;
    background-color: transparent;
    background-image: none;
    border-color: #17a2b8;
    }

    .btn-outline-info:hover {
    color: #fff;
    background-color: #17a2b8;
    border-color: #17a2b8;
    }

    .btn-outline-info:focus, .btn-outline-info.focus {
    box-shadow: 0 0 0 3px rgba(23, 162, 184, 0.5);
    }

    .btn-outline-info.disabled, .btn-outline-info:disabled {
    color: #17a2b8;
    background-color: transparent;
    }

    .btn-outline-info:active, .btn-outline-info.active,
    .show > .btn-outline-info.dropdown-toggle {
    color: #fff;
    background-color: #17a2b8;
    border-color: #17a2b8;
    }

    .btn-outline-warning {
    color: #ffc107;
    background-color: transparent;
    background-image: none;
    border-color: #ffc107;
    }

    .btn-outline-warning:hover {
    color: #fff;
    background-color: #ffc107;
    border-color: #ffc107;
    }

    .btn-outline-warning:focus, .btn-outline-warning.focus {
    box-shadow: 0 0 0 3px rgba(255, 193, 7, 0.5);
    }

    .btn-outline-warning.disabled, .btn-outline-warning:disabled {
    color: #ffc107;
    background-color: transparent;
    }

    .btn-outline-warning:active, .btn-outline-warning.active,
    .show > .btn-outline-warning.dropdown-toggle {
    color: #fff;
    background-color: #ffc107;
    border-color: #ffc107;
    }

    .btn-outline-danger {
    color: #dc3545;
    background-color: transparent;
    background-image: none;
    border-color: #dc3545;
    }

    .btn-outline-danger:hover {
    color: #fff;
    background-color: #dc3545;
    border-color: #dc3545;
    }

    .btn-outline-danger:focus, .btn-outline-danger.focus {
    box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.5);
    }

    .btn-outline-danger.disabled, .btn-outline-danger:disabled {
    color: #dc3545;
    background-color: transparent;
    }

    .btn-outline-danger:active, .btn-outline-danger.active,
    .show > .btn-outline-danger.dropdown-toggle {
    color: #fff;
    background-color: #dc3545;
    border-color: #dc3545;
    }

    .btn-outline-light {
    color: #f8f9fa;
    background-color: transparent;
    background-image: none;
    border-color: #f8f9fa;
    }

    .btn-outline-light:hover {
    color: #fff;
    background-color: #f8f9fa;
    border-color: #f8f9fa;
    }

    .btn-outline-light:focus, .btn-outline-light.focus {
    box-shadow: 0 0 0 3px rgba(248, 249, 250, 0.5);
    }

    .btn-outline-light.disabled, .btn-outline-light:disabled {
    color: #f8f9fa;
    background-color: transparent;
    }

    .btn-outline-light:active, .btn-outline-light.active,
    .show > .btn-outline-light.dropdown-toggle {
    color: #fff;
    background-color: #f8f9fa;
    border-color: #f8f9fa;
    }

    .btn-outline-dark {
    color: #343a40;
    background-color: transparent;
    background-image: none;
    border-color: #343a40;
    }

    .btn-outline-dark:hover {
    color: #fff;
    background-color: #343a40;
    border-color: #343a40;
    }

    .btn-outline-dark:focus, .btn-outline-dark.focus {
    box-shadow: 0 0 0 3px rgba(52, 58, 64, 0.5);
    }

    .btn-outline-dark.disabled, .btn-outline-dark:disabled {
    color: #343a40;
    background-color: transparent;
    }

    .btn-outline-dark:active, .btn-outline-dark.active,
    .show > .btn-outline-dark.dropdown-toggle {
    color: #fff;
    background-color: #343a40;
    border-color: #343a40;
    }

    .btn-link {
    font-weight: normal;
    color: #007bff;
    border-radius: 0;
    }

    .btn-link, .btn-link:active, .btn-link.active, .btn-link:disabled {
    background-color: transparent;
    }

    .btn-link, .btn-link:focus, .btn-link:active {
    border-color: transparent;
    box-shadow: none;
    }

    .btn-link:hover {
    border-color: transparent;
    }

    .btn-link:focus, .btn-link:hover {
    color: #0056b3;
    text-decoration: underline;
    background-color: transparent;
    }

    .btn-link:disabled {
    color: #868e96;
    }

    .btn-link:disabled:focus, .btn-link:disabled:hover {
    text-decoration: none;
    }

    .btn-lg, .btn-group-lg > .btn {
    padding: 0.5rem 1rem;
    font-size: 1.25rem;
    line-height: 1.5;
    border-radius: 0.3rem;
    }

    .btn-sm, .btn-group-sm > .btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    line-height: 1.5;
    border-radius: 0.2rem;
    }

    .btn-block {
    display: block;
    width: 100%;
    }

    .btn-block + .btn-block {
    margin-top: 0.5rem;
    }

    input[type="submit"].btn-block,
    input[type="reset"].btn-block,
    input[type="button"].btn-block {
    width: 100%;
    }

    .fade {
    opacity: 0;
    transition: opacity 0.15s linear;
    }

    .fade.show {
    opacity: 1;
    }

    .collapse {
    display: none;
    }

    .collapse.show {
    display: block;
    }

    tr.collapse.show {
    display: table-row;
    }

    tbody.collapse.show {
    display: table-row-group;
    }

    .collapsing {
    position: relative;
    height: 0;
    overflow: hidden;
    transition: height 0.35s ease;
    }

    .dropup,
    .dropdown {
    position: relative;
    }

    .dropdown-toggle::after {
    display: inline-block;
    width: 0;
    height: 0;
    margin-left: 0.255em;
    vertical-align: 0.255em;
    content: "";
    border-top: 0.3em solid;
    border-right: 0.3em solid transparent;
    border-left: 0.3em solid transparent;
    }

    .dropdown-toggle:empty::after {
    margin-left: 0;
    }

    .dropup .dropdown-menu {
    margin-top: 0;
    margin-bottom: 0.125rem;
    }

    .dropup .dropdown-toggle::after {
    border-top: 0;
    border-bottom: 0.3em solid;
    }

    .dropdown-menu {
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 1000;
    display: none;
    float: left;
    min-width: 10rem;
    padding: 0.5rem 0;
    margin: 0.125rem 0 0;
    font-size: 1rem;
    color: #212529;
    text-align: left;
    list-style: none;
    background-color: #fff;
    background-clip: padding-box;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 0.25rem;
    }

    .dropdown-divider {
    height: 0;
    margin: 0.5rem 0;
    overflow: hidden;
    border-top: 1px solid #e9ecef;
    }

    .dropdown-item {
    display: block;
    width: 100%;
    padding: 0.25rem 1.5rem;
    clear: both;
    font-weight: normal;
    color: #212529;
    text-align: inherit;
    white-space: nowrap;
    background: none;
    border: 0;
    }

    .dropdown-item:focus, .dropdown-item:hover {
    color: #16181b;
    text-decoration: none;
    background-color: #f8f9fa;
    }

    .dropdown-item.active, .dropdown-item:active {
    color: #fff;
    text-decoration: none;
    background-color: #007bff;
    }

    .dropdown-item.disabled, .dropdown-item:disabled {
    color: #868e96;
    background-color: transparent;
    }

    .show > a {
    outline: 0;
    }

    .dropdown-menu.show {
    display: block;
    }

    .dropdown-header {
    display: block;
    padding: 0.5rem 1.5rem;
    margin-bottom: 0;
    font-size: 0.875rem;
    color: #868e96;
    white-space: nowrap;
    }

    .btn-group,
    .btn-group-vertical {
    position: relative;
    display: -ms-inline-flexbox;
    display: inline-flex;
    vertical-align: middle;
    }

    .btn-group > .btn,
    .btn-group-vertical > .btn {
    position: relative;
    -ms-flex: 0 1 auto;
        flex: 0 1 auto;
    margin-bottom: 0;
    }

    .btn-group > .btn:hover,
    .btn-group-vertical > .btn:hover {
    z-index: 2;
    }

    .btn-group > .btn:focus, .btn-group > .btn:active, .btn-group > .btn.active,
    .btn-group-vertical > .btn:focus,
    .btn-group-vertical > .btn:active,
    .btn-group-vertical > .btn.active {
    z-index: 2;
    }

    .btn-group .btn + .btn,
    .btn-group .btn + .btn-group,
    .btn-group .btn-group + .btn,
    .btn-group .btn-group + .btn-group,
    .btn-group-vertical .btn + .btn,
    .btn-group-vertical .btn + .btn-group,
    .btn-group-vertical .btn-group + .btn,
    .btn-group-vertical .btn-group + .btn-group {
    margin-left: -1px;
    }

    .btn-toolbar {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-wrap: wrap;
        flex-wrap: wrap;
    -ms-flex-pack: start;
        justify-content: flex-start;
    }

    .btn-toolbar .input-group {
    width: auto;
    }

    .btn-group > .btn:not(:first-child):not(:last-child):not(.dropdown-toggle) {
    border-radius: 0;
    }

    .btn-group > .btn:first-child {
    margin-left: 0;
    }

    .btn-group > .btn:first-child:not(:last-child):not(.dropdown-toggle) {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    }

    .btn-group > .btn:last-child:not(:first-child),
    .btn-group > .dropdown-toggle:not(:first-child) {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    }

    .btn-group > .btn-group {
    float: left;
    }

    .btn-group > .btn-group:not(:first-child):not(:last-child) > .btn {
    border-radius: 0;
    }

    .btn-group > .btn-group:first-child:not(:last-child) > .btn:last-child,
    .btn-group > .btn-group:first-child:not(:last-child) > .dropdown-toggle {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    }

    .btn-group > .btn-group:last-child:not(:first-child) > .btn:first-child {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    }

    .btn + .dropdown-toggle-split {
    padding-right: 0.5625rem;
    padding-left: 0.5625rem;
    }

    .btn + .dropdown-toggle-split::after {
    margin-left: 0;
    }

    .btn-sm + .dropdown-toggle-split, .btn-group-sm > .btn + .dropdown-toggle-split {
    padding-right: 0.375rem;
    padding-left: 0.375rem;
    }

    .btn-lg + .dropdown-toggle-split, .btn-group-lg > .btn + .dropdown-toggle-split {
    padding-right: 0.75rem;
    padding-left: 0.75rem;
    }

    .btn-group-vertical {
    display: -ms-inline-flexbox;
    display: inline-flex;
    -ms-flex-direction: column;
        flex-direction: column;
    -ms-flex-align: start;
        align-items: flex-start;
    -ms-flex-pack: center;
        justify-content: center;
    }

    .btn-group-vertical .btn,
    .btn-group-vertical .btn-group {
    width: 100%;
    }

    .btn-group-vertical > .btn + .btn,
    .btn-group-vertical > .btn + .btn-group,
    .btn-group-vertical > .btn-group + .btn,
    .btn-group-vertical > .btn-group + .btn-group {
    margin-top: -1px;
    margin-left: 0;
    }

    .btn-group-vertical > .btn:not(:first-child):not(:last-child) {
    border-radius: 0;
    }

    .btn-group-vertical > .btn:first-child:not(:last-child) {
    border-bottom-right-radius: 0;
    border-bottom-left-radius: 0;
    }

    .btn-group-vertical > .btn:last-child:not(:first-child) {
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    }

    .btn-group-vertical > .btn-group:not(:first-child):not(:last-child) > .btn {
    border-radius: 0;
    }

    .btn-group-vertical > .btn-group:first-child:not(:last-child) > .btn:last-child,
    .btn-group-vertical > .btn-group:first-child:not(:last-child) > .dropdown-toggle {
    border-bottom-right-radius: 0;
    border-bottom-left-radius: 0;
    }

    .btn-group-vertical > .btn-group:last-child:not(:first-child) > .btn:first-child {
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    }

    [data-toggle="buttons"] > .btn input[type="radio"],
    [data-toggle="buttons"] > .btn input[type="checkbox"],
    [data-toggle="buttons"] > .btn-group > .btn input[type="radio"],
    [data-toggle="buttons"] > .btn-group > .btn input[type="checkbox"] {
    position: absolute;
    clip: rect(0, 0, 0, 0);
    pointer-events: none;
    }

    .input-group {
    position: relative;
    display: -ms-flexbox;
    display: flex;
    width: 100%;
    }

    .input-group .form-control {
    position: relative;
    z-index: 2;
    -ms-flex: 1 1 auto;
        flex: 1 1 auto;
    width: 1%;
    margin-bottom: 0;
    }

    .input-group .form-control:focus, .input-group .form-control:active, .input-group .form-control:hover {
    z-index: 3;
    }

    .input-group-addon,
    .input-group-btn,
    .input-group .form-control {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-align: center;
        align-items: center;
    }

    .input-group-addon:not(:first-child):not(:last-child),
    .input-group-btn:not(:first-child):not(:last-child),
    .input-group .form-control:not(:first-child):not(:last-child) {
    border-radius: 0;
    }

    .input-group-addon,
    .input-group-btn {
    white-space: nowrap;
    vertical-align: middle;
    }

    .input-group-addon {
    padding: 0.5rem 0.75rem;
    margin-bottom: 0;
    font-size: 1rem;
    font-weight: normal;
    line-height: 1.25;
    color: #495057;
    text-align: center;
    background-color: #e9ecef;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 0.25rem;
    }

    .input-group-addon.form-control-sm,
    .input-group-sm > .input-group-addon,
    .input-group-sm > .input-group-btn > .input-group-addon.btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    border-radius: 0.2rem;
    }

    .input-group-addon.form-control-lg,
    .input-group-lg > .input-group-addon,
    .input-group-lg > .input-group-btn > .input-group-addon.btn {
    padding: 0.5rem 1rem;
    font-size: 1.25rem;
    border-radius: 0.3rem;
    }

    .input-group-addon input[type="radio"],
    .input-group-addon input[type="checkbox"] {
    margin-top: 0;
    }

    .input-group .form-control:not(:last-child),
    .input-group-addon:not(:last-child),
    .input-group-btn:not(:last-child) > .btn,
    .input-group-btn:not(:last-child) > .btn-group > .btn,
    .input-group-btn:not(:last-child) > .dropdown-toggle,
    .input-group-btn:not(:first-child) > .btn:not(:last-child):not(.dropdown-toggle),
    .input-group-btn:not(:first-child) > .btn-group:not(:last-child) > .btn {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    }

    .input-group-addon:not(:last-child) {
    border-right: 0;
    }

    .input-group .form-control:not(:first-child),
    .input-group-addon:not(:first-child),
    .input-group-btn:not(:first-child) > .btn,
    .input-group-btn:not(:first-child) > .btn-group > .btn,
    .input-group-btn:not(:first-child) > .dropdown-toggle,
    .input-group-btn:not(:last-child) > .btn:not(:first-child),
    .input-group-btn:not(:last-child) > .btn-group:not(:first-child) > .btn {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    }

    .form-control + .input-group-addon:not(:first-child) {
    border-left: 0;
    }

    .input-group-btn {
    position: relative;
    font-size: 0;
    white-space: nowrap;
    }

    .input-group-btn > .btn {
    position: relative;
    }

    .input-group-btn > .btn + .btn {
    margin-left: -1px;
    }

    .input-group-btn > .btn:focus, .input-group-btn > .btn:active, .input-group-btn > .btn:hover {
    z-index: 3;
    }

    .input-group-btn:not(:last-child) > .btn,
    .input-group-btn:not(:last-child) > .btn-group {
    margin-right: -1px;
    }

    .input-group-btn:not(:first-child) > .btn,
    .input-group-btn:not(:first-child) > .btn-group {
    z-index: 2;
    margin-left: -1px;
    }

    .input-group-btn:not(:first-child) > .btn:focus, .input-group-btn:not(:first-child) > .btn:active, .input-group-btn:not(:first-child) > .btn:hover,
    .input-group-btn:not(:first-child) > .btn-group:focus,
    .input-group-btn:not(:first-child) > .btn-group:active,
    .input-group-btn:not(:first-child) > .btn-group:hover {
    z-index: 3;
    }

    .custom-control {
    position: relative;
    display: -ms-inline-flexbox;
    display: inline-flex;
    min-height: 1.5rem;
    padding-left: 1.5rem;
    margin-right: 1rem;
    }

    .custom-control-input {
    position: absolute;
    z-index: -1;
    opacity: 0;
    }

    .custom-control-input:checked ~ .custom-control-indicator {
    color: #fff;
    background-color: #007bff;
    }

    .custom-control-input:focus ~ .custom-control-indicator {
    box-shadow: 0 0 0 1px #fff, 0 0 0 3px #007bff;
    }

    .custom-control-input:active ~ .custom-control-indicator {
    color: #fff;
    background-color: #b3d7ff;
    }

    .custom-control-input:disabled ~ .custom-control-indicator {
    background-color: #e9ecef;
    }

    .custom-control-input:disabled ~ .custom-control-description {
    color: #868e96;
    }

    .custom-control-indicator {
    position: absolute;
    top: 0.25rem;
    left: 0;
    display: block;
    width: 1rem;
    height: 1rem;
    pointer-events: none;
    -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
            user-select: none;
    background-color: #ddd;
    background-repeat: no-repeat;
    background-position: center center;
    background-size: 50% 50%;
    }

    .custom-checkbox .custom-control-indicator {
    border-radius: 0.25rem;
    }

    .custom-checkbox .custom-control-input:checked ~ .custom-control-indicator {
    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 8 8'%3E%3Cpath fill='%23fff' d='M6.564.75l-3.59 3.612-1.538-1.55L0 4.26 2.974 7.25 8 2.193z'/%3E%3C/svg%3E");
    }

    .custom-checkbox .custom-control-input:indeterminate ~ .custom-control-indicator {
    background-color: #007bff;
    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 4 4'%3E%3Cpath stroke='%23fff' d='M0 2h4'/%3E%3C/svg%3E");
    }

    .custom-radio .custom-control-indicator {
    border-radius: 50%;
    }

    .custom-radio .custom-control-input:checked ~ .custom-control-indicator {
    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3E%3Ccircle r='3' fill='%23fff'/%3E%3C/svg%3E");
    }

    .custom-controls-stacked {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-direction: column;
        flex-direction: column;
    }

    .custom-controls-stacked .custom-control {
    margin-bottom: 0.25rem;
    }

    .custom-controls-stacked .custom-control + .custom-control {
    margin-left: 0;
    }

    .custom-select {
    display: inline-block;
    max-width: 100%;
    height: calc(2.25rem + 2px);
    padding: 0.375rem 1.75rem 0.375rem 0.75rem;
    line-height: 1.25;
    color: #495057;
    vertical-align: middle;
    background: #fff url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 4 5'%3E%3Cpath fill='%23333' d='M2 0L0 2h4zm0 5L0 3h4z'/%3E%3C/svg%3E") no-repeat right 0.75rem center;
    background-size: 8px 10px;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 0.25rem;
    -webkit-appearance: none;
        -moz-appearance: none;
            appearance: none;
    }

    .custom-select:focus {
    border-color: #80bdff;
    outline: none;
    }

    .custom-select:focus::-ms-value {
    color: #495057;
    background-color: #fff;
    }

    .custom-select:disabled {
    color: #868e96;
    background-color: #e9ecef;
    }

    .custom-select::-ms-expand {
    opacity: 0;
    }

    .custom-select-sm {
    height: calc(1.8125rem + 2px);
    padding-top: 0.375rem;
    padding-bottom: 0.375rem;
    font-size: 75%;
    }

    .custom-file {
    position: relative;
    display: inline-block;
    max-width: 100%;
    height: 2.5rem;
    margin-bottom: 0;
    }

    .custom-file-input {
    min-width: 14rem;
    max-width: 100%;
    height: 2.5rem;
    margin: 0;
    opacity: 0;
    }

    .custom-file-control {
    position: absolute;
    top: 0;
    right: 0;
    left: 0;
    z-index: 5;
    height: 2.5rem;
    padding: 0.5rem 1rem;
    line-height: 1.5;
    color: #495057;
    pointer-events: none;
    -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
            user-select: none;
    background-color: #fff;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 0.25rem;
    }

    .custom-file-control:lang(en):empty::after {
    content: "Choose file...";
    }

    .custom-file-control::before {
    position: absolute;
    top: -1px;
    right: -1px;
    bottom: -1px;
    z-index: 6;
    display: block;
    height: 2.5rem;
    padding: 0.5rem 1rem;
    line-height: 1.5;
    color: #495057;
    background-color: #e9ecef;
    border: 1px solid rgba(0, 0, 0, 0.15);
    border-radius: 0 0.25rem 0.25rem 0;
    }

    .custom-file-control:lang(en)::before {
    content: "Browse";
    }

    .nav {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-wrap: wrap;
        flex-wrap: wrap;
    padding-left: 0;
    margin-bottom: 0;
    list-style: none;
    }

    .nav-link {
    display: block;
    padding: 0.5rem 1rem;
    }

    .nav-link:focus, .nav-link:hover {
    text-decoration: none;
    }

    .nav-link.disabled {
    color: #868e96;
    }

    .nav-tabs {
    border-bottom: 1px solid #ddd;
    }

    .nav-tabs .nav-item {
    margin-bottom: -1px;
    }

    .nav-tabs .nav-link {
    border: 1px solid transparent;
    border-top-left-radius: 0.25rem;
    border-top-right-radius: 0.25rem;
    }

    .nav-tabs .nav-link:focus, .nav-tabs .nav-link:hover {
    border-color: #e9ecef #e9ecef #ddd;
    }

    .nav-tabs .nav-link.disabled {
    color: #868e96;
    background-color: transparent;
    border-color: transparent;
    }

    .nav-tabs .nav-link.active,
    .nav-tabs .nav-item.show .nav-link {
    color: #495057;
    background-color: #fff;
    border-color: #ddd #ddd #fff;
    }

    .nav-tabs .dropdown-menu {
    margin-top: -1px;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    }

    .nav-pills .nav-link {
    border-radius: 0.25rem;
    }

    .nav-pills .nav-link.active,
    .show > .nav-pills .nav-link {
    color: #fff;
    background-color: #007bff;
    }

    .nav-fill .nav-item {
    -ms-flex: 1 1 auto;
        flex: 1 1 auto;
    text-align: center;
    }

    .nav-justified .nav-item {
    -ms-flex-preferred-size: 0;
        flex-basis: 0;
    -ms-flex-positive: 1;
        flex-grow: 1;
    text-align: center;
    }

    .tab-content > .tab-pane {
    display: none;
    }

    .tab-content > .active {
    display: block;
    }

    .navbar {
    position: relative;
    display: -ms-flexbox;
    display: flex;
    -ms-flex-wrap: wrap;
        flex-wrap: wrap;
    -ms-flex-align: center;
        align-items: center;
    -ms-flex-pack: justify;
        justify-content: space-between;
    padding: 0.5rem 1rem;
    }

    .navbar > .container,
    .navbar > .container-fluid {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-wrap: wrap;
        flex-wrap: wrap;
    -ms-flex-align: center;
        align-items: center;
    -ms-flex-pack: justify;
        justify-content: space-between;
    }

    .navbar-brand {
    display: inline-block;
    padding-top: 0.3125rem;
    padding-bottom: 0.3125rem;
    margin-right: 1rem;
    font-size: 1.25rem;
    line-height: inherit;
    white-space: nowrap;
    }

    .navbar-brand:focus, .navbar-brand:hover {
    text-decoration: none;
    }

    .navbar-nav {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-direction: column;
        flex-direction: column;
    padding-left: 0;
    margin-bottom: 0;
    list-style: none;
    }

    .navbar-nav .nav-link {
    padding-right: 0;
    padding-left: 0;
    }

    .navbar-nav .dropdown-menu {
    position: static;
    float: none;
    }

    .navbar-text {
    display: inline-block;
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
    }

    .navbar-collapse {
    -ms-flex-preferred-size: 100%;
        flex-basis: 100%;
    -ms-flex-align: center;
        align-items: center;
    }

    .navbar-toggler {
    padding: 0.25rem 0.75rem;
    font-size: 1.25rem;
    line-height: 1;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 0.25rem;
    }

    .navbar-toggler:focus, .navbar-toggler:hover {
    text-decoration: none;
    }

    .navbar-toggler-icon {
    display: inline-block;
    width: 1.5em;
    height: 1.5em;
    vertical-align: middle;
    content: "";
    background: no-repeat center center;
    background-size: 100% 100%;
    }

    @media (max-width: 575px) {
    .navbar-expand-sm > .container,
    .navbar-expand-sm > .container-fluid {
        padding-right: 0;
        padding-left: 0;
    }
    }

    @media (min-width: 576px) {
    .navbar-expand-sm {
        -ms-flex-direction: row;
            flex-direction: row;
        -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
        -ms-flex-pack: start;
            justify-content: flex-start;
    }
    .navbar-expand-sm .navbar-nav {
        -ms-flex-direction: row;
            flex-direction: row;
    }
    .navbar-expand-sm .navbar-nav .dropdown-menu {
        position: absolute;
    }
    .navbar-expand-sm .navbar-nav .dropdown-menu-right {
        right: 0;
        left: auto;
    }
    .navbar-expand-sm .navbar-nav .nav-link {
        padding-right: .5rem;
        padding-left: .5rem;
    }
    .navbar-expand-sm > .container,
    .navbar-expand-sm > .container-fluid {
        -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
    }
    .navbar-expand-sm .navbar-collapse {
        display: -ms-flexbox !important;
        display: flex !important;
    }
    .navbar-expand-sm .navbar-toggler {
        display: none;
    }
    }

    @media (max-width: 767px) {
    .navbar-expand-md > .container,
    .navbar-expand-md > .container-fluid {
        padding-right: 0;
        padding-left: 0;
    }
    }

    @media (min-width: 768px) {
    .navbar-expand-md {
        -ms-flex-direction: row;
            flex-direction: row;
        -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
        -ms-flex-pack: start;
            justify-content: flex-start;
    }
    .navbar-expand-md .navbar-nav {
        -ms-flex-direction: row;
            flex-direction: row;
    }
    .navbar-expand-md .navbar-nav .dropdown-menu {
        position: absolute;
    }
    .navbar-expand-md .navbar-nav .dropdown-menu-right {
        right: 0;
        left: auto;
    }
    .navbar-expand-md .navbar-nav .nav-link {
        padding-right: .5rem;
        padding-left: .5rem;
    }
    .navbar-expand-md > .container,
    .navbar-expand-md > .container-fluid {
        -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
    }
    .navbar-expand-md .navbar-collapse {
        display: -ms-flexbox !important;
        display: flex !important;
    }
    .navbar-expand-md .navbar-toggler {
        display: none;
    }
    }

    @media (max-width: 991px) {
    .navbar-expand-lg > .container,
    .navbar-expand-lg > .container-fluid {
        padding-right: 0;
        padding-left: 0;
    }
    }

    @media (min-width: 992px) {
    .navbar-expand-lg {
        -ms-flex-direction: row;
            flex-direction: row;
        -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
        -ms-flex-pack: start;
            justify-content: flex-start;
    }
    .navbar-expand-lg .navbar-nav {
        -ms-flex-direction: row;
            flex-direction: row;
    }
    .navbar-expand-lg .navbar-nav .dropdown-menu {
        position: absolute;
    }
    .navbar-expand-lg .navbar-nav .dropdown-menu-right {
        right: 0;
        left: auto;
    }
    .navbar-expand-lg .navbar-nav .nav-link {
        padding-right: .5rem;
        padding-left: .5rem;
    }
    .navbar-expand-lg > .container,
    .navbar-expand-lg > .container-fluid {
        -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
    }
    .navbar-expand-lg .navbar-collapse {
        display: -ms-flexbox !important;
        display: flex !important;
    }
    .navbar-expand-lg .navbar-toggler {
        display: none;
    }
    }

    @media (max-width: 1199px) {
    .navbar-expand-xl > .container,
    .navbar-expand-xl > .container-fluid {
        padding-right: 0;
        padding-left: 0;
    }
    }

    @media (min-width: 1200px) {
    .navbar-expand-xl {
        -ms-flex-direction: row;
            flex-direction: row;
        -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
        -ms-flex-pack: start;
            justify-content: flex-start;
    }
    .navbar-expand-xl .navbar-nav {
        -ms-flex-direction: row;
            flex-direction: row;
    }
    .navbar-expand-xl .navbar-nav .dropdown-menu {
        position: absolute;
    }
    .navbar-expand-xl .navbar-nav .dropdown-menu-right {
        right: 0;
        left: auto;
    }
    .navbar-expand-xl .navbar-nav .nav-link {
        padding-right: .5rem;
        padding-left: .5rem;
    }
    .navbar-expand-xl > .container,
    .navbar-expand-xl > .container-fluid {
        -ms-flex-wrap: nowrap;
            flex-wrap: nowrap;
    }
    .navbar-expand-xl .navbar-collapse {
        display: -ms-flexbox !important;
        display: flex !important;
    }
    .navbar-expand-xl .navbar-toggler {
        display: none;
    }
    }

    .navbar-expand {
    -ms-flex-direction: row;
        flex-direction: row;
    -ms-flex-wrap: nowrap;
        flex-wrap: nowrap;
    -ms-flex-pack: start;
        justify-content: flex-start;
    }

    .navbar-expand > .container,
    .navbar-expand > .container-fluid {
    padding-right: 0;
    padding-left: 0;
    }

    .navbar-expand .navbar-nav {
    -ms-flex-direction: row;
        flex-direction: row;
    }

    .navbar-expand .navbar-nav .dropdown-menu {
    position: absolute;
    }

    .navbar-expand .navbar-nav .dropdown-menu-right {
    right: 0;
    left: auto;
    }

    .navbar-expand .navbar-nav .nav-link {
    padding-right: .5rem;
    padding-left: .5rem;
    }

    .navbar-expand > .container,
    .navbar-expand > .container-fluid {
    -ms-flex-wrap: nowrap;
        flex-wrap: nowrap;
    }

    .navbar-expand .navbar-collapse {
    display: -ms-flexbox !important;
    display: flex !important;
    }

    .navbar-expand .navbar-toggler {
    display: none;
    }

    .navbar-light .navbar-brand {
    color: rgba(0, 0, 0, 0.9);
    }

    .navbar-light .navbar-brand:focus, .navbar-light .navbar-brand:hover {
    color: rgba(0, 0, 0, 0.9);
    }

    .navbar-light .navbar-nav .nav-link {
    color: rgba(0, 0, 0, 0.5);
    }

    .navbar-light .navbar-nav .nav-link:focus, .navbar-light .navbar-nav .nav-link:hover {
    color: rgba(0, 0, 0, 0.7);
    }

    .navbar-light .navbar-nav .nav-link.disabled {
    color: rgba(0, 0, 0, 0.3);
    }

    .navbar-light .navbar-nav .show > .nav-link,
    .navbar-light .navbar-nav .active > .nav-link,
    .navbar-light .navbar-nav .nav-link.show,
    .navbar-light .navbar-nav .nav-link.active {
    color: rgba(0, 0, 0, 0.9);
    }

    .navbar-light .navbar-toggler {
    color: rgba(0, 0, 0, 0.5);
    border-color: rgba(0, 0, 0, 0.1);
    }

    .navbar-light .navbar-toggler-icon {
    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg viewBox='0 0 30 30' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath stroke='rgba(0, 0, 0, 0.5)' stroke-width='2' stroke-linecap='round' stroke-miterlimit='10' d='M4 7h22M4 15h22M4 23h22'/%3E%3C/svg%3E");
    }

    .navbar-light .navbar-text {
    color: rgba(0, 0, 0, 0.5);
    }

    .navbar-dark .navbar-brand {
    color: white;
    }

    .navbar-dark .navbar-brand:focus, .navbar-dark .navbar-brand:hover {
    color: white;
    }

    .navbar-dark .navbar-nav .nav-link {
    color: rgba(255, 255, 255, 0.5);
    }

    .navbar-dark .navbar-nav .nav-link:focus, .navbar-dark .navbar-nav .nav-link:hover {
    color: rgba(255, 255, 255, 0.75);
    }

    .navbar-dark .navbar-nav .nav-link.disabled {
    color: rgba(255, 255, 255, 0.25);
    }

    .navbar-dark .navbar-nav .show > .nav-link,
    .navbar-dark .navbar-nav .active > .nav-link,
    .navbar-dark .navbar-nav .nav-link.show,
    .navbar-dark .navbar-nav .nav-link.active {
    color: white;
    }

    .navbar-dark .navbar-toggler {
    color: rgba(255, 255, 255, 0.5);
    border-color: rgba(255, 255, 255, 0.1);
    }

    .navbar-dark .navbar-toggler-icon {
    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg viewBox='0 0 30 30' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath stroke='rgba(255, 255, 255, 0.5)' stroke-width='2' stroke-linecap='round' stroke-miterlimit='10' d='M4 7h22M4 15h22M4 23h22'/%3E%3C/svg%3E");
    }

    .navbar-dark .navbar-text {
    color: rgba(255, 255, 255, 0.5);
    }

    .card {
    position: relative;
    display: -ms-flexbox;
    display: flex;
    -ms-flex-direction: column;
        flex-direction: column;
    min-width: 0;
    word-wrap: break-word;
    background-color: #fff;
    background-clip: border-box;
    border: 1px solid rgba(0, 0, 0, 0.125);
    border-radius: 0.25rem;
    }

    .card-body {
    -ms-flex: 1 1 auto;
        flex: 1 1 auto;
    padding: 1.25rem;
    }

    .card-title {
    margin-bottom: 0.75rem;
    }

    .card-subtitle {
    margin-top: -0.375rem;
    margin-bottom: 0;
    }

    .card-text:last-child {
    margin-bottom: 0;
    }

    .card-link:hover {
    text-decoration: none;
    }

    .card-link + .card-link {
    margin-left: 1.25rem;
    }

    .card > .list-group:first-child .list-group-item:first-child {
    border-top-left-radius: 0.25rem;
    border-top-right-radius: 0.25rem;
    }

    .card > .list-group:last-child .list-group-item:last-child {
    border-bottom-right-radius: 0.25rem;
    border-bottom-left-radius: 0.25rem;
    }

    .card-header {
    padding: 0.75rem 1.25rem;
    margin-bottom: 0;
    background-color: rgba(0, 0, 0, 0.03);
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
    }

    .card-header:first-child {
    border-radius: calc(0.25rem - 1px) calc(0.25rem - 1px) 0 0;
    }

    .card-footer {
    padding: 0.75rem 1.25rem;
    background-color: rgba(0, 0, 0, 0.03);
    border-top: 1px solid rgba(0, 0, 0, 0.125);
    }

    .card-footer:last-child {
    border-radius: 0 0 calc(0.25rem - 1px) calc(0.25rem - 1px);
    }

    .card-header-tabs {
    margin-right: -0.625rem;
    margin-bottom: -0.75rem;
    margin-left: -0.625rem;
    border-bottom: 0;
    }

    .card-header-pills {
    margin-right: -0.625rem;
    margin-left: -0.625rem;
    }

    .card-img-overlay {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    padding: 1.25rem;
    }

    .card-img {
    width: 100%;
    border-radius: calc(0.25rem - 1px);
    }

    .card-img-top {
    width: 100%;
    border-top-left-radius: calc(0.25rem - 1px);
    border-top-right-radius: calc(0.25rem - 1px);
    }

    .card-img-bottom {
    width: 100%;
    border-bottom-right-radius: calc(0.25rem - 1px);
    border-bottom-left-radius: calc(0.25rem - 1px);
    }

    @media (min-width: 576px) {
    .card-deck {
        display: -ms-flexbox;
        display: flex;
        -ms-flex-flow: row wrap;
            flex-flow: row wrap;
        margin-right: -15px;
        margin-left: -15px;
    }
    .card-deck .card {
        display: -ms-flexbox;
        display: flex;
        -ms-flex: 1 0 0%;
            flex: 1 0 0%;
        -ms-flex-direction: column;
            flex-direction: column;
        margin-right: 15px;
        margin-left: 15px;
    }
    }

    @media (min-width: 576px) {
    .card-group {
        display: -ms-flexbox;
        display: flex;
        -ms-flex-flow: row wrap;
            flex-flow: row wrap;
    }
    .card-group .card {
        -ms-flex: 1 0 0%;
            flex: 1 0 0%;
    }
    .card-group .card + .card {
        margin-left: 0;
        border-left: 0;
    }
    .card-group .card:first-child {
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
    }
    .card-group .card:first-child .card-img-top {
        border-top-right-radius: 0;
    }
    .card-group .card:first-child .card-img-bottom {
        border-bottom-right-radius: 0;
    }
    .card-group .card:last-child {
        border-top-left-radius: 0;
        border-bottom-left-radius: 0;
    }
    .card-group .card:last-child .card-img-top {
        border-top-left-radius: 0;
    }
    .card-group .card:last-child .card-img-bottom {
        border-bottom-left-radius: 0;
    }
    .card-group .card:not(:first-child):not(:last-child) {
        border-radius: 0;
    }
    .card-group .card:not(:first-child):not(:last-child) .card-img-top,
    .card-group .card:not(:first-child):not(:last-child) .card-img-bottom {
        border-radius: 0;
    }
    }

    .card-columns .card {
    margin-bottom: 0.75rem;
    }

    @media (min-width: 576px) {
    .card-columns {
        -webkit-column-count: 3;
                column-count: 3;
        -webkit-column-gap: 1.25rem;
                column-gap: 1.25rem;
    }
    .card-columns .card {
        display: inline-block;
        width: 100%;
    }
    }

    .breadcrumb {
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    list-style: none;
    background-color: #e9ecef;
    border-radius: 0.25rem;
    }

    .breadcrumb::after {
    display: block;
    clear: both;
    content: "";
    }

    .breadcrumb-item {
    float: left;
    }

    .breadcrumb-item + .breadcrumb-item::before {
    display: inline-block;
    padding-right: 0.5rem;
    padding-left: 0.5rem;
    color: #868e96;
    content: "/";
    }

    .breadcrumb-item + .breadcrumb-item:hover::before {
    text-decoration: underline;
    }

    .breadcrumb-item + .breadcrumb-item:hover::before {
    text-decoration: none;
    }

    .breadcrumb-item.active {
    color: #868e96;
    }

    .pagination {
    display: -ms-flexbox;
    display: flex;
    padding-left: 0;
    list-style: none;
    border-radius: 0.25rem;
    }

    .page-item:first-child .page-link {
    margin-left: 0;
    border-top-left-radius: 0.25rem;
    border-bottom-left-radius: 0.25rem;
    }

    .page-item:last-child .page-link {
    border-top-right-radius: 0.25rem;
    border-bottom-right-radius: 0.25rem;
    }

    .page-item.active .page-link {
    z-index: 2;
    color: #fff;
    background-color: #007bff;
    border-color: #007bff;
    }

    .page-item.disabled .page-link {
    color: #868e96;
    pointer-events: none;
    background-color: #fff;
    border-color: #ddd;
    }

    .page-link {
    position: relative;
    display: block;
    padding: 0.5rem 0.75rem;
    margin-left: -1px;
    line-height: 1.25;
    color: #007bff;
    background-color: #fff;
    border: 1px solid #ddd;
    }

    .page-link:focus, .page-link:hover {
    color: #0056b3;
    text-decoration: none;
    background-color: #e9ecef;
    border-color: #ddd;
    }

    .pagination-lg .page-link {
    padding: 0.75rem 1.5rem;
    font-size: 1.25rem;
    line-height: 1.5;
    }

    .pagination-lg .page-item:first-child .page-link {
    border-top-left-radius: 0.3rem;
    border-bottom-left-radius: 0.3rem;
    }

    .pagination-lg .page-item:last-child .page-link {
    border-top-right-radius: 0.3rem;
    border-bottom-right-radius: 0.3rem;
    }

    .pagination-sm .page-link {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    line-height: 1.5;
    }

    .pagination-sm .page-item:first-child .page-link {
    border-top-left-radius: 0.2rem;
    border-bottom-left-radius: 0.2rem;
    }

    .pagination-sm .page-item:last-child .page-link {
    border-top-right-radius: 0.2rem;
    border-bottom-right-radius: 0.2rem;
    }

    .badge {
    display: inline-block;
    padding: 0.25em 0.4em;
    font-size: 75%;
    font-weight: bold;
    line-height: 1;
    color: #fff;
    text-align: center;
    white-space: nowrap;
    vertical-align: baseline;
    border-radius: 0.25rem;
    }

    .badge:empty {
    display: none;
    }

    .btn .badge {
    position: relative;
    top: -1px;
    }

    .badge-pill {
    padding-right: 0.6em;
    padding-left: 0.6em;
    border-radius: 10rem;
    }

    .badge-primary {
    color: #fff;
    background-color: #007bff;
    }

    .badge-primary[href]:focus, .badge-primary[href]:hover {
    color: #fff;
    text-decoration: none;
    background-color: #0062cc;
    }

    .badge-secondary {
    color: #fff;
    background-color: #868e96;
    }

    .badge-secondary[href]:focus, .badge-secondary[href]:hover {
    color: #fff;
    text-decoration: none;
    background-color: #6c757d;
    }

    .badge-success {
    color: #fff;
    background-color: #28a745;
    }

    .badge-success[href]:focus, .badge-success[href]:hover {
    color: #fff;
    text-decoration: none;
    background-color: #1e7e34;
    }

    .badge-info {
    color: #fff;
    background-color: #17a2b8;
    }

    .badge-info[href]:focus, .badge-info[href]:hover {
    color: #fff;
    text-decoration: none;
    background-color: #117a8b;
    }

    .badge-warning {
    color: #111;
    background-color: #ffc107;
    }

    .badge-warning[href]:focus, .badge-warning[href]:hover {
    color: #111;
    text-decoration: none;
    background-color: #d39e00;
    }

    .badge-danger {
    color: #fff;
    background-color: #dc3545;
    }

    .badge-danger[href]:focus, .badge-danger[href]:hover {
    color: #fff;
    text-decoration: none;
    background-color: #bd2130;
    }

    .badge-light {
    color: #111;
    background-color: #f8f9fa;
    }

    .badge-light[href]:focus, .badge-light[href]:hover {
    color: #111;
    text-decoration: none;
    background-color: #dae0e5;
    }

    .badge-dark {
    color: #fff;
    background-color: #343a40;
    }

    .badge-dark[href]:focus, .badge-dark[href]:hover {
    color: #fff;
    text-decoration: none;
    background-color: #1d2124;
    }

    .jumbotron {
    padding: 2rem 1rem;
    margin-bottom: 2rem;
    background-color: #e9ecef;
    border-radius: 0.3rem;
    }

    @media (min-width: 576px) {
    .jumbotron {
        padding: 4rem 2rem;
    }
    }

    .jumbotron-fluid {
    padding-right: 0;
    padding-left: 0;
    border-radius: 0;
    }

    .alert {
    padding: 0.75rem 1.25rem;
    margin-bottom: 1rem;
    border: 1px solid transparent;
    border-radius: 0.25rem;
    }

    .alert-heading {
    color: inherit;
    }

    .alert-link {
    font-weight: bold;
    }

    .alert-dismissible .close {
    position: relative;
    top: -0.75rem;
    right: -1.25rem;
    padding: 0.75rem 1.25rem;
    color: inherit;
    }

    .alert-primary {
    color: #004085;
    background-color: #cce5ff;
    border-color: #b8daff;
    }

    .alert-primary hr {
    border-top-color: #9fcdff;
    }

    .alert-primary .alert-link {
    color: #002752;
    }

    .alert-secondary {
    color: #464a4e;
    background-color: #e7e8ea;
    border-color: #dddfe2;
    }

    .alert-secondary hr {
    border-top-color: #cfd2d6;
    }

    .alert-secondary .alert-link {
    color: #2e3133;
    }

    .alert-success {
    color: #155724;
    background-color: #d4edda;
    border-color: #c3e6cb;
    }

    .alert-success hr {
    border-top-color: #b1dfbb;
    }

    .alert-success .alert-link {
    color: #0b2e13;
    }

    .alert-info {
    color: #0c5460;
    background-color: #d1ecf1;
    border-color: #bee5eb;
    }

    .alert-info hr {
    border-top-color: #abdde5;
    }

    .alert-info .alert-link {
    color: #062c33;
    }

    .alert-warning {
    color: #856404;
    background-color: #fff3cd;
    border-color: #ffeeba;
    }

    .alert-warning hr {
    border-top-color: #ffe8a1;
    }

    .alert-warning .alert-link {
    color: #533f03;
    }

    .alert-danger {
    color: #721c24;
    background-color: #f8d7da;
    border-color: #f5c6cb;
    }

    .alert-danger hr {
    border-top-color: #f1b0b7;
    }

    .alert-danger .alert-link {
    color: #491217;
    }

    .alert-light {
    color: #818182;
    background-color: #fefefe;
    border-color: #fdfdfe;
    }

    .alert-light hr {
    border-top-color: #ececf6;
    }

    .alert-light .alert-link {
    color: #686868;
    }

    .alert-dark {
    color: #1b1e21;
    background-color: #d6d8d9;
    border-color: #c6c8ca;
    }

    .alert-dark hr {
    border-top-color: #b9bbbe;
    }

    .alert-dark .alert-link {
    color: #040505;
    }

    @-webkit-keyframes progress-bar-stripes {
    from {
        background-position: 1rem 0;
    }
    to {
        background-position: 0 0;
    }
    }

    @keyframes progress-bar-stripes {
    from {
        background-position: 1rem 0;
    }
    to {
        background-position: 0 0;
    }
    }

    .progress {
    display: -ms-flexbox;
    display: flex;
    overflow: hidden;
    font-size: 0.75rem;
    line-height: 1rem;
    text-align: center;
    background-color: #e9ecef;
    border-radius: 0.25rem;
    }

    .progress-bar {
    height: 1rem;
    line-height: 1rem;
    color: #fff;
    background-color: #007bff;
    transition: width 0.6s ease;
    }

    .progress-bar-striped {
    background-image: linear-gradient(45deg, rgba(255, 255, 255, 0.15) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 255, 255, 0.15) 75%, transparent 75%, transparent);
    background-size: 1rem 1rem;
    }

    .progress-bar-animated {
    -webkit-animation: progress-bar-stripes 1s linear infinite;
            animation: progress-bar-stripes 1s linear infinite;
    }

    .media {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-align: start;
        align-items: flex-start;
    }

    .media-body {
    -ms-flex: 1;
        flex: 1;
    }

    .list-group {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-direction: column;
        flex-direction: column;
    padding-left: 0;
    margin-bottom: 0;
    }

    .list-group-item-action {
    width: 100%;
    color: #495057;
    text-align: inherit;
    }

    .list-group-item-action:focus, .list-group-item-action:hover {
    color: #495057;
    text-decoration: none;
    background-color: #f8f9fa;
    }

    .list-group-item-action:active {
    color: #212529;
    background-color: #e9ecef;
    }

    .list-group-item {
    position: relative;
    display: block;
    padding: 0.75rem 1.25rem;
    margin-bottom: -1px;
    background-color: #fff;
    border: 1px solid rgba(0, 0, 0, 0.125);
    }

    .list-group-item:first-child {
    border-top-left-radius: 0.25rem;
    border-top-right-radius: 0.25rem;
    }

    .list-group-item:last-child {
    margin-bottom: 0;
    border-bottom-right-radius: 0.25rem;
    border-bottom-left-radius: 0.25rem;
    }

    .list-group-item:focus, .list-group-item:hover {
    text-decoration: none;
    }

    .list-group-item.disabled, .list-group-item:disabled {
    color: #868e96;
    background-color: #fff;
    }

    .list-group-item.active {
    z-index: 2;
    color: #fff;
    background-color: #007bff;
    border-color: #007bff;
    }

    .list-group-flush .list-group-item {
    border-right: 0;
    border-left: 0;
    border-radius: 0;
    }

    .list-group-flush:first-child .list-group-item:first-child {
    border-top: 0;
    }

    .list-group-flush:last-child .list-group-item:last-child {
    border-bottom: 0;
    }

    .list-group-item-primary {
    color: #004085;
    background-color: #b8daff;
    }

    a.list-group-item-primary,
    button.list-group-item-primary {
    color: #004085;
    }

    a.list-group-item-primary:focus, a.list-group-item-primary:hover,
    button.list-group-item-primary:focus,
    button.list-group-item-primary:hover {
    color: #004085;
    background-color: #9fcdff;
    }

    a.list-group-item-primary.active,
    button.list-group-item-primary.active {
    color: #fff;
    background-color: #004085;
    border-color: #004085;
    }

    .list-group-item-secondary {
    color: #464a4e;
    background-color: #dddfe2;
    }

    a.list-group-item-secondary,
    button.list-group-item-secondary {
    color: #464a4e;
    }

    a.list-group-item-secondary:focus, a.list-group-item-secondary:hover,
    button.list-group-item-secondary:focus,
    button.list-group-item-secondary:hover {
    color: #464a4e;
    background-color: #cfd2d6;
    }

    a.list-group-item-secondary.active,
    button.list-group-item-secondary.active {
    color: #fff;
    background-color: #464a4e;
    border-color: #464a4e;
    }

    .list-group-item-success {
    color: #155724;
    background-color: #c3e6cb;
    }

    a.list-group-item-success,
    button.list-group-item-success {
    color: #155724;
    }

    a.list-group-item-success:focus, a.list-group-item-success:hover,
    button.list-group-item-success:focus,
    button.list-group-item-success:hover {
    color: #155724;
    background-color: #b1dfbb;
    }

    a.list-group-item-success.active,
    button.list-group-item-success.active {
    color: #fff;
    background-color: #155724;
    border-color: #155724;
    }

    .list-group-item-info {
    color: #0c5460;
    background-color: #bee5eb;
    }

    a.list-group-item-info,
    button.list-group-item-info {
    color: #0c5460;
    }

    a.list-group-item-info:focus, a.list-group-item-info:hover,
    button.list-group-item-info:focus,
    button.list-group-item-info:hover {
    color: #0c5460;
    background-color: #abdde5;
    }

    a.list-group-item-info.active,
    button.list-group-item-info.active {
    color: #fff;
    background-color: #0c5460;
    border-color: #0c5460;
    }

    .list-group-item-warning {
    color: #856404;
    background-color: #ffeeba;
    }

    a.list-group-item-warning,
    button.list-group-item-warning {
    color: #856404;
    }

    a.list-group-item-warning:focus, a.list-group-item-warning:hover,
    button.list-group-item-warning:focus,
    button.list-group-item-warning:hover {
    color: #856404;
    background-color: #ffe8a1;
    }

    a.list-group-item-warning.active,
    button.list-group-item-warning.active {
    color: #fff;
    background-color: #856404;
    border-color: #856404;
    }

    .list-group-item-danger {
    color: #721c24;
    background-color: #f5c6cb;
    }

    a.list-group-item-danger,
    button.list-group-item-danger {
    color: #721c24;
    }

    a.list-group-item-danger:focus, a.list-group-item-danger:hover,
    button.list-group-item-danger:focus,
    button.list-group-item-danger:hover {
    color: #721c24;
    background-color: #f1b0b7;
    }

    a.list-group-item-danger.active,
    button.list-group-item-danger.active {
    color: #fff;
    background-color: #721c24;
    border-color: #721c24;
    }

    .list-group-item-light {
    color: #818182;
    background-color: #fdfdfe;
    }

    a.list-group-item-light,
    button.list-group-item-light {
    color: #818182;
    }

    a.list-group-item-light:focus, a.list-group-item-light:hover,
    button.list-group-item-light:focus,
    button.list-group-item-light:hover {
    color: #818182;
    background-color: #ececf6;
    }

    a.list-group-item-light.active,
    button.list-group-item-light.active {
    color: #fff;
    background-color: #818182;
    border-color: #818182;
    }

    .list-group-item-dark {
    color: #1b1e21;
    background-color: #c6c8ca;
    }

    a.list-group-item-dark,
    button.list-group-item-dark {
    color: #1b1e21;
    }

    a.list-group-item-dark:focus, a.list-group-item-dark:hover,
    button.list-group-item-dark:focus,
    button.list-group-item-dark:hover {
    color: #1b1e21;
    background-color: #b9bbbe;
    }

    a.list-group-item-dark.active,
    button.list-group-item-dark.active {
    color: #fff;
    background-color: #1b1e21;
    border-color: #1b1e21;
    }

    .close {
    float: right;
    font-size: 1.5rem;
    font-weight: bold;
    line-height: 1;
    color: #000;
    text-shadow: 0 1px 0 #fff;
    opacity: .5;
    }

    .close:focus, .close:hover {
    color: #000;
    text-decoration: none;
    opacity: .75;
    }

    button.close {
    padding: 0;
    background: transparent;
    border: 0;
    -webkit-appearance: none;
    }

    .modal-open {
    overflow: hidden;
    }

    .modal {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 1050;
    display: none;
    overflow: hidden;
    outline: 0;
    }

    .modal.fade .modal-dialog {
    transition: -webkit-transform 0.3s ease-out;
    transition: transform 0.3s ease-out;
    transition: transform 0.3s ease-out, -webkit-transform 0.3s ease-out;
    -webkit-transform: translate(0, -25%);
            transform: translate(0, -25%);
    }

    .modal.show .modal-dialog {
    -webkit-transform: translate(0, 0);
            transform: translate(0, 0);
    }

    .modal-open .modal {
    overflow-x: hidden;
    overflow-y: auto;
    }

    .modal-dialog {
    position: relative;
    width: auto;
    margin: 10px;
    }

    .modal-content {
    position: relative;
    display: -ms-flexbox;
    display: flex;
    -ms-flex-direction: column;
        flex-direction: column;
    background-color: #fff;
    background-clip: padding-box;
    border: 1px solid rgba(0, 0, 0, 0.2);
    border-radius: 0.3rem;
    outline: 0;
    }

    .modal-backdrop {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 1040;
    background-color: #000;
    }

    .modal-backdrop.fade {
    opacity: 0;
    }

    .modal-backdrop.show {
    opacity: 0.5;
    }

    .modal-header {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-align: center;
        align-items: center;
    -ms-flex-pack: justify;
        justify-content: space-between;
    padding: 15px;
    border-bottom: 1px solid #e9ecef;
    }

    .modal-title {
    margin-bottom: 0;
    line-height: 1.5;
    }

    .modal-body {
    position: relative;
    -ms-flex: 1 1 auto;
        flex: 1 1 auto;
    padding: 15px;
    }

    .modal-footer {
    display: -ms-flexbox;
    display: flex;
    -ms-flex-align: center;
        align-items: center;
    -ms-flex-pack: end;
        justify-content: flex-end;
    padding: 15px;
    border-top: 1px solid #e9ecef;
    }

    .modal-footer > :not(:first-child) {
    margin-left: .25rem;
    }

    .modal-footer > :not(:last-child) {
    margin-right: .25rem;
    }

    .modal-scrollbar-measure {
    position: absolute;
    top: -9999px;
    width: 50px;
    height: 50px;
    overflow: scroll;
    }

    @media (min-width: 576px) {
    .modal-dialog {
        max-width: 500px;
        margin: 30px auto;
    }
    .modal-sm {
        max-width: 300px;
    }
    }

    @media (min-width: 992px) {
    .modal-lg {
        max-width: 800px;
    }
    }

    .tooltip {
    position: absolute;
    z-index: 1070;
    display: block;
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-style: normal;
    font-weight: normal;
    line-height: 1.5;
    text-align: left;
    text-align: start;
    text-decoration: none;
    text-shadow: none;
    text-transform: none;
    letter-spacing: normal;
    word-break: normal;
    word-spacing: normal;
    white-space: normal;
    line-break: auto;
    font-size: 0.875rem;
    word-wrap: break-word;
    opacity: 0;
    }

    .tooltip.show {
    opacity: 0.9;
    }

    .tooltip .arrow {
    position: absolute;
    display: block;
    width: 5px;
    height: 5px;
    }

    .tooltip.bs-tooltip-top, .tooltip.bs-tooltip-auto[x-placement^="top"] {
    padding: 5px 0;
    }

    .tooltip.bs-tooltip-top .arrow, .tooltip.bs-tooltip-auto[x-placement^="top"] .arrow {
    bottom: 0;
    }

    .tooltip.bs-tooltip-top .arrow::before, .tooltip.bs-tooltip-auto[x-placement^="top"] .arrow::before {
    margin-left: -3px;
    content: "";
    border-width: 5px 5px 0;
    border-top-color: #000;
    }

    .tooltip.bs-tooltip-right, .tooltip.bs-tooltip-auto[x-placement^="right"] {
    padding: 0 5px;
    }

    .tooltip.bs-tooltip-right .arrow, .tooltip.bs-tooltip-auto[x-placement^="right"] .arrow {
    left: 0;
    }

    .tooltip.bs-tooltip-right .arrow::before, .tooltip.bs-tooltip-auto[x-placement^="right"] .arrow::before {
    margin-top: -3px;
    content: "";
    border-width: 5px 5px 5px 0;
    border-right-color: #000;
    }

    .tooltip.bs-tooltip-bottom, .tooltip.bs-tooltip-auto[x-placement^="bottom"] {
    padding: 5px 0;
    }

    .tooltip.bs-tooltip-bottom .arrow, .tooltip.bs-tooltip-auto[x-placement^="bottom"] .arrow {
    top: 0;
    }

    .tooltip.bs-tooltip-bottom .arrow::before, .tooltip.bs-tooltip-auto[x-placement^="bottom"] .arrow::before {
    margin-left: -3px;
    content: "";
    border-width: 0 5px 5px;
    border-bottom-color: #000;
    }

    .tooltip.bs-tooltip-left, .tooltip.bs-tooltip-auto[x-placement^="left"] {
    padding: 0 5px;
    }

    .tooltip.bs-tooltip-left .arrow, .tooltip.bs-tooltip-auto[x-placement^="left"] .arrow {
    right: 0;
    }

    .tooltip.bs-tooltip-left .arrow::before, .tooltip.bs-tooltip-auto[x-placement^="left"] .arrow::before {
    right: 0;
    margin-top: -3px;
    content: "";
    border-width: 5px 0 5px 5px;
    border-left-color: #000;
    }

    .tooltip .arrow::before {
    position: absolute;
    border-color: transparent;
    border-style: solid;
    }

    .tooltip-inner {
    max-width: 200px;
    padding: 3px 8px;
    color: #fff;
    text-align: center;
    background-color: #000;
    border-radius: 0.25rem;
    }

    .popover {
    position: absolute;
    top: 0;
    left: 0;
    z-index: 1060;
    display: block;
    max-width: 276px;
    padding: 1px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-style: normal;
    font-weight: normal;
    line-height: 1.5;
    text-align: left;
    text-align: start;
    text-decoration: none;
    text-shadow: none;
    text-transform: none;
    letter-spacing: normal;
    word-break: normal;
    word-spacing: normal;
    white-space: normal;
    line-break: auto;
    font-size: 0.875rem;
    word-wrap: break-word;
    background-color: #fff;
    background-clip: padding-box;
    border: 1px solid rgba(0, 0, 0, 0.2);
    border-radius: 0.3rem;
    }

    .popover .arrow {
    position: absolute;
    display: block;
    width: 10px;
    height: 5px;
    }

    .popover .arrow::before,
    .popover .arrow::after {
    position: absolute;
    display: block;
    border-color: transparent;
    border-style: solid;
    }

    .popover .arrow::before {
    content: "";
    border-width: 11px;
    }

    .popover .arrow::after {
    content: "";
    border-width: 11px;
    }

    .popover.bs-popover-top, .popover.bs-popover-auto[x-placement^="top"] {
    margin-bottom: 10px;
    }

    .popover.bs-popover-top .arrow, .popover.bs-popover-auto[x-placement^="top"] .arrow {
    bottom: 0;
    }

    .popover.bs-popover-top .arrow::before, .popover.bs-popover-auto[x-placement^="top"] .arrow::before,
    .popover.bs-popover-top .arrow::after, .popover.bs-popover-auto[x-placement^="top"] .arrow::after {
    border-bottom-width: 0;
    }

    .popover.bs-popover-top .arrow::before, .popover.bs-popover-auto[x-placement^="top"] .arrow::before {
    bottom: -11px;
    margin-left: -6px;
    border-top-color: rgba(0, 0, 0, 0.25);
    }

    .popover.bs-popover-top .arrow::after, .popover.bs-popover-auto[x-placement^="top"] .arrow::after {
    bottom: -10px;
    margin-left: -6px;
    border-top-color: #fff;
    }

    .popover.bs-popover-right, .popover.bs-popover-auto[x-placement^="right"] {
    margin-left: 10px;
    }

    .popover.bs-popover-right .arrow, .popover.bs-popover-auto[x-placement^="right"] .arrow {
    left: 0;
    }

    .popover.bs-popover-right .arrow::before, .popover.bs-popover-auto[x-placement^="right"] .arrow::before,
    .popover.bs-popover-right .arrow::after, .popover.bs-popover-auto[x-placement^="right"] .arrow::after {
    margin-top: -8px;
    border-left-width: 0;
    }

    .popover.bs-popover-right .arrow::before, .popover.bs-popover-auto[x-placement^="right"] .arrow::before {
    left: -11px;
    border-right-color: rgba(0, 0, 0, 0.25);
    }

    .popover.bs-popover-right .arrow::after, .popover.bs-popover-auto[x-placement^="right"] .arrow::after {
    left: -10px;
    border-right-color: #fff;
    }

    .popover.bs-popover-bottom, .popover.bs-popover-auto[x-placement^="bottom"] {
    margin-top: 10px;
    }

    .popover.bs-popover-bottom .arrow, .popover.bs-popover-auto[x-placement^="bottom"] .arrow {
    top: 0;
    }

    .popover.bs-popover-bottom .arrow::before, .popover.bs-popover-auto[x-placement^="bottom"] .arrow::before,
    .popover.bs-popover-bottom .arrow::after, .popover.bs-popover-auto[x-placement^="bottom"] .arrow::after {
    margin-left: -7px;
    border-top-width: 0;
    }

    .popover.bs-popover-bottom .arrow::before, .popover.bs-popover-auto[x-placement^="bottom"] .arrow::before {
    top: -11px;
    border-bottom-color: rgba(0, 0, 0, 0.25);
    }

    .popover.bs-popover-bottom .arrow::after, .popover.bs-popover-auto[x-placement^="bottom"] .arrow::after {
    top: -10px;
    border-bottom-color: #fff;
    }

    .popover.bs-popover-bottom .popover-header::before, .popover.bs-popover-auto[x-placement^="bottom"] .popover-header::before {
    position: absolute;
    top: 0;
    left: 50%;
    display: block;
    width: 20px;
    margin-left: -10px;
    content: "";
    border-bottom: 1px solid #f7f7f7;
    }

    .popover.bs-popover-left, .popover.bs-popover-auto[x-placement^="left"] {
    margin-right: 10px;
    }

    .popover.bs-popover-left .arrow, .popover.bs-popover-auto[x-placement^="left"] .arrow {
    right: 0;
    }

    .popover.bs-popover-left .arrow::before, .popover.bs-popover-auto[x-placement^="left"] .arrow::before,
    .popover.bs-popover-left .arrow::after, .popover.bs-popover-auto[x-placement^="left"] .arrow::after {
    margin-top: -8px;
    border-right-width: 0;
    }

    .popover.bs-popover-left .arrow::before, .popover.bs-popover-auto[x-placement^="left"] .arrow::before {
    right: -11px;
    border-left-color: rgba(0, 0, 0, 0.25);
    }

    .popover.bs-popover-left .arrow::after, .popover.bs-popover-auto[x-placement^="left"] .arrow::after {
    right: -10px;
    border-left-color: #fff;
    }

    .popover-header {
    padding: 8px 14px;
    margin-bottom: 0;
    font-size: 1rem;
    color: inherit;
    background-color: #f7f7f7;
    border-bottom: 1px solid #ebebeb;
    border-top-left-radius: calc(0.3rem - 1px);
    border-top-right-radius: calc(0.3rem - 1px);
    }

    .popover-header:empty {
    display: none;
    }

    .popover-body {
    padding: 9px 14px;
    color: #212529;
    }

    .carousel {
    position: relative;
    }

    .carousel-inner {
    position: relative;
    width: 100%;
    overflow: hidden;
    }

    .carousel-item {
    position: relative;
    display: none;
    -ms-flex-align: center;
        align-items: center;
    width: 100%;
    transition: -webkit-transform 0.6s ease;
    transition: transform 0.6s ease;
    transition: transform 0.6s ease, -webkit-transform 0.6s ease;
    -webkit-backface-visibility: hidden;
            backface-visibility: hidden;
    -webkit-perspective: 1000px;
            perspective: 1000px;
    }

    .carousel-item.active,
    .carousel-item-next,
    .carousel-item-prev {
    display: block;
    }

    .carousel-item-next,
    .carousel-item-prev {
    position: absolute;
    top: 0;
    }

    .carousel-item-next.carousel-item-left,
    .carousel-item-prev.carousel-item-right {
    -webkit-transform: translateX(0);
            transform: translateX(0);
    }

    @supports ((-webkit-transform-style: preserve-3d) or (transform-style: preserve-3d)) {
    .carousel-item-next.carousel-item-left,
    .carousel-item-prev.carousel-item-right {
        -webkit-transform: translate3d(0, 0, 0);
                transform: translate3d(0, 0, 0);
    }
    }

    .carousel-item-next,
    .active.carousel-item-right {
    -webkit-transform: translateX(100%);
            transform: translateX(100%);
    }

    @supports ((-webkit-transform-style: preserve-3d) or (transform-style: preserve-3d)) {
    .carousel-item-next,
    .active.carousel-item-right {
        -webkit-transform: translate3d(100%, 0, 0);
                transform: translate3d(100%, 0, 0);
    }
    }

    .carousel-item-prev,
    .active.carousel-item-left {
    -webkit-transform: translateX(-100%);
            transform: translateX(-100%);
    }

    @supports ((-webkit-transform-style: preserve-3d) or (transform-style: preserve-3d)) {
    .carousel-item-prev,
    .active.carousel-item-left {
        -webkit-transform: translate3d(-100%, 0, 0);
                transform: translate3d(-100%, 0, 0);
    }
    }

    .carousel-control-prev,
    .carousel-control-next {
    position: absolute;
    top: 0;
    bottom: 0;
    display: -ms-flexbox;
    display: flex;
    -ms-flex-align: center;
        align-items: center;
    -ms-flex-pack: center;
        justify-content: center;
    width: 15%;
    color: #fff;
    text-align: center;
    opacity: 0.5;
    }

    .carousel-control-prev:focus, .carousel-control-prev:hover,
    .carousel-control-next:focus,
    .carousel-control-next:hover {
    color: #fff;
    text-decoration: none;
    outline: 0;
    opacity: .9;
    }

    .carousel-control-prev {
    left: 0;
    }

    .carousel-control-next {
    right: 0;
    }

    .carousel-control-prev-icon,
    .carousel-control-next-icon {
    display: inline-block;
    width: 20px;
    height: 20px;
    background: transparent no-repeat center center;
    background-size: 100% 100%;
    }

    .carousel-control-prev-icon {
    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23fff' viewBox='0 0 8 8'%3E%3Cpath d='M4 0l-4 4 4 4 1.5-1.5-2.5-2.5 2.5-2.5-1.5-1.5z'/%3E%3C/svg%3E");
    }

    .carousel-control-next-icon {
    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23fff' viewBox='0 0 8 8'%3E%3Cpath d='M1.5 0l-1.5 1.5 2.5 2.5-2.5 2.5 1.5 1.5 4-4-4-4z'/%3E%3C/svg%3E");
    }

    .carousel-indicators {
    position: absolute;
    right: 0;
    bottom: 10px;
    left: 0;
    z-index: 15;
    display: -ms-flexbox;
    display: flex;
    -ms-flex-pack: center;
        justify-content: center;
    padding-left: 0;
    margin-right: 15%;
    margin-left: 15%;
    list-style: none;
    }

    .carousel-indicators li {
    position: relative;
    -ms-flex: 0 1 auto;
        flex: 0 1 auto;
    width: 30px;
    height: 3px;
    margin-right: 3px;
    margin-left: 3px;
    text-indent: -999px;
    background-color: rgba(255, 255, 255, 0.5);
    }

    .carousel-indicators li::before {
    position: absolute;
    top: -10px;
    left: 0;
    display: inline-block;
    width: 100%;
    height: 10px;
    content: "";
    }

    .carousel-indicators li::after {
    position: absolute;
    bottom: -10px;
    left: 0;
    display: inline-block;
    width: 100%;
    height: 10px;
    content: "";
    }

    .carousel-indicators .active {
    background-color: #fff;
    }

    .carousel-caption {
    position: absolute;
    right: 15%;
    bottom: 20px;
    left: 15%;
    z-index: 10;
    padding-top: 20px;
    padding-bottom: 20px;
    color: #fff;
    text-align: center;
    }

    .align-baseline {
    vertical-align: baseline !important;
    }

    .align-top {
    vertical-align: top !important;
    }

    .align-middle {
    vertical-align: middle !important;
    }

    .align-bottom {
    vertical-align: bottom !important;
    }

    .align-text-bottom {
    vertical-align: text-bottom !important;
    }

    .align-text-top {
    vertical-align: text-top !important;
    }

    .bg-primary {
    background-color: #007bff !important;
    }

    a.bg-primary:focus, a.bg-primary:hover {
    background-color: #0062cc !important;
    }

    .bg-secondary {
    background-color: #868e96 !important;
    }

    a.bg-secondary:focus, a.bg-secondary:hover {
    background-color: #6c757d !important;
    }

    .bg-success {
    background-color: #28a745 !important;
    }

    a.bg-success:focus, a.bg-success:hover {
    background-color: #1e7e34 !important;
    }

    .bg-info {
    background-color: #17a2b8 !important;
    }

    a.bg-info:focus, a.bg-info:hover {
    background-color: #117a8b !important;
    }

    .bg-warning {
    background-color: #ffc107 !important;
    }

    a.bg-warning:focus, a.bg-warning:hover {
    background-color: #d39e00 !important;
    }

    .bg-danger {
    background-color: #dc3545 !important;
    }

    a.bg-danger:focus, a.bg-danger:hover {
    background-color: #bd2130 !important;
    }

    .bg-light {
    background-color: #f8f9fa !important;
    }

    a.bg-light:focus, a.bg-light:hover {
    background-color: #dae0e5 !important;
    }

    .bg-dark {
    background-color: #343a40 !important;
    }

    a.bg-dark:focus, a.bg-dark:hover {
    background-color: #1d2124 !important;
    }

    .bg-white {
    background-color: #fff !important;
    }

    .bg-transparent {
    background-color: transparent !important;
    }

    .border {
    border: 1px solid #e9ecef !important;
    }

    .border-0 {
    border: 0 !important;
    }

    .border-top-0 {
    border-top: 0 !important;
    }

    .border-right-0 {
    border-right: 0 !important;
    }

    .border-bottom-0 {
    border-bottom: 0 !important;
    }

    .border-left-0 {
    border-left: 0 !important;
    }

    .border-primary {
    border-color: #007bff !important;
    }

    .border-secondary {
    border-color: #868e96 !important;
    }

    .border-success {
    border-color: #28a745 !important;
    }

    .border-info {
    border-color: #17a2b8 !important;
    }

    .border-warning {
    border-color: #ffc107 !important;
    }

    .border-danger {
    border-color: #dc3545 !important;
    }

    .border-light {
    border-color: #f8f9fa !important;
    }

    .border-dark {
    border-color: #343a40 !important;
    }

    .border-white {
    border-color: #fff !important;
    }

    .rounded {
    border-radius: 0.25rem !important;
    }

    .rounded-top {
    border-top-left-radius: 0.25rem !important;
    border-top-right-radius: 0.25rem !important;
    }

    .rounded-right {
    border-top-right-radius: 0.25rem !important;
    border-bottom-right-radius: 0.25rem !important;
    }

    .rounded-bottom {
    border-bottom-right-radius: 0.25rem !important;
    border-bottom-left-radius: 0.25rem !important;
    }

    .rounded-left {
    border-top-left-radius: 0.25rem !important;
    border-bottom-left-radius: 0.25rem !important;
    }

    .rounded-circle {
    border-radius: 50%;
    }

    .rounded-0 {
    border-radius: 0;
    }

    .clearfix::after {
    display: block;
    clear: both;
    content: "";
    }

    .d-none {
    display: none !important;
    }

    .d-inline {
    display: inline !important;
    }

    .d-inline-block {
    display: inline-block !important;
    }

    .d-block {
    display: block !important;
    }

    .d-table {
    display: table !important;
    }

    .d-table-cell {
    display: table-cell !important;
    }

    .d-flex {
    display: -ms-flexbox !important;
    display: flex !important;
    }

    .d-inline-flex {
    display: -ms-inline-flexbox !important;
    display: inline-flex !important;
    }

    @media (min-width: 576px) {
    .d-sm-none {
        display: none !important;
    }
    .d-sm-inline {
        display: inline !important;
    }
    .d-sm-inline-block {
        display: inline-block !important;
    }
    .d-sm-block {
        display: block !important;
    }
    .d-sm-table {
        display: table !important;
    }
    .d-sm-table-cell {
        display: table-cell !important;
    }
    .d-sm-flex {
        display: -ms-flexbox !important;
        display: flex !important;
    }
    .d-sm-inline-flex {
        display: -ms-inline-flexbox !important;
        display: inline-flex !important;
    }
    }

    @media (min-width: 768px) {
    .d-md-none {
        display: none !important;
    }
    .d-md-inline {
        display: inline !important;
    }
    .d-md-inline-block {
        display: inline-block !important;
    }
    .d-md-block {
        display: block !important;
    }
    .d-md-table {
        display: table !important;
    }
    .d-md-table-cell {
        display: table-cell !important;
    }
    .d-md-flex {
        display: -ms-flexbox !important;
        display: flex !important;
    }
    .d-md-inline-flex {
        display: -ms-inline-flexbox !important;
        display: inline-flex !important;
    }
    }

    @media (min-width: 992px) {
    .d-lg-none {
        display: none !important;
    }
    .d-lg-inline {
        display: inline !important;
    }
    .d-lg-inline-block {
        display: inline-block !important;
    }
    .d-lg-block {
        display: block !important;
    }
    .d-lg-table {
        display: table !important;
    }
    .d-lg-table-cell {
        display: table-cell !important;
    }
    .d-lg-flex {
        display: -ms-flexbox !important;
        display: flex !important;
    }
    .d-lg-inline-flex {
        display: -ms-inline-flexbox !important;
        display: inline-flex !important;
    }
    }

    @media (min-width: 1200px) {
    .d-xl-none {
        display: none !important;
    }
    .d-xl-inline {
        display: inline !important;
    }
    .d-xl-inline-block {
        display: inline-block !important;
    }
    .d-xl-block {
        display: block !important;
    }
    .d-xl-table {
        display: table !important;
    }
    .d-xl-table-cell {
        display: table-cell !important;
    }
    .d-xl-flex {
        display: -ms-flexbox !important;
        display: flex !important;
    }
    .d-xl-inline-flex {
        display: -ms-inline-flexbox !important;
        display: inline-flex !important;
    }
    }

    .d-print-block {
    display: none !important;
    }

    @media print {
    .d-print-block {
        display: block !important;
    }
    }

    .d-print-inline {
    display: none !important;
    }

    @media print {
    .d-print-inline {
        display: inline !important;
    }
    }

    .d-print-inline-block {
    display: none !important;
    }

    @media print {
    .d-print-inline-block {
        display: inline-block !important;
    }
    }

    @media print {
    .d-print-none {
        display: none !important;
    }
    }

    .embed-responsive {
    position: relative;
    display: block;
    width: 100%;
    padding: 0;
    overflow: hidden;
    }

    .embed-responsive::before {
    display: block;
    content: "";
    }

    .embed-responsive .embed-responsive-item,
    .embed-responsive iframe,
    .embed-responsive embed,
    .embed-responsive object,
    .embed-responsive video {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: 0;
    }

    .embed-responsive-21by9::before {
    padding-top: 42.857143%;
    }

    .embed-responsive-16by9::before {
    padding-top: 56.25%;
    }

    .embed-responsive-4by3::before {
    padding-top: 75%;
    }

    .embed-responsive-1by1::before {
    padding-top: 100%;
    }

    .flex-row {
    -ms-flex-direction: row !important;
        flex-direction: row !important;
    }

    .flex-column {
    -ms-flex-direction: column !important;
        flex-direction: column !important;
    }

    .flex-row-reverse {
    -ms-flex-direction: row-reverse !important;
        flex-direction: row-reverse !important;
    }

    .flex-column-reverse {
    -ms-flex-direction: column-reverse !important;
        flex-direction: column-reverse !important;
    }

    .flex-wrap {
    -ms-flex-wrap: wrap !important;
        flex-wrap: wrap !important;
    }

    .flex-nowrap {
    -ms-flex-wrap: nowrap !important;
        flex-wrap: nowrap !important;
    }

    .flex-wrap-reverse {
    -ms-flex-wrap: wrap-reverse !important;
        flex-wrap: wrap-reverse !important;
    }

    .justify-content-start {
    -ms-flex-pack: start !important;
        justify-content: flex-start !important;
    }

    .justify-content-end {
    -ms-flex-pack: end !important;
        justify-content: flex-end !important;
    }

    .justify-content-center {
    -ms-flex-pack: center !important;
        justify-content: center !important;
    }

    .justify-content-between {
    -ms-flex-pack: justify !important;
        justify-content: space-between !important;
    }

    .justify-content-around {
    -ms-flex-pack: distribute !important;
        justify-content: space-around !important;
    }

    .align-items-start {
    -ms-flex-align: start !important;
        align-items: flex-start !important;
    }

    .align-items-end {
    -ms-flex-align: end !important;
        align-items: flex-end !important;
    }

    .align-items-center {
    -ms-flex-align: center !important;
        align-items: center !important;
    }

    .align-items-baseline {
    -ms-flex-align: baseline !important;
        align-items: baseline !important;
    }

    .align-items-stretch {
    -ms-flex-align: stretch !important;
        align-items: stretch !important;
    }

    .align-content-start {
    -ms-flex-line-pack: start !important;
        align-content: flex-start !important;
    }

    .align-content-end {
    -ms-flex-line-pack: end !important;
        align-content: flex-end !important;
    }

    .align-content-center {
    -ms-flex-line-pack: center !important;
        align-content: center !important;
    }

    .align-content-between {
    -ms-flex-line-pack: justify !important;
        align-content: space-between !important;
    }

    .align-content-around {
    -ms-flex-line-pack: distribute !important;
        align-content: space-around !important;
    }

    .align-content-stretch {
    -ms-flex-line-pack: stretch !important;
        align-content: stretch !important;
    }

    .align-self-auto {
    -ms-flex-item-align: auto !important;
        align-self: auto !important;
    }

    .align-self-start {
    -ms-flex-item-align: start !important;
        align-self: flex-start !important;
    }

    .align-self-end {
    -ms-flex-item-align: end !important;
        align-self: flex-end !important;
    }

    .align-self-center {
    -ms-flex-item-align: center !important;
        align-self: center !important;
    }

    .align-self-baseline {
    -ms-flex-item-align: baseline !important;
        align-self: baseline !important;
    }

    .align-self-stretch {
    -ms-flex-item-align: stretch !important;
        align-self: stretch !important;
    }

    @media (min-width: 576px) {
    .flex-sm-row {
        -ms-flex-direction: row !important;
            flex-direction: row !important;
    }
    .flex-sm-column {
        -ms-flex-direction: column !important;
            flex-direction: column !important;
    }
    .flex-sm-row-reverse {
        -ms-flex-direction: row-reverse !important;
            flex-direction: row-reverse !important;
    }
    .flex-sm-column-reverse {
        -ms-flex-direction: column-reverse !important;
            flex-direction: column-reverse !important;
    }
    .flex-sm-wrap {
        -ms-flex-wrap: wrap !important;
            flex-wrap: wrap !important;
    }
    .flex-sm-nowrap {
        -ms-flex-wrap: nowrap !important;
            flex-wrap: nowrap !important;
    }
    .flex-sm-wrap-reverse {
        -ms-flex-wrap: wrap-reverse !important;
            flex-wrap: wrap-reverse !important;
    }
    .justify-content-sm-start {
        -ms-flex-pack: start !important;
            justify-content: flex-start !important;
    }
    .justify-content-sm-end {
        -ms-flex-pack: end !important;
            justify-content: flex-end !important;
    }
    .justify-content-sm-center {
        -ms-flex-pack: center !important;
            justify-content: center !important;
    }
    .justify-content-sm-between {
        -ms-flex-pack: justify !important;
            justify-content: space-between !important;
    }
    .justify-content-sm-around {
        -ms-flex-pack: distribute !important;
            justify-content: space-around !important;
    }
    .align-items-sm-start {
        -ms-flex-align: start !important;
            align-items: flex-start !important;
    }
    .align-items-sm-end {
        -ms-flex-align: end !important;
            align-items: flex-end !important;
    }
    .align-items-sm-center {
        -ms-flex-align: center !important;
            align-items: center !important;
    }
    .align-items-sm-baseline {
        -ms-flex-align: baseline !important;
            align-items: baseline !important;
    }
    .align-items-sm-stretch {
        -ms-flex-align: stretch !important;
            align-items: stretch !important;
    }
    .align-content-sm-start {
        -ms-flex-line-pack: start !important;
            align-content: flex-start !important;
    }
    .align-content-sm-end {
        -ms-flex-line-pack: end !important;
            align-content: flex-end !important;
    }
    .align-content-sm-center {
        -ms-flex-line-pack: center !important;
            align-content: center !important;
    }
    .align-content-sm-between {
        -ms-flex-line-pack: justify !important;
            align-content: space-between !important;
    }
    .align-content-sm-around {
        -ms-flex-line-pack: distribute !important;
            align-content: space-around !important;
    }
    .align-content-sm-stretch {
        -ms-flex-line-pack: stretch !important;
            align-content: stretch !important;
    }
    .align-self-sm-auto {
        -ms-flex-item-align: auto !important;
            align-self: auto !important;
    }
    .align-self-sm-start {
        -ms-flex-item-align: start !important;
            align-self: flex-start !important;
    }
    .align-self-sm-end {
        -ms-flex-item-align: end !important;
            align-self: flex-end !important;
    }
    .align-self-sm-center {
        -ms-flex-item-align: center !important;
            align-self: center !important;
    }
    .align-self-sm-baseline {
        -ms-flex-item-align: baseline !important;
            align-self: baseline !important;
    }
    .align-self-sm-stretch {
        -ms-flex-item-align: stretch !important;
            align-self: stretch !important;
    }
    }

    @media (min-width: 768px) {
    .flex-md-row {
        -ms-flex-direction: row !important;
            flex-direction: row !important;
    }
    .flex-md-column {
        -ms-flex-direction: column !important;
            flex-direction: column !important;
    }
    .flex-md-row-reverse {
        -ms-flex-direction: row-reverse !important;
            flex-direction: row-reverse !important;
    }
    .flex-md-column-reverse {
        -ms-flex-direction: column-reverse !important;
            flex-direction: column-reverse !important;
    }
    .flex-md-wrap {
        -ms-flex-wrap: wrap !important;
            flex-wrap: wrap !important;
    }
    .flex-md-nowrap {
        -ms-flex-wrap: nowrap !important;
            flex-wrap: nowrap !important;
    }
    .flex-md-wrap-reverse {
        -ms-flex-wrap: wrap-reverse !important;
            flex-wrap: wrap-reverse !important;
    }
    .justify-content-md-start {
        -ms-flex-pack: start !important;
            justify-content: flex-start !important;
    }
    .justify-content-md-end {
        -ms-flex-pack: end !important;
            justify-content: flex-end !important;
    }
    .justify-content-md-center {
        -ms-flex-pack: center !important;
            justify-content: center !important;
    }
    .justify-content-md-between {
        -ms-flex-pack: justify !important;
            justify-content: space-between !important;
    }
    .justify-content-md-around {
        -ms-flex-pack: distribute !important;
            justify-content: space-around !important;
    }
    .align-items-md-start {
        -ms-flex-align: start !important;
            align-items: flex-start !important;
    }
    .align-items-md-end {
        -ms-flex-align: end !important;
            align-items: flex-end !important;
    }
    .align-items-md-center {
        -ms-flex-align: center !important;
            align-items: center !important;
    }
    .align-items-md-baseline {
        -ms-flex-align: baseline !important;
            align-items: baseline !important;
    }
    .align-items-md-stretch {
        -ms-flex-align: stretch !important;
            align-items: stretch !important;
    }
    .align-content-md-start {
        -ms-flex-line-pack: start !important;
            align-content: flex-start !important;
    }
    .align-content-md-end {
        -ms-flex-line-pack: end !important;
            align-content: flex-end !important;
    }
    .align-content-md-center {
        -ms-flex-line-pack: center !important;
            align-content: center !important;
    }
    .align-content-md-between {
        -ms-flex-line-pack: justify !important;
            align-content: space-between !important;
    }
    .align-content-md-around {
        -ms-flex-line-pack: distribute !important;
            align-content: space-around !important;
    }
    .align-content-md-stretch {
        -ms-flex-line-pack: stretch !important;
            align-content: stretch !important;
    }
    .align-self-md-auto {
        -ms-flex-item-align: auto !important;
            align-self: auto !important;
    }
    .align-self-md-start {
        -ms-flex-item-align: start !important;
            align-self: flex-start !important;
    }
    .align-self-md-end {
        -ms-flex-item-align: end !important;
            align-self: flex-end !important;
    }
    .align-self-md-center {
        -ms-flex-item-align: center !important;
            align-self: center !important;
    }
    .align-self-md-baseline {
        -ms-flex-item-align: baseline !important;
            align-self: baseline !important;
    }
    .align-self-md-stretch {
        -ms-flex-item-align: stretch !important;
            align-self: stretch !important;
    }
    }

    @media (min-width: 992px) {
    .flex-lg-row {
        -ms-flex-direction: row !important;
            flex-direction: row !important;
    }
    .flex-lg-column {
        -ms-flex-direction: column !important;
            flex-direction: column !important;
    }
    .flex-lg-row-reverse {
        -ms-flex-direction: row-reverse !important;
            flex-direction: row-reverse !important;
    }
    .flex-lg-column-reverse {
        -ms-flex-direction: column-reverse !important;
            flex-direction: column-reverse !important;
    }
    .flex-lg-wrap {
        -ms-flex-wrap: wrap !important;
            flex-wrap: wrap !important;
    }
    .flex-lg-nowrap {
        -ms-flex-wrap: nowrap !important;
            flex-wrap: nowrap !important;
    }
    .flex-lg-wrap-reverse {
        -ms-flex-wrap: wrap-reverse !important;
            flex-wrap: wrap-reverse !important;
    }
    .justify-content-lg-start {
        -ms-flex-pack: start !important;
            justify-content: flex-start !important;
    }
    .justify-content-lg-end {
        -ms-flex-pack: end !important;
            justify-content: flex-end !important;
    }
    .justify-content-lg-center {
        -ms-flex-pack: center !important;
            justify-content: center !important;
    }
    .justify-content-lg-between {
        -ms-flex-pack: justify !important;
            justify-content: space-between !important;
    }
    .justify-content-lg-around {
        -ms-flex-pack: distribute !important;
            justify-content: space-around !important;
    }
    .align-items-lg-start {
        -ms-flex-align: start !important;
            align-items: flex-start !important;
    }
    .align-items-lg-end {
        -ms-flex-align: end !important;
            align-items: flex-end !important;
    }
    .align-items-lg-center {
        -ms-flex-align: center !important;
            align-items: center !important;
    }
    .align-items-lg-baseline {
        -ms-flex-align: baseline !important;
            align-items: baseline !important;
    }
    .align-items-lg-stretch {
        -ms-flex-align: stretch !important;
            align-items: stretch !important;
    }
    .align-content-lg-start {
        -ms-flex-line-pack: start !important;
            align-content: flex-start !important;
    }
    .align-content-lg-end {
        -ms-flex-line-pack: end !important;
            align-content: flex-end !important;
    }
    .align-content-lg-center {
        -ms-flex-line-pack: center !important;
            align-content: center !important;
    }
    .align-content-lg-between {
        -ms-flex-line-pack: justify !important;
            align-content: space-between !important;
    }
    .align-content-lg-around {
        -ms-flex-line-pack: distribute !important;
            align-content: space-around !important;
    }
    .align-content-lg-stretch {
        -ms-flex-line-pack: stretch !important;
            align-content: stretch !important;
    }
    .align-self-lg-auto {
        -ms-flex-item-align: auto !important;
            align-self: auto !important;
    }
    .align-self-lg-start {
        -ms-flex-item-align: start !important;
            align-self: flex-start !important;
    }
    .align-self-lg-end {
        -ms-flex-item-align: end !important;
            align-self: flex-end !important;
    }
    .align-self-lg-center {
        -ms-flex-item-align: center !important;
            align-self: center !important;
    }
    .align-self-lg-baseline {
        -ms-flex-item-align: baseline !important;
            align-self: baseline !important;
    }
    .align-self-lg-stretch {
        -ms-flex-item-align: stretch !important;
            align-self: stretch !important;
    }
    }

    @media (min-width: 1200px) {
    .flex-xl-row {
        -ms-flex-direction: row !important;
            flex-direction: row !important;
    }
    .flex-xl-column {
        -ms-flex-direction: column !important;
            flex-direction: column !important;
    }
    .flex-xl-row-reverse {
        -ms-flex-direction: row-reverse !important;
            flex-direction: row-reverse !important;
    }
    .flex-xl-column-reverse {
        -ms-flex-direction: column-reverse !important;
            flex-direction: column-reverse !important;
    }
    .flex-xl-wrap {
        -ms-flex-wrap: wrap !important;
            flex-wrap: wrap !important;
    }
    .flex-xl-nowrap {
        -ms-flex-wrap: nowrap !important;
            flex-wrap: nowrap !important;
    }
    .flex-xl-wrap-reverse {
        -ms-flex-wrap: wrap-reverse !important;
            flex-wrap: wrap-reverse !important;
    }
    .justify-content-xl-start {
        -ms-flex-pack: start !important;
            justify-content: flex-start !important;
    }
    .justify-content-xl-end {
        -ms-flex-pack: end !important;
            justify-content: flex-end !important;
    }
    .justify-content-xl-center {
        -ms-flex-pack: center !important;
            justify-content: center !important;
    }
    .justify-content-xl-between {
        -ms-flex-pack: justify !important;
            justify-content: space-between !important;
    }
    .justify-content-xl-around {
        -ms-flex-pack: distribute !important;
            justify-content: space-around !important;
    }
    .align-items-xl-start {
        -ms-flex-align: start !important;
            align-items: flex-start !important;
    }
    .align-items-xl-end {
        -ms-flex-align: end !important;
            align-items: flex-end !important;
    }
    .align-items-xl-center {
        -ms-flex-align: center !important;
            align-items: center !important;
    }
    .align-items-xl-baseline {
        -ms-flex-align: baseline !important;
            align-items: baseline !important;
    }
    .align-items-xl-stretch {
        -ms-flex-align: stretch !important;
            align-items: stretch !important;
    }
    .align-content-xl-start {
        -ms-flex-line-pack: start !important;
            align-content: flex-start !important;
    }
    .align-content-xl-end {
        -ms-flex-line-pack: end !important;
            align-content: flex-end !important;
    }
    .align-content-xl-center {
        -ms-flex-line-pack: center !important;
            align-content: center !important;
    }
    .align-content-xl-between {
        -ms-flex-line-pack: justify !important;
            align-content: space-between !important;
    }
    .align-content-xl-around {
        -ms-flex-line-pack: distribute !important;
            align-content: space-around !important;
    }
    .align-content-xl-stretch {
        -ms-flex-line-pack: stretch !important;
            align-content: stretch !important;
    }
    .align-self-xl-auto {
        -ms-flex-item-align: auto !important;
            align-self: auto !important;
    }
    .align-self-xl-start {
        -ms-flex-item-align: start !important;
            align-self: flex-start !important;
    }
    .align-self-xl-end {
        -ms-flex-item-align: end !important;
            align-self: flex-end !important;
    }
    .align-self-xl-center {
        -ms-flex-item-align: center !important;
            align-self: center !important;
    }
    .align-self-xl-baseline {
        -ms-flex-item-align: baseline !important;
            align-self: baseline !important;
    }
    .align-self-xl-stretch {
        -ms-flex-item-align: stretch !important;
            align-self: stretch !important;
    }
    }

    .float-left {
    float: left !important;
    }

    .float-right {
    float: right !important;
    }

    .float-none {
    float: none !important;
    }

    @media (min-width: 576px) {
    .float-sm-left {
        float: left !important;
    }
    .float-sm-right {
        float: right !important;
    }
    .float-sm-none {
        float: none !important;
    }
    }

    @media (min-width: 768px) {
    .float-md-left {
        float: left !important;
    }
    .float-md-right {
        float: right !important;
    }
    .float-md-none {
        float: none !important;
    }
    }

    @media (min-width: 992px) {
    .float-lg-left {
        float: left !important;
    }
    .float-lg-right {
        float: right !important;
    }
    .float-lg-none {
        float: none !important;
    }
    }

    @media (min-width: 1200px) {
    .float-xl-left {
        float: left !important;
    }
    .float-xl-right {
        float: right !important;
    }
    .float-xl-none {
        float: none !important;
    }
    }

    .fixed-top {
    position: fixed;
    top: 0;
    right: 0;
    left: 0;
    z-index: 1030;
    }

    .fixed-bottom {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 1030;
    }

    @supports ((position: -webkit-sticky) or (position: sticky)) {
    .sticky-top {
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        z-index: 1020;
    }
    }

    .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    -webkit-clip-path: inset(50%);
            clip-path: inset(50%);
    border: 0;
    }

    .sr-only-focusable:active, .sr-only-focusable:focus {
    position: static;
    width: auto;
    height: auto;
    overflow: visible;
    clip: auto;
    white-space: normal;
    -webkit-clip-path: none;
            clip-path: none;
    }

    .w-25 {
    width: 25% !important;
    }

    .w-50 {
    width: 50% !important;
    }

    .w-75 {
    width: 75% !important;
    }

    .w-100 {
    width: 100% !important;
    }

    .h-25 {
    height: 25% !important;
    }

    .h-50 {
    height: 50% !important;
    }

    .h-75 {
    height: 75% !important;
    }

    .h-100 {
    height: 100% !important;
    }

    .mw-100 {
    max-width: 100% !important;
    }

    .mh-100 {
    max-height: 100% !important;
    }

    .m-0 {
    margin: 0 !important;
    }

    .mt-0 {
    margin-top: 0 !important;
    }

    .mr-0 {
    margin-right: 0 !important;
    }

    .mb-0 {
    margin-bottom: 0 !important;
    }

    .ml-0 {
    margin-left: 0 !important;
    }

    .mx-0 {
    margin-right: 0 !important;
    margin-left: 0 !important;
    }

    .my-0 {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    }

    .m-1 {
    margin: 0.25rem !important;
    }

    .mt-1 {
    margin-top: 0.25rem !important;
    }

    .mr-1 {
    margin-right: 0.25rem !important;
    }

    .mb-1 {
    margin-bottom: 0.25rem !important;
    }

    .ml-1 {
    margin-left: 0.25rem !important;
    }

    .mx-1 {
    margin-right: 0.25rem !important;
    margin-left: 0.25rem !important;
    }

    .my-1 {
    margin-top: 0.25rem !important;
    margin-bottom: 0.25rem !important;
    }

    .m-2 {
    margin: 0.5rem !important;
    }

    .mt-2 {
    margin-top: 0.5rem !important;
    }

    .mr-2 {
    margin-right: 0.5rem !important;
    }

    .mb-2 {
    margin-bottom: 0.5rem !important;
    }

    .ml-2 {
    margin-left: 0.5rem !important;
    }

    .mx-2 {
    margin-right: 0.5rem !important;
    margin-left: 0.5rem !important;
    }

    .my-2 {
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
    }

    .m-3 {
    margin: 1rem !important;
    }

    .mt-3 {
    margin-top: 1rem !important;
    }

    .mr-3 {
    margin-right: 1rem !important;
    }

    .mb-3 {
    margin-bottom: 1rem !important;
    }

    .ml-3 {
    margin-left: 1rem !important;
    }

    .mx-3 {
    margin-right: 1rem !important;
    margin-left: 1rem !important;
    }

    .my-3 {
    margin-top: 1rem !important;
    margin-bottom: 1rem !important;
    }

    .m-4 {
    margin: 1.5rem !important;
    }

    .mt-4 {
    margin-top: 1.5rem !important;
    }

    .mr-4 {
    margin-right: 1.5rem !important;
    }

    .mb-4 {
    margin-bottom: 1.5rem !important;
    }

    .ml-4 {
    margin-left: 1.5rem !important;
    }

    .mx-4 {
    margin-right: 1.5rem !important;
    margin-left: 1.5rem !important;
    }

    .my-4 {
    margin-top: 1.5rem !important;
    margin-bottom: 1.5rem !important;
    }

    .m-5 {
    margin: 3rem !important;
    }

    .mt-5 {
    margin-top: 3rem !important;
    }

    .mr-5 {
    margin-right: 3rem !important;
    }

    .mb-5 {
    margin-bottom: 3rem !important;
    }

    .ml-5 {
    margin-left: 3rem !important;
    }

    .mx-5 {
    margin-right: 3rem !important;
    margin-left: 3rem !important;
    }

    .my-5 {
    margin-top: 3rem !important;
    margin-bottom: 3rem !important;
    }

    .p-0 {
    padding: 0 !important;
    }

    .pt-0 {
    padding-top: 0 !important;
    }

    .pr-0 {
    padding-right: 0 !important;
    }

    .pb-0 {
    padding-bottom: 0 !important;
    }

    .pl-0 {
    padding-left: 0 !important;
    }

    .px-0 {
    padding-right: 0 !important;
    padding-left: 0 !important;
    }

    .py-0 {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    }

    .p-1 {
    padding: 0.25rem !important;
    }

    .pt-1 {
    padding-top: 0.25rem !important;
    }

    .pr-1 {
    padding-right: 0.25rem !important;
    }

    .pb-1 {
    padding-bottom: 0.25rem !important;
    }

    .pl-1 {
    padding-left: 0.25rem !important;
    }

    .px-1 {
    padding-right: 0.25rem !important;
    padding-left: 0.25rem !important;
    }

    .py-1 {
    padding-top: 0.25rem !important;
    padding-bottom: 0.25rem !important;
    }

    .p-2 {
    padding: 0.5rem !important;
    }

    .pt-2 {
    padding-top: 0.5rem !important;
    }

    .pr-2 {
    padding-right: 0.5rem !important;
    }

    .pb-2 {
    padding-bottom: 0.5rem !important;
    }

    .pl-2 {
    padding-left: 0.5rem !important;
    }

    .px-2 {
    padding-right: 0.5rem !important;
    padding-left: 0.5rem !important;
    }

    .py-2 {
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
    }

    .p-3 {
    padding: 1rem !important;
    }

    .pt-3 {
    padding-top: 1rem !important;
    }

    .pr-3 {
    padding-right: 1rem !important;
    }

    .pb-3 {
    padding-bottom: 1rem !important;
    }

    .pl-3 {
    padding-left: 1rem !important;
    }

    .px-3 {
    padding-right: 1rem !important;
    padding-left: 1rem !important;
    }

    .py-3 {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    }

    .p-4 {
    padding: 1.5rem !important;
    }

    .pt-4 {
    padding-top: 1.5rem !important;
    }

    .pr-4 {
    padding-right: 1.5rem !important;
    }

    .pb-4 {
    padding-bottom: 1.5rem !important;
    }

    .pl-4 {
    padding-left: 1.5rem !important;
    }

    .px-4 {
    padding-right: 1.5rem !important;
    padding-left: 1.5rem !important;
    }

    .py-4 {
    padding-top: 1.5rem !important;
    padding-bottom: 1.5rem !important;
    }

    .p-5 {
    padding: 3rem !important;
    }

    .pt-5 {
    padding-top: 3rem !important;
    }

    .pr-5 {
    padding-right: 3rem !important;
    }

    .pb-5 {
    padding-bottom: 3rem !important;
    }

    .pl-5 {
    padding-left: 3rem !important;
    }

    .px-5 {
    padding-right: 3rem !important;
    padding-left: 3rem !important;
    }

    .py-5 {
    padding-top: 3rem !important;
    padding-bottom: 3rem !important;
    }

    .m-auto {
    margin: auto !important;
    }

    .mt-auto {
    margin-top: auto !important;
    }

    .mr-auto {
    margin-right: auto !important;
    }

    .mb-auto {
    margin-bottom: auto !important;
    }

    .ml-auto {
    margin-left: auto !important;
    }

    .mx-auto {
    margin-right: auto !important;
    margin-left: auto !important;
    }

    .my-auto {
    margin-top: auto !important;
    margin-bottom: auto !important;
    }

    @media (min-width: 576px) {
    .m-sm-0 {
        margin: 0 !important;
    }
    .mt-sm-0 {
        margin-top: 0 !important;
    }
    .mr-sm-0 {
        margin-right: 0 !important;
    }
    .mb-sm-0 {
        margin-bottom: 0 !important;
    }
    .ml-sm-0 {
        margin-left: 0 !important;
    }
    .mx-sm-0 {
        margin-right: 0 !important;
        margin-left: 0 !important;
    }
    .my-sm-0 {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    .m-sm-1 {
        margin: 0.25rem !important;
    }
    .mt-sm-1 {
        margin-top: 0.25rem !important;
    }
    .mr-sm-1 {
        margin-right: 0.25rem !important;
    }
    .mb-sm-1 {
        margin-bottom: 0.25rem !important;
    }
    .ml-sm-1 {
        margin-left: 0.25rem !important;
    }
    .mx-sm-1 {
        margin-right: 0.25rem !important;
        margin-left: 0.25rem !important;
    }
    .my-sm-1 {
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
    }
    .m-sm-2 {
        margin: 0.5rem !important;
    }
    .mt-sm-2 {
        margin-top: 0.5rem !important;
    }
    .mr-sm-2 {
        margin-right: 0.5rem !important;
    }
    .mb-sm-2 {
        margin-bottom: 0.5rem !important;
    }
    .ml-sm-2 {
        margin-left: 0.5rem !important;
    }
    .mx-sm-2 {
        margin-right: 0.5rem !important;
        margin-left: 0.5rem !important;
    }
    .my-sm-2 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    .m-sm-3 {
        margin: 1rem !important;
    }
    .mt-sm-3 {
        margin-top: 1rem !important;
    }
    .mr-sm-3 {
        margin-right: 1rem !important;
    }
    .mb-sm-3 {
        margin-bottom: 1rem !important;
    }
    .ml-sm-3 {
        margin-left: 1rem !important;
    }
    .mx-sm-3 {
        margin-right: 1rem !important;
        margin-left: 1rem !important;
    }
    .my-sm-3 {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    .m-sm-4 {
        margin: 1.5rem !important;
    }
    .mt-sm-4 {
        margin-top: 1.5rem !important;
    }
    .mr-sm-4 {
        margin-right: 1.5rem !important;
    }
    .mb-sm-4 {
        margin-bottom: 1.5rem !important;
    }
    .ml-sm-4 {
        margin-left: 1.5rem !important;
    }
    .mx-sm-4 {
        margin-right: 1.5rem !important;
        margin-left: 1.5rem !important;
    }
    .my-sm-4 {
        margin-top: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    .m-sm-5 {
        margin: 3rem !important;
    }
    .mt-sm-5 {
        margin-top: 3rem !important;
    }
    .mr-sm-5 {
        margin-right: 3rem !important;
    }
    .mb-sm-5 {
        margin-bottom: 3rem !important;
    }
    .ml-sm-5 {
        margin-left: 3rem !important;
    }
    .mx-sm-5 {
        margin-right: 3rem !important;
        margin-left: 3rem !important;
    }
    .my-sm-5 {
        margin-top: 3rem !important;
        margin-bottom: 3rem !important;
    }
    .p-sm-0 {
        padding: 0 !important;
    }
    .pt-sm-0 {
        padding-top: 0 !important;
    }
    .pr-sm-0 {
        padding-right: 0 !important;
    }
    .pb-sm-0 {
        padding-bottom: 0 !important;
    }
    .pl-sm-0 {
        padding-left: 0 !important;
    }
    .px-sm-0 {
        padding-right: 0 !important;
        padding-left: 0 !important;
    }
    .py-sm-0 {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    .p-sm-1 {
        padding: 0.25rem !important;
    }
    .pt-sm-1 {
        padding-top: 0.25rem !important;
    }
    .pr-sm-1 {
        padding-right: 0.25rem !important;
    }
    .pb-sm-1 {
        padding-bottom: 0.25rem !important;
    }
    .pl-sm-1 {
        padding-left: 0.25rem !important;
    }
    .px-sm-1 {
        padding-right: 0.25rem !important;
        padding-left: 0.25rem !important;
    }
    .py-sm-1 {
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
    }
    .p-sm-2 {
        padding: 0.5rem !important;
    }
    .pt-sm-2 {
        padding-top: 0.5rem !important;
    }
    .pr-sm-2 {
        padding-right: 0.5rem !important;
    }
    .pb-sm-2 {
        padding-bottom: 0.5rem !important;
    }
    .pl-sm-2 {
        padding-left: 0.5rem !important;
    }
    .px-sm-2 {
        padding-right: 0.5rem !important;
        padding-left: 0.5rem !important;
    }
    .py-sm-2 {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    .p-sm-3 {
        padding: 1rem !important;
    }
    .pt-sm-3 {
        padding-top: 1rem !important;
    }
    .pr-sm-3 {
        padding-right: 1rem !important;
    }
    .pb-sm-3 {
        padding-bottom: 1rem !important;
    }
    .pl-sm-3 {
        padding-left: 1rem !important;
    }
    .px-sm-3 {
        padding-right: 1rem !important;
        padding-left: 1rem !important;
    }
    .py-sm-3 {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .p-sm-4 {
        padding: 1.5rem !important;
    }
    .pt-sm-4 {
        padding-top: 1.5rem !important;
    }
    .pr-sm-4 {
        padding-right: 1.5rem !important;
    }
    .pb-sm-4 {
        padding-bottom: 1.5rem !important;
    }
    .pl-sm-4 {
        padding-left: 1.5rem !important;
    }
    .px-sm-4 {
        padding-right: 1.5rem !important;
        padding-left: 1.5rem !important;
    }
    .py-sm-4 {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }
    .p-sm-5 {
        padding: 3rem !important;
    }
    .pt-sm-5 {
        padding-top: 3rem !important;
    }
    .pr-sm-5 {
        padding-right: 3rem !important;
    }
    .pb-sm-5 {
        padding-bottom: 3rem !important;
    }
    .pl-sm-5 {
        padding-left: 3rem !important;
    }
    .px-sm-5 {
        padding-right: 3rem !important;
        padding-left: 3rem !important;
    }
    .py-sm-5 {
        padding-top: 3rem !important;
        padding-bottom: 3rem !important;
    }
    .m-sm-auto {
        margin: auto !important;
    }
    .mt-sm-auto {
        margin-top: auto !important;
    }
    .mr-sm-auto {
        margin-right: auto !important;
    }
    .mb-sm-auto {
        margin-bottom: auto !important;
    }
    .ml-sm-auto {
        margin-left: auto !important;
    }
    .mx-sm-auto {
        margin-right: auto !important;
        margin-left: auto !important;
    }
    .my-sm-auto {
        margin-top: auto !important;
        margin-bottom: auto !important;
    }
    }

    @media (min-width: 768px) {
    .m-md-0 {
        margin: 0 !important;
    }
    .mt-md-0 {
        margin-top: 0 !important;
    }
    .mr-md-0 {
        margin-right: 0 !important;
    }
    .mb-md-0 {
        margin-bottom: 0 !important;
    }
    .ml-md-0 {
        margin-left: 0 !important;
    }
    .mx-md-0 {
        margin-right: 0 !important;
        margin-left: 0 !important;
    }
    .my-md-0 {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    .m-md-1 {
        margin: 0.25rem !important;
    }
    .mt-md-1 {
        margin-top: 0.25rem !important;
    }
    .mr-md-1 {
        margin-right: 0.25rem !important;
    }
    .mb-md-1 {
        margin-bottom: 0.25rem !important;
    }
    .ml-md-1 {
        margin-left: 0.25rem !important;
    }
    .mx-md-1 {
        margin-right: 0.25rem !important;
        margin-left: 0.25rem !important;
    }
    .my-md-1 {
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
    }
    .m-md-2 {
        margin: 0.5rem !important;
    }
    .mt-md-2 {
        margin-top: 0.5rem !important;
    }
    .mr-md-2 {
        margin-right: 0.5rem !important;
    }
    .mb-md-2 {
        margin-bottom: 0.5rem !important;
    }
    .ml-md-2 {
        margin-left: 0.5rem !important;
    }
    .mx-md-2 {
        margin-right: 0.5rem !important;
        margin-left: 0.5rem !important;
    }
    .my-md-2 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    .m-md-3 {
        margin: 1rem !important;
    }
    .mt-md-3 {
        margin-top: 1rem !important;
    }
    .mr-md-3 {
        margin-right: 1rem !important;
    }
    .mb-md-3 {
        margin-bottom: 1rem !important;
    }
    .ml-md-3 {
        margin-left: 1rem !important;
    }
    .mx-md-3 {
        margin-right: 1rem !important;
        margin-left: 1rem !important;
    }
    .my-md-3 {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    .m-md-4 {
        margin: 1.5rem !important;
    }
    .mt-md-4 {
        margin-top: 1.5rem !important;
    }
    .mr-md-4 {
        margin-right: 1.5rem !important;
    }
    .mb-md-4 {
        margin-bottom: 1.5rem !important;
    }
    .ml-md-4 {
        margin-left: 1.5rem !important;
    }
    .mx-md-4 {
        margin-right: 1.5rem !important;
        margin-left: 1.5rem !important;
    }
    .my-md-4 {
        margin-top: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    .m-md-5 {
        margin: 3rem !important;
    }
    .mt-md-5 {
        margin-top: 3rem !important;
    }
    .mr-md-5 {
        margin-right: 3rem !important;
    }
    .mb-md-5 {
        margin-bottom: 3rem !important;
    }
    .ml-md-5 {
        margin-left: 3rem !important;
    }
    .mx-md-5 {
        margin-right: 3rem !important;
        margin-left: 3rem !important;
    }
    .my-md-5 {
        margin-top: 3rem !important;
        margin-bottom: 3rem !important;
    }
    .p-md-0 {
        padding: 0 !important;
    }
    .pt-md-0 {
        padding-top: 0 !important;
    }
    .pr-md-0 {
        padding-right: 0 !important;
    }
    .pb-md-0 {
        padding-bottom: 0 !important;
    }
    .pl-md-0 {
        padding-left: 0 !important;
    }
    .px-md-0 {
        padding-right: 0 !important;
        padding-left: 0 !important;
    }
    .py-md-0 {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    .p-md-1 {
        padding: 0.25rem !important;
    }
    .pt-md-1 {
        padding-top: 0.25rem !important;
    }
    .pr-md-1 {
        padding-right: 0.25rem !important;
    }
    .pb-md-1 {
        padding-bottom: 0.25rem !important;
    }
    .pl-md-1 {
        padding-left: 0.25rem !important;
    }
    .px-md-1 {
        padding-right: 0.25rem !important;
        padding-left: 0.25rem !important;
    }
    .py-md-1 {
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
    }
    .p-md-2 {
        padding: 0.5rem !important;
    }
    .pt-md-2 {
        padding-top: 0.5rem !important;
    }
    .pr-md-2 {
        padding-right: 0.5rem !important;
    }
    .pb-md-2 {
        padding-bottom: 0.5rem !important;
    }
    .pl-md-2 {
        padding-left: 0.5rem !important;
    }
    .px-md-2 {
        padding-right: 0.5rem !important;
        padding-left: 0.5rem !important;
    }
    .py-md-2 {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    .p-md-3 {
        padding: 1rem !important;
    }
    .pt-md-3 {
        padding-top: 1rem !important;
    }
    .pr-md-3 {
        padding-right: 1rem !important;
    }
    .pb-md-3 {
        padding-bottom: 1rem !important;
    }
    .pl-md-3 {
        padding-left: 1rem !important;
    }
    .px-md-3 {
        padding-right: 1rem !important;
        padding-left: 1rem !important;
    }
    .py-md-3 {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .p-md-4 {
        padding: 1.5rem !important;
    }
    .pt-md-4 {
        padding-top: 1.5rem !important;
    }
    .pr-md-4 {
        padding-right: 1.5rem !important;
    }
    .pb-md-4 {
        padding-bottom: 1.5rem !important;
    }
    .pl-md-4 {
        padding-left: 1.5rem !important;
    }
    .px-md-4 {
        padding-right: 1.5rem !important;
        padding-left: 1.5rem !important;
    }
    .py-md-4 {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }
    .p-md-5 {
        padding: 3rem !important;
    }
    .pt-md-5 {
        padding-top: 3rem !important;
    }
    .pr-md-5 {
        padding-right: 3rem !important;
    }
    .pb-md-5 {
        padding-bottom: 3rem !important;
    }
    .pl-md-5 {
        padding-left: 3rem !important;
    }
    .px-md-5 {
        padding-right: 3rem !important;
        padding-left: 3rem !important;
    }
    .py-md-5 {
        padding-top: 3rem !important;
        padding-bottom: 3rem !important;
    }
    .m-md-auto {
        margin: auto !important;
    }
    .mt-md-auto {
        margin-top: auto !important;
    }
    .mr-md-auto {
        margin-right: auto !important;
    }
    .mb-md-auto {
        margin-bottom: auto !important;
    }
    .ml-md-auto {
        margin-left: auto !important;
    }
    .mx-md-auto {
        margin-right: auto !important;
        margin-left: auto !important;
    }
    .my-md-auto {
        margin-top: auto !important;
        margin-bottom: auto !important;
    }
    }

    @media (min-width: 992px) {
    .m-lg-0 {
        margin: 0 !important;
    }
    .mt-lg-0 {
        margin-top: 0 !important;
    }
    .mr-lg-0 {
        margin-right: 0 !important;
    }
    .mb-lg-0 {
        margin-bottom: 0 !important;
    }
    .ml-lg-0 {
        margin-left: 0 !important;
    }
    .mx-lg-0 {
        margin-right: 0 !important;
        margin-left: 0 !important;
    }
    .my-lg-0 {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    .m-lg-1 {
        margin: 0.25rem !important;
    }
    .mt-lg-1 {
        margin-top: 0.25rem !important;
    }
    .mr-lg-1 {
        margin-right: 0.25rem !important;
    }
    .mb-lg-1 {
        margin-bottom: 0.25rem !important;
    }
    .ml-lg-1 {
        margin-left: 0.25rem !important;
    }
    .mx-lg-1 {
        margin-right: 0.25rem !important;
        margin-left: 0.25rem !important;
    }
    .my-lg-1 {
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
    }
    .m-lg-2 {
        margin: 0.5rem !important;
    }
    .mt-lg-2 {
        margin-top: 0.5rem !important;
    }
    .mr-lg-2 {
        margin-right: 0.5rem !important;
    }
    .mb-lg-2 {
        margin-bottom: 0.5rem !important;
    }
    .ml-lg-2 {
        margin-left: 0.5rem !important;
    }
    .mx-lg-2 {
        margin-right: 0.5rem !important;
        margin-left: 0.5rem !important;
    }
    .my-lg-2 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    .m-lg-3 {
        margin: 1rem !important;
    }
    .mt-lg-3 {
        margin-top: 1rem !important;
    }
    .mr-lg-3 {
        margin-right: 1rem !important;
    }
    .mb-lg-3 {
        margin-bottom: 1rem !important;
    }
    .ml-lg-3 {
        margin-left: 1rem !important;
    }
    .mx-lg-3 {
        margin-right: 1rem !important;
        margin-left: 1rem !important;
    }
    .my-lg-3 {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    .m-lg-4 {
        margin: 1.5rem !important;
    }
    .mt-lg-4 {
        margin-top: 1.5rem !important;
    }
    .mr-lg-4 {
        margin-right: 1.5rem !important;
    }
    .mb-lg-4 {
        margin-bottom: 1.5rem !important;
    }
    .ml-lg-4 {
        margin-left: 1.5rem !important;
    }
    .mx-lg-4 {
        margin-right: 1.5rem !important;
        margin-left: 1.5rem !important;
    }
    .my-lg-4 {
        margin-top: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    .m-lg-5 {
        margin: 3rem !important;
    }
    .mt-lg-5 {
        margin-top: 3rem !important;
    }
    .mr-lg-5 {
        margin-right: 3rem !important;
    }
    .mb-lg-5 {
        margin-bottom: 3rem !important;
    }
    .ml-lg-5 {
        margin-left: 3rem !important;
    }
    .mx-lg-5 {
        margin-right: 3rem !important;
        margin-left: 3rem !important;
    }
    .my-lg-5 {
        margin-top: 3rem !important;
        margin-bottom: 3rem !important;
    }
    .p-lg-0 {
        padding: 0 !important;
    }
    .pt-lg-0 {
        padding-top: 0 !important;
    }
    .pr-lg-0 {
        padding-right: 0 !important;
    }
    .pb-lg-0 {
        padding-bottom: 0 !important;
    }
    .pl-lg-0 {
        padding-left: 0 !important;
    }
    .px-lg-0 {
        padding-right: 0 !important;
        padding-left: 0 !important;
    }
    .py-lg-0 {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    .p-lg-1 {
        padding: 0.25rem !important;
    }
    .pt-lg-1 {
        padding-top: 0.25rem !important;
    }
    .pr-lg-1 {
        padding-right: 0.25rem !important;
    }
    .pb-lg-1 {
        padding-bottom: 0.25rem !important;
    }
    .pl-lg-1 {
        padding-left: 0.25rem !important;
    }
    .px-lg-1 {
        padding-right: 0.25rem !important;
        padding-left: 0.25rem !important;
    }
    .py-lg-1 {
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
    }
    .p-lg-2 {
        padding: 0.5rem !important;
    }
    .pt-lg-2 {
        padding-top: 0.5rem !important;
    }
    .pr-lg-2 {
        padding-right: 0.5rem !important;
    }
    .pb-lg-2 {
        padding-bottom: 0.5rem !important;
    }
    .pl-lg-2 {
        padding-left: 0.5rem !important;
    }
    .px-lg-2 {
        padding-right: 0.5rem !important;
        padding-left: 0.5rem !important;
    }
    .py-lg-2 {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    .p-lg-3 {
        padding: 1rem !important;
    }
    .pt-lg-3 {
        padding-top: 1rem !important;
    }
    .pr-lg-3 {
        padding-right: 1rem !important;
    }
    .pb-lg-3 {
        padding-bottom: 1rem !important;
    }
    .pl-lg-3 {
        padding-left: 1rem !important;
    }
    .px-lg-3 {
        padding-right: 1rem !important;
        padding-left: 1rem !important;
    }
    .py-lg-3 {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .p-lg-4 {
        padding: 1.5rem !important;
    }
    .pt-lg-4 {
        padding-top: 1.5rem !important;
    }
    .pr-lg-4 {
        padding-right: 1.5rem !important;
    }
    .pb-lg-4 {
        padding-bottom: 1.5rem !important;
    }
    .pl-lg-4 {
        padding-left: 1.5rem !important;
    }
    .px-lg-4 {
        padding-right: 1.5rem !important;
        padding-left: 1.5rem !important;
    }
    .py-lg-4 {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }
    .p-lg-5 {
        padding: 3rem !important;
    }
    .pt-lg-5 {
        padding-top: 3rem !important;
    }
    .pr-lg-5 {
        padding-right: 3rem !important;
    }
    .pb-lg-5 {
        padding-bottom: 3rem !important;
    }
    .pl-lg-5 {
        padding-left: 3rem !important;
    }
    .px-lg-5 {
        padding-right: 3rem !important;
        padding-left: 3rem !important;
    }
    .py-lg-5 {
        padding-top: 3rem !important;
        padding-bottom: 3rem !important;
    }
    .m-lg-auto {
        margin: auto !important;
    }
    .mt-lg-auto {
        margin-top: auto !important;
    }
    .mr-lg-auto {
        margin-right: auto !important;
    }
    .mb-lg-auto {
        margin-bottom: auto !important;
    }
    .ml-lg-auto {
        margin-left: auto !important;
    }
    .mx-lg-auto {
        margin-right: auto !important;
        margin-left: auto !important;
    }
    .my-lg-auto {
        margin-top: auto !important;
        margin-bottom: auto !important;
    }
    }

    @media (min-width: 1200px) {
    .m-xl-0 {
        margin: 0 !important;
    }
    .mt-xl-0 {
        margin-top: 0 !important;
    }
    .mr-xl-0 {
        margin-right: 0 !important;
    }
    .mb-xl-0 {
        margin-bottom: 0 !important;
    }
    .ml-xl-0 {
        margin-left: 0 !important;
    }
    .mx-xl-0 {
        margin-right: 0 !important;
        margin-left: 0 !important;
    }
    .my-xl-0 {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    .m-xl-1 {
        margin: 0.25rem !important;
    }
    .mt-xl-1 {
        margin-top: 0.25rem !important;
    }
    .mr-xl-1 {
        margin-right: 0.25rem !important;
    }
    .mb-xl-1 {
        margin-bottom: 0.25rem !important;
    }
    .ml-xl-1 {
        margin-left: 0.25rem !important;
    }
    .mx-xl-1 {
        margin-right: 0.25rem !important;
        margin-left: 0.25rem !important;
    }
    .my-xl-1 {
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
    }
    .m-xl-2 {
        margin: 0.5rem !important;
    }
    .mt-xl-2 {
        margin-top: 0.5rem !important;
    }
    .mr-xl-2 {
        margin-right: 0.5rem !important;
    }
    .mb-xl-2 {
        margin-bottom: 0.5rem !important;
    }
    .ml-xl-2 {
        margin-left: 0.5rem !important;
    }
    .mx-xl-2 {
        margin-right: 0.5rem !important;
        margin-left: 0.5rem !important;
    }
    .my-xl-2 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    .m-xl-3 {
        margin: 1rem !important;
    }
    .mt-xl-3 {
        margin-top: 1rem !important;
    }
    .mr-xl-3 {
        margin-right: 1rem !important;
    }
    .mb-xl-3 {
        margin-bottom: 1rem !important;
    }
    .ml-xl-3 {
        margin-left: 1rem !important;
    }
    .mx-xl-3 {
        margin-right: 1rem !important;
        margin-left: 1rem !important;
    }
    .my-xl-3 {
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    .m-xl-4 {
        margin: 1.5rem !important;
    }
    .mt-xl-4 {
        margin-top: 1.5rem !important;
    }
    .mr-xl-4 {
        margin-right: 1.5rem !important;
    }
    .mb-xl-4 {
        margin-bottom: 1.5rem !important;
    }
    .ml-xl-4 {
        margin-left: 1.5rem !important;
    }
    .mx-xl-4 {
        margin-right: 1.5rem !important;
        margin-left: 1.5rem !important;
    }
    .my-xl-4 {
        margin-top: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    .m-xl-5 {
        margin: 3rem !important;
    }
    .mt-xl-5 {
        margin-top: 3rem !important;
    }
    .mr-xl-5 {
        margin-right: 3rem !important;
    }
    .mb-xl-5 {
        margin-bottom: 3rem !important;
    }
    .ml-xl-5 {
        margin-left: 3rem !important;
    }
    .mx-xl-5 {
        margin-right: 3rem !important;
        margin-left: 3rem !important;
    }
    .my-xl-5 {
        margin-top: 3rem !important;
        margin-bottom: 3rem !important;
    }
    .p-xl-0 {
        padding: 0 !important;
    }
    .pt-xl-0 {
        padding-top: 0 !important;
    }
    .pr-xl-0 {
        padding-right: 0 !important;
    }
    .pb-xl-0 {
        padding-bottom: 0 !important;
    }
    .pl-xl-0 {
        padding-left: 0 !important;
    }
    .px-xl-0 {
        padding-right: 0 !important;
        padding-left: 0 !important;
    }
    .py-xl-0 {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    .p-xl-1 {
        padding: 0.25rem !important;
    }
    .pt-xl-1 {
        padding-top: 0.25rem !important;
    }
    .pr-xl-1 {
        padding-right: 0.25rem !important;
    }
    .pb-xl-1 {
        padding-bottom: 0.25rem !important;
    }
    .pl-xl-1 {
        padding-left: 0.25rem !important;
    }
    .px-xl-1 {
        padding-right: 0.25rem !important;
        padding-left: 0.25rem !important;
    }
    .py-xl-1 {
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
    }
    .p-xl-2 {
        padding: 0.5rem !important;
    }
    .pt-xl-2 {
        padding-top: 0.5rem !important;
    }
    .pr-xl-2 {
        padding-right: 0.5rem !important;
    }
    .pb-xl-2 {
        padding-bottom: 0.5rem !important;
    }
    .pl-xl-2 {
        padding-left: 0.5rem !important;
    }
    .px-xl-2 {
        padding-right: 0.5rem !important;
        padding-left: 0.5rem !important;
    }
    .py-xl-2 {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    .p-xl-3 {
        padding: 1rem !important;
    }
    .pt-xl-3 {
        padding-top: 1rem !important;
    }
    .pr-xl-3 {
        padding-right: 1rem !important;
    }
    .pb-xl-3 {
        padding-bottom: 1rem !important;
    }
    .pl-xl-3 {
        padding-left: 1rem !important;
    }
    .px-xl-3 {
        padding-right: 1rem !important;
        padding-left: 1rem !important;
    }
    .py-xl-3 {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    .p-xl-4 {
        padding: 1.5rem !important;
    }
    .pt-xl-4 {
        padding-top: 1.5rem !important;
    }
    .pr-xl-4 {
        padding-right: 1.5rem !important;
    }
    .pb-xl-4 {
        padding-bottom: 1.5rem !important;
    }
    .pl-xl-4 {
        padding-left: 1.5rem !important;
    }
    .px-xl-4 {
        padding-right: 1.5rem !important;
        padding-left: 1.5rem !important;
    }
    .py-xl-4 {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }
    .p-xl-5 {
        padding: 3rem !important;
    }
    .pt-xl-5 {
        padding-top: 3rem !important;
    }
    .pr-xl-5 {
        padding-right: 3rem !important;
    }
    .pb-xl-5 {
        padding-bottom: 3rem !important;
    }
    .pl-xl-5 {
        padding-left: 3rem !important;
    }
    .px-xl-5 {
        padding-right: 3rem !important;
        padding-left: 3rem !important;
    }
    .py-xl-5 {
        padding-top: 3rem !important;
        padding-bottom: 3rem !important;
    }
    .m-xl-auto {
        margin: auto !important;
    }
    .mt-xl-auto {
        margin-top: auto !important;
    }
    .mr-xl-auto {
        margin-right: auto !important;
    }
    .mb-xl-auto {
        margin-bottom: auto !important;
    }
    .ml-xl-auto {
        margin-left: auto !important;
    }
    .mx-xl-auto {
        margin-right: auto !important;
        margin-left: auto !important;
    }
    .my-xl-auto {
        margin-top: auto !important;
        margin-bottom: auto !important;
    }
    }

    .text-justify {
    text-align: justify !important;
    }

    .text-nowrap {
    white-space: nowrap !important;
    }

    .text-truncate {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    }

    .text-left {
    text-align: left !important;
    }

    .text-right {
    text-align: right !important;
    }

    .text-center {
    text-align: center !important;
    }

    @media (min-width: 576px) {
    .text-sm-left {
        text-align: left !important;
    }
    .text-sm-right {
        text-align: right !important;
    }
    .text-sm-center {
        text-align: center !important;
    }
    }

    @media (min-width: 768px) {
    .text-md-left {
        text-align: left !important;
    }
    .text-md-right {
        text-align: right !important;
    }
    .text-md-center {
        text-align: center !important;
    }
    }

    @media (min-width: 992px) {
    .text-lg-left {
        text-align: left !important;
    }
    .text-lg-right {
        text-align: right !important;
    }
    .text-lg-center {
        text-align: center !important;
    }
    }

    @media (min-width: 1200px) {
    .text-xl-left {
        text-align: left !important;
    }
    .text-xl-right {
        text-align: right !important;
    }
    .text-xl-center {
        text-align: center !important;
    }
    }

    .text-lowercase {
    text-transform: lowercase !important;
    }

    .text-uppercase {
    text-transform: uppercase !important;
    }

    .text-capitalize {
    text-transform: capitalize !important;
    }

    .font-weight-normal {
    font-weight: normal;
    }

    .font-weight-bold {
    font-weight: bold;
    }

    .font-italic {
    font-style: italic;
    }

    .text-white {
    color: #fff !important;
    }

    .text-primary {
    color: #007bff !important;
    }

    a.text-primary:focus, a.text-primary:hover {
    color: #0062cc !important;
    }

    .text-secondary {
    color: #868e96 !important;
    }

    a.text-secondary:focus, a.text-secondary:hover {
    color: #6c757d !important;
    }

    .text-success {
    color: #28a745 !important;
    }

    a.text-success:focus, a.text-success:hover {
    color: #1e7e34 !important;
    }

    .text-info {
    color: #17a2b8 !important;
    }

    a.text-info:focus, a.text-info:hover {
    color: #117a8b !important;
    }

    .text-warning {
    color: #ffc107 !important;
    }

    a.text-warning:focus, a.text-warning:hover {
    color: #d39e00 !important;
    }

    .text-danger {
    color: #dc3545 !important;
    }

    a.text-danger:focus, a.text-danger:hover {
    color: #bd2130 !important;
    }

    .text-light {
    color: #f8f9fa !important;
    }

    a.text-light:focus, a.text-light:hover {
    color: #dae0e5 !important;
    }

    .text-dark {
    color: #343a40 !important;
    }

    a.text-dark:focus, a.text-dark:hover {
    color: #1d2124 !important;
    }

    .text-muted {
    color: #868e96 !important;
    }

    .text-hide {
    font: 0/0 a;
    color: transparent;
    text-shadow: none;
    background-color: transparent;
    border: 0;
    }

    .visible {
    visibility: visible !important;
    }

    .invisible {
    visibility: hidden !important;
    }
    /*# sourceMappingURL=bootstrap.css.map */"""
    dt_bootstrap = """table.dataTable{clear:both;margin-top:6px !important;margin-bottom:6px !important;max-width:none !important;border-collapse:separate !important}table.dataTable td,table.dataTable th{-webkit-box-sizing:content-box;box-sizing:content-box}table.dataTable td.dataTables_empty,table.dataTable th.dataTables_empty{text-align:center}table.dataTable.nowrap th,table.dataTable.nowrap td{white-space:nowrap}div.dataTables_wrapper div.dataTables_length label{font-weight:normal;text-align:left;white-space:nowrap}div.dataTables_wrapper div.dataTables_length select{width:75px;display:inline-block}div.dataTables_wrapper div.dataTables_filter{text-align:right}div.dataTables_wrapper div.dataTables_filter label{font-weight:normal;white-space:nowrap;text-align:left}div.dataTables_wrapper div.dataTables_filter input{margin-left:0.5em;display:inline-block;width:auto}div.dataTables_wrapper div.dataTables_info{padding-top:0.85em;white-space:nowrap}div.dataTables_wrapper div.dataTables_paginate{margin:0;white-space:nowrap;text-align:right}div.dataTables_wrapper div.dataTables_paginate ul.pagination{margin:2px 0;white-space:nowrap;justify-content:flex-end}div.dataTables_wrapper div.dataTables_processing{position:absolute;top:50%;left:50%;width:200px;margin-left:-100px;margin-top:-26px;text-align:center;padding:1em 0}table.dataTable thead>tr>th.sorting_asc,table.dataTable thead>tr>th.sorting_desc,table.dataTable thead>tr>th.sorting,table.dataTable thead>tr>td.sorting_asc,table.dataTable thead>tr>td.sorting_desc,table.dataTable thead>tr>td.sorting{padding-right:30px}table.dataTable thead>tr>th:active,table.dataTable thead>tr>td:active{outline:none}table.dataTable thead .sorting,table.dataTable thead .sorting_asc,table.dataTable thead .sorting_desc,table.dataTable thead .sorting_asc_disabled,table.dataTable thead .sorting_desc_disabled{cursor:pointer;position:relative}table.dataTable thead .sorting:before,table.dataTable thead .sorting:after,table.dataTable thead .sorting_asc:before,table.dataTable thead .sorting_asc:after,table.dataTable thead .sorting_desc:before,table.dataTable thead .sorting_desc:after,table.dataTable thead .sorting_asc_disabled:before,table.dataTable thead .sorting_asc_disabled:after,table.dataTable thead .sorting_desc_disabled:before,table.dataTable thead .sorting_desc_disabled:after{position:absolute;bottom:0.9em;display:block;opacity:0.3}table.dataTable thead .sorting:before,table.dataTable thead .sorting_asc:before,table.dataTable thead .sorting_desc:before,table.dataTable thead .sorting_asc_disabled:before,table.dataTable thead .sorting_desc_disabled:before{right:1em;content:"\2191"}table.dataTable thead .sorting:after,table.dataTable thead .sorting_asc:after,table.dataTable thead .sorting_desc:after,table.dataTable thead .sorting_asc_disabled:after,table.dataTable thead .sorting_desc_disabled:after{right:0.5em;content:"\2193"}table.dataTable thead .sorting_asc:before,table.dataTable thead .sorting_desc:after{opacity:1}table.dataTable thead .sorting_asc_disabled:before,table.dataTable thead .sorting_desc_disabled:after{opacity:0}div.dataTables_scrollHead table.dataTable{margin-bottom:0 !important}div.dataTables_scrollBody table{border-top:none;margin-top:0 !important;margin-bottom:0 !important}div.dataTables_scrollBody table thead .sorting:after,div.dataTables_scrollBody table thead .sorting_asc:after,div.dataTables_scrollBody table thead .sorting_desc:after{display:none}div.dataTables_scrollBody table tbody tr:first-child th,div.dataTables_scrollBody table tbody tr:first-child td{border-top:none}div.dataTables_scrollFoot>.dataTables_scrollFootInner{box-sizing:content-box}div.dataTables_scrollFoot>.dataTables_scrollFootInner>table{margin-top:0 !important;border-top:none}@media screen and (max-width: 767px){div.dataTables_wrapper div.dataTables_length,div.dataTables_wrapper div.dataTables_filter,div.dataTables_wrapper div.dataTables_info,div.dataTables_wrapper div.dataTables_paginate{text-align:center}}table.dataTable.table-sm>thead>tr>th{padding-right:20px}table.dataTable.table-sm .sorting:before,table.dataTable.table-sm .sorting_asc:before,table.dataTable.table-sm .sorting_desc:before{top:5px;right:0.85em}table.dataTable.table-sm .sorting:after,table.dataTable.table-sm .sorting_asc:after,table.dataTable.table-sm .sorting_desc:after{top:5px}table.table-bordered.dataTable th,table.table-bordered.dataTable td{border-left-width:0}table.table-bordered.dataTable th:last-child,table.table-bordered.dataTable th:last-child,table.table-bordered.dataTable td:last-child,table.table-bordered.dataTable td:last-child{border-right-width:0}table.table-bordered.dataTable tbody th,table.table-bordered.dataTable tbody td{border-bottom-width:0}div.dataTables_scrollHead table.table-bordered{border-bottom-width:0}div.table-responsive>div.dataTables_wrapper>div.row{margin:0}div.table-responsive>div.dataTables_wrapper>div.row>div[class^="col-"]:first-child{padding-left:0}div.table-responsive>div.dataTables_wrapper>div.row>div[class^="col-"]:last-child{padding-right:0}"""
    
    with open(cmd_line_obj.d + "/bootstrap.min.css") as bootstrpmin_out:
        bootstrpmin_out.write(bootstrap_min)
    with open(cmd_line_obj.d + "/bootstrap.css") as bootstrp_out:
        bootstrp_out.write(bootstrap)
    with open(cmd_line_obj.d + "/dataTables.bootstrap4.min.css") as bootstrpdt_out:
        bootstrpdt_out.write(dt_bootstrap)
    return
