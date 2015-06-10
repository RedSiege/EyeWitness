import sqlite3
from objects import HTTPTableObject
from objects import UAObject
import pickle
from helpers import get_ua_values
from pprint import pprint


class DB_Manager(object):

    """docstring for DB_Manager"""

    def __init__(self, dbpath):
        super(DB_Manager, self).__init__()
        self._dbpath = dbpath
        self._connection = None

    @property
    def connection(self):
        return self._connection

    @connection.setter
    def connection(self, connection):
        self._connection = connection

    def initialize_db(self):
        c = self.connection.cursor()
        sqlite3.register_adapter(bool, int)
        sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))
        c.execute('''CREATE TABLE opts
             (object blob)''')
        c.execute('''CREATE TABLE http
            (id integer primary key, object blob, complete boolean)''')
        c.execute('''CREATE TABLE rdpvnc
            (id integer primary key, screenshot_path text, port integer,
                remote_system text, proto text, complete boolean)''')
        self.connection.commit()
        c.close()

    def open_connection(self):
        self._connection = sqlite3.connect(
            self._dbpath, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row

    def create_http_object(self, remote_system, cli_parsed):
        c = self.connection.cursor()
        obj = HTTPTableObject()
        obj.remote_system = remote_system
        obj.set_paths(
            cli_parsed.d, 'baseline' if cli_parsed.cycle is not None else None)
        obj.max_difference = cli_parsed.difference
        c.execute("SELECT MAX(id) FROM http")
        rowid = c.fetchone()[0]
        if rowid is None:
            rowid = 0
        obj.id = rowid + 1
        pobj = sqlite3.Binary(pickle.dumps(obj, protocol=2))
        c.execute(("INSERT INTO http (object, complete)"
                   "VALUES (?,?)"),
                  (pobj, False))
        self.connection.commit()
        c.close()
        return obj

    def update_http_object(self, http_object):
        c = self.connection.cursor()
        o = sqlite3.Binary(pickle.dumps(http_object, protocol=2))
        c.execute(("UPDATE http SET object=?,complete=? WHERE id=?"),
                  (o, True, http_object.id))
        self.connection.commit()
        c.close()

    def save_options(self, cli_parsed):
        opts = sqlite3.Binary(pickle.dumps(cli_parsed, protocol=2))
        c = self.connection.cursor()
        c.execute("INSERT INTO opts (object) VALUES (?)",
                  (opts,))
        self.connection.commit()
        c.close()

    def get_options(self):
        c = self.connection.cursor()
        c.execute("SELECT * FROM opts")
        blob = c.fetchone()['object']
        cli_parsed = pickle.loads(str(blob))
        return cli_parsed

    def get_incomplete_http(self, q):
        count = 0
        c = self.connection.cursor()
        for row in c.execute("SELECT * FROM http WHERE complete=0"):
            o = pickle.loads(str(row['object']))
            q.put(o)
            count += 1
        return count

    def get_complete_http(self):
        finished = []
        c = self.connection.cursor()
        for row in c.execute("SELECT * FROM http WHERE complete=1"):
            o = pickle.loads(str(row['object']))
            finished.append(o)
        return finished

    def close(self):
        self._connection.close()

    def get_cursor(self):
        return self.connection.cursor()
