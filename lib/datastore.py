"""
This class consolidates functions related to the local sqlite datastore and not included in the application, except
then the test application.
"""

import logging
import sqlite3
# import sys


class DataStore:

    tables = ['components', 'relations', 'labels']

    def __init__(self, dbfile):
        """
        Method to instantiate the class in an object for the datastore.
        @param dbfile - full path to the database filename.
        @return: Object to handle datastore commands.
        """
        logging.debug("Initializing Datastore object")
        self.dbConn, self.cur = self._connect2db(dbfile)
        return

    @staticmethod
    def _connect2db(dbfile):
        """
        Internal method to create a database connection and a cursor. This method is called during object
        initialization.
        Note that sqlite connection object does not test the Database connection. If database does not exist, this
        method will not fail. This is expected behaviour, since it will be called to create databases as well.
        @param dbfile: Full path to the database file.
        @return: Database handle and cursor for the database.
        """
        logging.debug("Creating Datastore object and cursor")
        db = dbfile
        db_conn = sqlite3.connect(db)
        logging.debug("Datastore object and cursor are created")
        db_conn.row_factory = sqlite3.Row
        return db_conn, db_conn.cursor()

    def close_connection(self):
        """
        Method to close the Database Connection.
        @return:
        """
        logging.debug("Close connection to database")
        self.dbConn.close()
        return

    def create_tables(self):
        self.create_table_components()
        self.create_table_relations()
        self.create_table_labels()
        return

    def clear_tables(self):
        for table in self.tables:
            query = "DELETE FROM {table}".format(table=table)
            self.dbConn.execute(query)
            logging.info("Clear table {table}".format(table=table))

    def remove_tables(self):
        for table in self.tables:
            self.remove_table(table)

    def remove_table(self, table):
        query = "DROP TABLE IF EXISTS {table}".format(table=table)
        self.dbConn.execute(query)
        logging.info("Drop table {table}".format(table=table))
        return True

    def create_table_components(self):
        # Create table
        # Get the field names from Protege - Slots, where Value Type is not Instance.
        # class and protege_id are fixed and should always be there.
        query = """
        CREATE TABLE components
            (beschrijving text,
             born text,
             city text,
             day integer,
             key text,
             mf text,
             month integer,
             name text,
             nid text unique not null,
             points integer,
             pos integer,
             pwd text,
             rel_pos integer,
             remark text,
             weight text,
             year integer
            )
        """
        self.dbConn.execute(query)
        logging.info("Table components is build.")
        return True

    def create_table_relations(self):
        # Create table
        query = """
        CREATE TABLE relations
            (rel text not null,
             from_nid text not null,
             to_nid text not null)
        """
        self.dbConn.execute(query)
        logging.info("Table relations is build.")
        return True

    def create_table_labels(self):
        # Create table
        query = """
        CREATE TABLE labels
            (label text not null,
             nid text not null)
        """
        self.dbConn.execute(query)
        logging.info("Table labels is build.")
        return True

    def insert_row(self, tablename, rowdict):
        columns = ", ".join(rowdict.keys())
        values_template = ", ".join(["?"] * len(rowdict.keys()))
        query = "insert into  {tn} ({cols}) values ({vt})".format(tn=tablename, cols=columns, vt=values_template)
        values = tuple(rowdict[key] for key in rowdict.keys())
        # print("Query: {q}".format(q=query))
        self.dbConn.execute(query, values)
        self.dbConn.commit()
        return

    def get_records(self, tablename):
        """
        This method will return all components with all attributes from the components table 'in_bereik'.
        @param tablename: Tablename for which records need to be retrieved.
        @return: Array of components. Each component is a dictionary of the array.
        """
        query = "SELECT * FROM {t}".format(t=tablename)
        self.cur.execute(query)
        rows = self.cur.fetchall()
        return rows

    def get_key_list(self, tablename):
        """
        This method will get the columns for the table.
        :param tablename:
        :return:
        """
        query = "SELECT * FROM {t}".format(t=tablename)
        cursor = self.cur.execute(query)
        key_list = [description[0] for description in cursor.description]
        return key_list

    def get_label(self, nid):
        """
        This method will get the label for the node with nid.
        :param nid:
        :return: label
        """
        query = "SELECT label FROM labels WHERE nid=?"
        res = self.cur.execute(query, (nid,))
        rec = next(res)
        return rec["label"]
