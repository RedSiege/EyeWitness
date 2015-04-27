import re
import os


class HTTPTableObject(object):

    """docstring for HTTPTableObject"""

    def __init__(self):
        super(HTTPTableObject, self).__init__()
        self._screenshot_path = None
        self._http_headers = None
        self._page_title = None
        self._remote_system = None
        self._source_path = None

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
