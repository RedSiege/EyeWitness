#!/usr/bin/env python3

import glob
import os
import sys
import webbrowser

from modules.helpers import strtobool
from modules.db_manager import DB_Manager
from modules.reporting import sort_data_and_write

def open_file_input(cli_parsed):
    files = glob.glob(os.path.join(cli_parsed.d, 'report.html'))
    if len(files) > 0:
        print('Would you like to open the report now? [Y/n]'),
        while True:
            try:
                response = input().lower()
                if response == "":
                    return True
                else:
                    return strtobool(response)
            except ValueError:
                print("Please respond with y or n"),
    else:
        print ('[*] No report files found to open, perhaps no hosts were successful')
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Recategorize a previously completed EyeWitness scan to account for updates. This can take a while!\n')
        print('[*] Usage: python Recategorize.py <dbpath>')
        print('DBPath should point to the ew.db file in your EyeWitness output folder')
        sys.exit()
    db_path = sys.argv[1]
    if not os.path.isfile(db_path):
        print('[*] No valid db path provided')
        sys.exit()
    dbm = DB_Manager(db_path)
    dbm.open_connection()
    cli_parsed = dbm.get_options()
    cli_parsed.d = os.path.dirname(db_path)
    cli_parsed.results = 50
    files = glob.glob(cli_parsed.d + '/report*.html')
    for f in files:
        os.remove(f)
    results = dbm.recategorize()
    print ('Writing report')
    sort_data_and_write(cli_parsed, results)
    newfiles = glob.glob(cli_parsed.d + '/report.html')
    if open_file_input(cli_parsed):
        for f in newfiles:
            webbrowser.open(f)
        sys.exit()
