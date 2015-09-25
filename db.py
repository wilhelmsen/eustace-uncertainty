# coding: UTF-8
import os
import tempfile
import sqlite3
import logging

# Define the logger
LOG = logging.getLogger(__name__)

class Db:
    def __init__(self, db_filename):
        self.db_filename = db_filename
        self.conn = sqlite3.connect(self.db_filename)
        self.c = self.conn.cursor()
        # TODO: Create tables.

    def __enter__(self):
        LOG.debug("Entering db.")
        return self

    def __exit__(self, type, value, traceback):
        LOG.debug("Exiting db.")
        self.conn.close()

    def execute(self, sql, values=None):
        if values is None:
            LOG.debug("Executing SQL: '%s'." % (sql))
            self.c.execute(sql)
        else:
            LOG.debug("Executing SQL: '%s' with values: '%s'." % (sql, values))
            self.c.execute(sql, values)

        LOG.debug("Committing SQL.")
        self.conn.commit()

    def get_rows(self, sql, where_values=None):
        if where_values is None:
            LOG.debug("Executing SQL: '%s'." % (sql))
            for row in self.c.execute(sql):
                yield row
        else:
            LOG.debug("Executing SQL: '%s' with values: '%s'." %
                      (sql, where_values))
            for row in self.c.execute(sql, where_values):
                yield row

    def insert(self, surface_temperature_truth_K, t11_K, t12_K, t37_K,
               satellite_id, algorithm, time, sat_zenit_angle, sun_zenit_angle,
               ice_concentration, cloud_mask, epsilon_1, epsilon_2, epsilon_3,
               st_new):
        pass
        
        

if __name__ == "__main__":
    # Create tables.
    sql_list = [
        """CREATE TABLE IF NOT EXISTS satellites (id INTEGER PRIMARY KEY, name TEXT)""",
        """CREATE UNIQUE INDEX satellites_id ON satellites(name)""",
        """CREATE TABLE IF NOT EXISTS algorithms (id INTEGER PRIMARY KEY, name TEXT)""",
        """CREATE UNIQUE INDEX algorithms_id ON satellites(name)""",
        """CREATE TABLE IF NOT EXISTS temperatures (
           id INTEGER PRIMARY KEY,
           satellite_id INTEGER,
           algorithm_id TEXT,
           time TEXT,
           lat REAL,
           lon REAL,
           sat_zenit_angle REAL,
           sun_zenit_angle REAL,
           temperature_true REAL,
           temperature_simulated REAL,
           FOREIGN KEY(satellite_id) REFERENCES satellites(id),
           FOREIGN KEY(algorithm_id) REFERENCES algorithms(id)
        )""",
        ]

    with Db("/tmp/fisk.db") as db:
        for sql in sql_list:
            db.execute(sql)
            
