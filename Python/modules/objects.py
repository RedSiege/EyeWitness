import html
import os
import re

from modules.helpers import strip_nonalphanum


class HTTPTableObject(object):

    """docstring for HTTPTableObject"""

    def __init__(self):
        super(HTTPTableObject, self).__init__()
        self._id = None
        self._screenshot_path = None
        self._http_headers = {}
        self._page_title = None
        self._remote_system = None
        self._remote_login = None
        self._source_path = None
        self._error_state = None
        self._blank = False
        self._uadata = []
        self._source_code = None
        self._max_difference = None
        self._root_path = None
        self._default_creds = None
        self._category = None
        self._ssl_error = False
        self._ua_left = None
        self._resolved = None

    def set_paths(self, outdir, suffix=None):
        file_name = self.remote_system.replace('://', '.')
        for char in [':', '/', '?', '=', '%', '+']:
            file_name = file_name.replace(char, '.')
        self.root_path = outdir
        if suffix is not None:
            file_name += '_' + suffix
        self.screenshot_path = os.path.join(
            outdir, 'screens', file_name + '.png')
        self.source_path = os.path.join(outdir, 'source', file_name + '.txt')

    @property
    def resolved(self):
        return self._resolved

    @resolved.setter
    def resolved(self, resolved):
        self._resolved = resolved

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        self._id = id

    @property
    def ua_left(self):
        return self._ua_left

    @ua_left.setter
    def ua_left(self, ua_left):
        self._ua_left = ua_left

    @property
    def root_path(self):
        return self._root_path

    @root_path.setter
    def root_path(self, root_path):
        self._root_path = root_path

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
            if ':8443' in remote_system or ':443' in remote_system:
                remote_system = 'https://' + remote_system
            else:
                remote_system = 'http://' + remote_system

        remote_system = remote_system.strip()
        if 'http://' in remote_system and re.search(':80$', remote_system) is not None:
            remote_system = remote_system.replace(':80', '')

        if 'https://' in remote_system and re.search(':443$', remote_system) is not None:
            remote_system = remote_system.replace(':443', '')

        self._remote_system = remote_system.strip()

    @property
    def source_path(self):
        return self._source_path

    @source_path.setter
    def source_path(self, source_path):
        self._source_path = source_path

    @property
    def headers(self):
        if hasattr(self, '_headers'):
            return self._headers
        else:
            missing = { "Missing Headers" : "No Headers found" }
            return missing

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

    @property
    def source_code(self):
        return self._source_code

    @source_code.setter
    def source_code(self, source_code):
        self._source_code = source_code

    @property
    def max_difference(self):
        return self._max_difference

    @max_difference.setter
    def max_difference(self, max_difference):
        self._max_difference = max_difference

    @property
    def default_creds(self):
        return self._default_creds

    @default_creds.setter
    def default_creds(self, default_creds):
        self._default_creds = default_creds

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, category):
        self._category = category

    @property
    def ssl_error(self):
        return self._ssl_error

    @ssl_error.setter
    def ssl_error(self, ssl_error):
        self._ssl_error = ssl_error

    def create_table_html(self):
        scr_path = os.path.relpath(self.screenshot_path, self.root_path)
        src_path = os.path.relpath(self.source_path, self.root_path)
        html = u""
        if self._remote_login is not None:
            html += ("""<tr>
            <td><div style=\"display: inline-block; width: 300px; word-wrap: break-word\">
            <a href=\"{address}\" target=\"_blank\">{address}</a><br>
            """).format(address=self._remote_login)
        else:
            html += ("""<tr>
            <td><div style=\"display: inline-block; width: 300px; word-wrap: break-word\">
            <a href=\"{address}\" target=\"_blank\">{address}</a><br>
            """).format(address=self.remote_system)

        if self.resolved != None and self.resolved != 'Unknown':
            html += ("""<b>Resolved to:</b> {0}<br>""").format(self.resolved)

        if len(self._uadata) > 0:
            html += ("""
                <br><b>This is the baseline request.</b><br>
                The browser type is: <b>Baseline</b><br><br>
                The user agent is: <b>Baseline</b><br><br>""")

        if self.ssl_error:
            html += "<br><b>SSL Certificate error present on\
                     <a href=\"{0}\" target=\"_blank\">{0}</a></b><br>".format(
                self.remote_system)

        if self.default_creds is not None:
            try:
                html += "<br><b>Default credentials:</b> {0}<br>".format(
                    self.sanitize(self.default_creds))
            except UnicodeEncodeError:
                html += u"<br><b>Default credentials:</b> {0}<br>".format(
                    self.sanitize(self.default_creds))

        if self.error_state is None:
            try:
                html += "\n<br><b> Page Title: </b>{0}\n".format(
                    self.sanitize(self.page_title))
            except AttributeError:
                html += "\n<br><b> Page Title:</b>{0}\n".format(
                    'Unable to Display')
            except UnicodeDecodeError:
                html += "\n<br><b> Page Title:</b>{0}\n".format(
                    'Unable to Display')
            except UnicodeEncodeError:
                html += u"\n<br><b> Page Title:</b>{0}\n".format(
                    self.sanitize(self.page_title))

            for key, value in self.headers.items():
                try:
                    html += '<br><b> {0}:</b> {1}\n'.format(
                        self.sanitize(key), self.sanitize(value))
                except UnicodeEncodeError:
                    html += u'<br><b> {0}:</b> {1}\n'.format(
                        self.sanitize(key), self.sanitize(value))
        if self.blank:
            html += ("""<br></td>
            <td><div style=\"display: inline-block; width: 850px;\">Page Blank\
            ,Connection error, or SSL Issues</div></td>
            </tr>
            """)
        elif self.error_state == 'Timeout':
            html += ("""</td><td>Hit timeout limit while attempting to
            screenshot</td></tr>""")
        elif self.error_state == 'BadStatus':
            html += ("""</td><td>Unknown error while attempting to
            screenshot</td></tr>""")
        elif self.error_state == 'ConnReset':
            html += ("""</td><td>Connection Reset</td></tr>""")
        elif self.error_state == 'ConnRefuse':
            html += ("""</td><td>Connection Refused</td></tr>""")
        elif self.error_state == 'SSLHandshake':
            html += ("""</td><td>SSL Handshake Error</td></tr>""")
        else:
            html += ("""<br><br><a href=\"{0}\"
                target=\"_blank\">Source Code</a></div></td>
                <td><div id=\"screenshot\"><a href=\"{1}\"
                target=\"_blank\"><img src=\"{1}\"
                height=\"400\"></a></div></td></tr>""").format(
                src_path, scr_path)

        if len(self._uadata) > 0:
            divid = strip_nonalphanum(self.remote_system)
            html += ("""<tr><td id={0} class="uabold" align="center" \
                colspan="2" onclick="toggleUA('{0}', '{1}');">
                Click to expand User Agents for {1}</td></tr>""").format(
                divid, self.remote_system)
            for ua_obj in sorted(self._uadata, key=lambda x: x.difference):
                html += ua_obj.create_table_html(divid)
            html += ("""<tr class="hide {0}"><td class="uared" align="center"\
             colspan="2" onclick="toggleUA('{0}', '{1}');">
            Click to collapse User Agents for {1}</td></tr>""").format(
                divid, self.remote_system)

        html += ("""</div>
        </div>""")
        return html

    def sanitize(self, incoming_html):
        if type(incoming_html) == bytes:
            pass
        else:
            incoming_html = incoming_html.encode()
        return html.escape(incoming_html.decode(), quote=True)

    def add_ua_data(self, uaobject):
        difference = abs(len(self.source_code) - len(uaobject.source_code))
        if difference > self.max_difference:
            uaobject.difference = difference
            self._uadata.append(uaobject)

    @property
    def uadata(self):
        return self._uadata

    @uadata.setter
    def uadata(self, uadata):
        self._uadata = uadata


