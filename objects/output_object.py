#!/usr/bin/env python

# This object will be used for tracking EyeWitness output such as managing
# the paths for the different directories, etc.


class OutputObject:

    def __init__(self):
        self.eyewitness_path = None
        self.report_folder = None
        self.images_path = None
        self.source_files_path = None
        self.operating_system = None

    def set_os(self, os):
        self.operating_system = os
        return

    def set_ew_path(self, ew_path):
        self.eyewitness_path = ew_path
        return

    def set_report_folder(self, report_folder):
        self.report_folder = report_folder
        return
