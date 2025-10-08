#!/usr/bin/env python3

import glob
import os
import sys
import webbrowser

from modules.helpers import strtobool, open_file_input
from modules.db_manager import DB_Manager
from modules.reporting import sort_data_and_write

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
    print('Writing report')
    sort_data_and_write(cli_parsed, results)
    newfiles = glob.glob(cli_parsed.d + '/report.html')
    if open_file_input(cli_parsed):
        for f in newfiles:
            webbrowser.open(f)
        sys.exit()
