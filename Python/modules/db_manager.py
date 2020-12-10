import pickle
import sqlite3

from modules.objects import HTTPTableObject
from modules.objects import UAObject
from modules.helpers import default_creds_category


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
        c.execute('''CREATE TABLE ua
            (id integer primary key, parent_id integer, object blob,
                complete boolean, key text)''')
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
            cli_parsed.d, None)
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

    def create_ua_object(self, http_object, browser, ua):
        c = self.connection.cursor()
        obj = UAObject(browser, ua)
        obj.copy_data(http_object)
        c.execute("SELECT MAX(id) FROM ua")
        rowid = c.fetchone()[0]
        if rowid is None:
            rowid = 0
        obj.id = rowid + 1
        pobj = sqlite3.Binary(pickle.dumps(obj, protocol=2))
        c.execute(("INSERT INTO ua (parent_id, object, complete, key)"
                   " VALUES (?,?,?,?)"),
                  (http_object.id, pobj, False, browser))
        self.connection.commit()
        c.close()
        return obj

    def update_ua_object(self, ua_object):
        c = self.connection.cursor()
        o = sqlite3.Binary(pickle.dumps(ua_object, protocol=2))
        c.execute(("UPDATE ua SET object=?,complete=? WHERE id=?"),
                  (o, True, ua_object.id))
        self.connection.commit()
        c.close()

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
        cli_parsed = pickle.loads(blob)
        return cli_parsed

    def get_incomplete_http(self, q):
        count = 0
        c = self.connection.cursor()
        for row in c.execute("SELECT * FROM http WHERE complete=0"):
            o = pickle.loads(row['object'])
            q.put(o)
            count += 1
        c.close()
        return count

    def get_incomplete_ua(self, q, key):
        count = 0
        c = self.connection.cursor()
        for row in c.execute("SELECT * FROM ua WHERE complete=? AND key=?",
                             (0, key)):
            o = pickle.loads(row['object'])
            q.put(o)
            count += 1
        c.close()
        return count

    def get_complete_http(self):
        finished = []
        c = self.connection.cursor()
        rows = c.execute("SELECT * FROM http WHERE complete=1").fetchall()
        for row in rows:
            o = pickle.loads(row['object'])
            uadat = c.execute("SELECT * FROM ua WHERE parent_id=?",
                              (o.id,)).fetchall()
            for ua in uadat:
                uao = pickle.loads(ua['object'])
                if uao is not None and uao.source_code is not None and o.source_code:
                    o.add_ua_data(uao)
            finished.append(o)
        c.close()
        return finished

    def clear_table(self, tname):
        c = self.connection.cursor()
        c.execute("DELETE FROM {0}".format(tname))
        self.connection.commit()
        c.close()

    def close(self):
        self._connection.close()

    def get_cursor(self):
        return self.connection.cursor()

    def recategorize(self):
        finished = []
        counter = 0
        c = self.connection.cursor()
        rows = c.execute("SELECT * FROM http WHERE complete=1").fetchall()
        total = len(rows)
        for row in rows:
            o = pickle.loads(row['object'])
            uadat = c.execute("SELECT * FROM ua WHERE parent_id=?",
                              (o.id,)).fetchall()
            for ua in uadat:
                uao = pickle.loads(ua['object'])
                if uao is not None:
                    o.add_ua_data(uao)
            if o.category != 'unauth' and o.category != 'notfound':
                t = o.category
                o = default_creds_category(o)
                if o.category != t:
                    print('{0} changed to {1}'.format(t, o.category))
            counter += 1
            if counter % 10 == 0:
                print('{0}/{1}'.format(counter, total))
            finished.append(o)
        c.close()
        return finished

    def search_for_term(self, search):
        finished = []
        c = self.connection.cursor()
        rows = c.execute("SELECT * FROM http WHERE complete=1").fetchall()
        for row in rows:
            o = pickle.loads(row['object'])
            uadat = c.execute("SELECT * FROM ua WHERE parent_id=?",
                              (o.id,)).fetchall()
            for ua in uadat:
                uao = pickle.loads(ua['object'])
                if uao is not None:
                    o.add_ua_data(uao)
            if o.error_state is None:
                if search in o.source_code or search in o.page_title:
                    finished.append(o)
        c.close()
        return finished

    def get_mikto_results(self):
        results = []
        c = self.connection.cursor()
        rows = c.execute("SELECT * FROM http WHERE complete=1").fetchall()
        for row in rows:
            o = pickle.loads(row['object'])
            if o.error_state is None and (o.category == 'notfound'
                                          or o.category == 'crap'):
                results.append(o)
        c.close()
        return results