class UAObject(HTTPTableObject):

    """docstring for UAObject"""

    def __init__(self, browser, ua):
        super(UAObject, self).__init__()
        self._browser = browser
        self._ua = ua
        self._difference = None
        self._id = None
        self._parent = None

    @property
    def browser(self):
        return self._browser

    @browser.setter
    def browser(self, browser):
        self._browser = browser

    @property
    def difference(self):
        return self._difference

    @difference.setter
    def difference(self, difference):
        self._difference = difference

    @property
    def ua(self):
        return self._ua

    @ua.setter
    def ua(self, ua):
        self._ua = ua

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        self._id = id

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        self._parent = parent

    def copy_data(self, http_object):
        self.remote_system = http_object.remote_system
        self.root_path = http_object.root_path
        self.parent = http_object.id
        super(UAObject, self).set_paths(self.root_path, self.browser)

    def create_table_html(self, divid):
        scr_path = os.path.relpath(self.screenshot_path, self.root_path)
        src_path = os.path.relpath(self.source_path, self.root_path)
        html = u""
        html += ("""<tr class="hide {0}">
        <td><div style=\"display: inline-block; width: 300px; word-wrap: break-word\">
        <a href=\"{1}\" target=\"_blank\">{1}</a><br>
        """).format(divid, self.remote_system)

        html += ("""
        <br>This request was different from the baseline.<br>
        The browser type is: <b>{0}</b><br><br>
        The user agent is: <b>{1}</b><br><br>
        Difference in length of the two webpage sources is\
        : <b>{2}</b><br>
        """).format(self.browser, self.ua, self.difference)

        if self.ssl_error:
            html += "<br><b>SSL Certificate error present on\
                     <a href=\"{0}\" target=\"_blank\">{0}</a></b><br>".format(
                self.remote_system)

        if self.default_creds is not None:
            try:
                html += "<br><b>Default credentials:</b> {0}<br>".format(
                    self.sanitize(self.default_creds))
            except UnicodeEncodeError:
                html += u"<br><b>Default credentials:</b> {0}<br>".format(
		    self.sanitize(self.default_creds))
                
        try:
            html += "\n<br><b> Page Title: </b>{0}\n".format(
                self.sanitize(self.page_title))
        except AttributeError:
            html += "\n<br><b> Page Title:</b>{0}\n".format(
                'Unable to Display')
        except UnicodeDecodeError:
            html += "\n<br><b> Page Title:</b>{0}\n".format(
                'Unable to Display')
        except UnicodeEncodeError:
                html += u'<br><b> Page Title: </b>{0}\n'.format(
                    self.sanitize(self.page_title))

        for key, value in self.headers.items():
            try: 
                html += '<br><b> {0}:</b> {1}\n'.format(
                    self.sanitize(key), self.sanitize(value))
            except UnicodeEncodeError:
                html += u'<br><b> {0}:</b> {1}\n'.format(
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
                src_path, scr_path)
        return html

