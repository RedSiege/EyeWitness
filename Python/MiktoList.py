#!/usr/bin/env python

import glob
import os
import sys
import webbrowser

from modules.helpers import strtobool, open_file_input
from modules.db_manager import DB_Manager

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Create a file containing urls for splash pages and 404s to feed to Mikto\n')
        print('[*] Usage: python MiktoList.py <dbpath> <outfile>')
        print('DBPath should point to the ew.db file in your EyeWitness output folder')
        sys.exit()
    db_path = sys.argv[1]
    outfile = sys.argv[2]
    if not os.path.isfile(db_path):
        print('[*] No valid db path provided')
        sys.exit()
    dbm = DB_Manager(db_path)
    dbm.open_connection()
    results = dbm.get_mikto_results()
    with open(outfile, 'w') as f:
        f.writelines([x.remote_system + '\n' for x in results])
    print('Wrote {0} URLs to {1}'.format(len(results), outfile))
