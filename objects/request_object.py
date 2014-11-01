#!/usr/bin/env python

# This is the request object that will be created for every IP/URL passed in.
# It will contain the protocol(s) to be captured, IP/URL, port, response, etc.

class RequestObject:

    def __init__(self):
        self.web_protocol = False
        self.rdp_protocol = False
        self.vnc_protocol = False
        self.rdp_port = 3389
        self.vnc_port = 5900
        self.remote_ip = None
        self.web_source_code = None
        self.web_server_headers = None
        self.web_screenshot_path = None
        self.rdp_screenshot_path = None
        self.vnc_screenshot_path = None

    def set_web_request_attributes(self):
        # attributes for the upcoming web request
        self.web_protocol = True
        self.remote_ip = "X"
        return

    def set_web_response_attributes(self):
        # Attributes based on the server response
        self.web_source_code = "X"
        self.web_server_headers = "Y"
        self.web_screenshot_path = "Z"
        return

    def set_rdp_request_attributes(self):
        # Attributes for connecting to RDP services
        self.rdp_protocol = True
        self.remote_ip = "X"
        return

    def set_rdp_response_attributes(self):
        # Attributes based on rdp connection
        self.rdp_screenshot_path = "X"
        return
