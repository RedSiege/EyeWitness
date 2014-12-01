#!/usr/bin/env python

# This is the request object that will be created for every IP/URL passed in.
# It will contain the protocol(s) to be captured, IP/URL, port, response, etc.


class RequestObject:

    def __init__(self):
        self.web_protocol = False
        self.rdp_protocol = False
        self.vnc_protocol = False
        self.rdp_port = None
        self.vnc_port = None
        self.remote_system = None
        self.web_source_code = None
        self.web_server_headers = None
        self.web_sourcecode_path = None
        self.web_screenshot_path = None
        self.web_default_credentials = None
        self.rdp_screenshot_path = None
        self.vnc_screenshot_path = None

    def set_web_request_attributes(self, web_address):
        # attributes for the upcoming web request
        self.web_protocol = True

        # If URL doesn't start with http:// or https://, assume it is
        # http:// and add it to URL
        if web_address.startswith('http://') or web_address.\
                startswith('https://'):
            pass
        else:
            web_address = "http://" + web_address

        self.remote_system = web_address.strip()
        return

    def set_default_creds(self, creds):
        self.web_default_credentials = creds
        return

    def return_remote_system_address(self):
        return self.remote_system

    def set_web_response_attributes(self, source, headers, web_screen_path):
        # Attributes based on the server response
        self.web_source_code = source
        self.web_server_headers = headers
        self.web_screenshot_path = web_screen_path
        return

    def set_rdp_request_attributes(self, rdp_target):
        # Attributes for connecting to RDP services
        self.rdp_protocol = True
        self.remote_system = rdp_target
        return

    def set_rdp_response_attributes(self, rdp_screen_path):
        # Attributes based on rdp connection
        self.rdp_screenshot_path = rdp_screen_path
        return

    def set_vnc_request_attributes(self, vnc_target):
        # Attributes for connecting to vnc services
        self.vnc_protocol = True
        self.remote_system = vnc_target
        return

    def set_vnc_response_attributes(self, vnc_screen_path):
        # Attributes based on vnc connection
        self.vnc_screenshot_path = vnc_screen_path
        return
