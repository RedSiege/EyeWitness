import re
import os
import cgi


class HTTPTableObject(object):

    """docstring for HTTPTableObject"""

    def __init__(self):
        super(HTTPTableObject, self).__init__()
        self._screenshot_path = None
        self._http_headers = {}
        self._page_title = None
        self._remote_system = None
        self._source_path = None
        self._error_state = None
        self._blank = False

    def set_paths(self, outdir, web_address=None):
        if web_address is None:
            web_address = self.remote_system

        file_name = web_address.replace('://', '.')
        for char in [':', '/', '?', '=', '%', '+']:
            file_name = file_name.replace(char, '.')
        self.screenshot_path = os.path.join(
            outdir, 'screens', file_name + '.png')
        self.source_path = os.path.join(outdir, 'source', file_name + '.txt')

    @property
    def screenshot_path(self):
        return self._screenshot_path

    @screenshot_path.setter
    def screenshot_path(self, screenshot_path):
        self._screenshot_path = screenshot_path

    @property
    def http_headers(self):
        return self._http_headers

    @http_headers.setter
    def http_headers(self, headers):
        self._http_headers = headers

    @property
    def page_title(self):
        return self._page_title

    @page_title.setter
    def page_title(self, page_title):
        self._page_title = page_title

    @property
    def remote_system(self):
        return self._remote_system

    @remote_system.setter
    def remote_system(self, remote_system):
        if remote_system.startswith('http://') or remote_system.startswith('https://'):
            pass
        else:
            remote_system = 'http://' + remote_system
        self._remote_system = remote_system.strip()

    @property
    def source_path(self):
        return self._source_path

    @source_path.setter
    def source_path(self, source_path):
        self._source_path = source_path

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, headers):
        self._headers = headers

    @property
    def error_state(self):
        return self._error_state

    # Error states include Timeouts and other errors
    @error_state.setter
    def error_state(self, error_state):
        self._error_state = error_state

    @property
    def blank(self):
        return self._blank

    @blank.setter
    def blank(self, blank):
        self._blank = blank

    def create_table_html(self):
        html = u""
        html += ("""<tr>
        <td><div style=\"display: inline-block; width: 300px; word-wrap: break-word\">
        <a href=\"{address}\" target=\"_blank\">{address}</a><br>
        """).format(address=self.remote_system)

        try:
            html += "\n<br><b> Page Title: </b>{0}\n".format(
                self.sanitize(self.page_title))
        except UnicodeDecodeError:
            html += "\n<br><b> Page Title:</b>{0}\n".format(
                'Unable to Display')

        for key, value in self.headers.items():
            html += '<br><b> {0}:</b> {1}\n'.format(
                self.sanitize(key), self.sanitize(value))

        if self.blank:
            html += ("""<br></td>
            <td><div style=\"display: inline-block; width: 850px;\">Page Blank,\
            Connection error, or SSL Issues</div></td>
            </tr>
            """)
        else:
            html += ("""<br><br><a href=\"{0}\"
                target=\"_blank\">Source Code</a></div></td>
                <td><div id=\"screenshot\"><a href=\"{1}\"
                target=\"_blank\"><img src=\"{1}\"
                height=\"400\"></a></div></td></tr>""").format(
                self.source_path, self.screenshot_path)
        return html

    def sanitize(self, html):
        return cgi.escape(html, quote=True)


class RDPTableObject(object):

    """docstring for RDPTableObject"""

    def __init__(self):
        super(RDPTableObject, self).__init__()
        self._screenshot_path = None
        self._port = None
        self._remote_system = None

    @property
    def screenshot_path(self):
        return self._screenshot_path

    @screenshot_path.setter
    def screenshot_path(self, screenshot_path):
        self._screenshot_path = screenshot_path

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port

    @property
    def remote_system(self):
        return self._remote_system

    @remote_system.setter
    def remote_system(self, remote_system):
        self._remote_system = remote_system


class VNCTableObject(object):

    """docstring for VNCTableObject"""

    def __init__(self):
        super(VNCTableObject, self).__init__()
        self._screenshot_path = None
        self._port = None
        self._remote_system = None

    @property
    def screenshot_path(self):
        return self._screenshot_path

    @screenshot_path.setter
    def screenshot_path(self, screenshot_path):
        self._screenshot_path = screenshot_path

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port

    @property
    def remote_system(self):
        return self._remote_system

    @remote_system.setter
    def remote_system(self, remote_system):
        self._remote_system = remote_system
