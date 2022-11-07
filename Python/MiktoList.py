#!/usr/bin/env python

import glob
import os
import sys
import webbrowser

from modules.helpers import strtobool
from modules.db_manager import DB_Manager

def open_file_input(cli_parsed):
    files = glob.glob(os.path.join(cli_parsed.d, 'report.html'))
    if len(files) > 0:
        print 'Would you like to open the report now? [Y/n]',
        while True:
            try:
                response = raw_input().lower()
                if response is "":
                    return True
                else:
                    return strtobool(response)
            except ValueError:
                print "Please respond with y or n",
    else:
        print '[*] No report files found to open, perhaps no hosts were successful'
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print 'Create a file containing urls for splash pages and 404s to feed to Mikto\n'
        print '[*] Usage: python MiktoList.py <dbpath> <outfile>'
        print 'DBPath should point to the ew.db file in your EyeWitness output folder'
        sys.exit()
    db_path = sys.argv[1]
    outfile = sys.argv[2]
    if not os.path.isfile(db_path):
        print '[*] No valid db path provided'
        sys.exit()
    dbm = DB_Manager(db_path)
    dbm.open_connection()
    results = dbm.get_mikto_results()
    with open(outfile, 'w') as f:
        f.writelines([x.remote_system + '\n' for x in results])
    print 'Wrote {0} URLs to {1}'.format(len(results), outfile)