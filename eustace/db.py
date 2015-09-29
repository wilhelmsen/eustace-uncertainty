# coding: UTF-8
from contextlib import closing
import os
import tempfile
import sqlite3
import logging


# Define the logger
LOG = logging.getLogger(__name__)
_ID_CACHE = {"algorithm_id": {}, "satellite_id": {} }
_SWATH_KEYS = ["surface_temp", "t_11", "t_12", "t_37", "sat_zenit_angle", "sun_zenit_angle", "ice_concentration", "cloud_mask", "swath_datetime", "lat", "lon"]
_PERTURBATION_KEYS = ["epsilon_1", "epsilon_2", "epsilon_3", "surface_temp"]


class Db:
    # Create tables.
    SETUP_SQLS = [
        """CREATE TABLE IF NOT EXISTS satellites (id INTEGER PRIMARY KEY, name TEXT NOT NULL)""",
        """CREATE UNIQUE INDEX IF NOT EXISTS satellites_id ON satellites(name)""",

        """CREATE TABLE IF NOT EXISTS algorithms (id INTEGER PRIMARY KEY, name TEXT NOT NULL)""",
        """CREATE UNIQUE INDEX IF NOT EXISTS algorithm_name_index ON algorithms(name)""",

        """CREATE TABLE IF NOT EXISTS swath_inputs (
           id INTEGER PRIMARY KEY,
           satellite_id INT NOT NULL,
           surface_temp REAL NOT NULL,
           t_11 REAL NOT NULL,
           t_12 REAL NOT NULL,
           t_37 REAL,
           sat_zenit_angle REAL NOT NULL,
           sun_zenit_angle REAL NOT NULL,
           ice_concentration REAL,
           cloud_mask INT NOT NULL,
           swath_datetime DATETIME NOT NULL,
           lat REAL NOT NULL,
           lon REAL NOT NULL,
           FOREIGN KEY(satellite_id) REFERENCES satellites(id)
        )""",
        """CREATE INDEX IF NOT EXISTS swath_satellite_index ON swath_inputs(satellite_id)""",
        """CREATE INDEX IF NOT EXISTS swath_datetime_index ON swath_inputs(swath_datetime)""",
        """CREATE INDEX IF NOT EXISTS swath_lat_index ON swath_inputs(lat)""",
        """CREATE INDEX IF NOT EXISTS swath_lon_index ON swath_inputs(lon)""",
        """CREATE INDEX IF NOT EXISTS swath_sun_zenit_index ON swath_inputs(sun_zenit_angle)""",
        """CREATE INDEX IF NOT EXISTS swath_sat_zenit_index ON swath_inputs(sat_zenit_angle)""",

        """CREATE TABLE IF NOT EXISTS perturbations (
           id INT PRIMARY KEY,
           swath_input_id INT NOT NULL,
           algorithm_id INT NOT NULL,
           epsilon_1 REAL NOT NULL,
           epsilon_2 REAL NOT NULL,
           epsilon_3,
           surface_temp REAL NOT NULL,
           FOREIGN KEY(swath_input_id) REFERENCES swath_inputs(id),
           FOREIGN KEY(algorithm_id) REFERENCES algorithms(id)
        )""",
        """CREATE INDEX IF NOT EXISTS pert_swath_input_index ON perturbations(swath_input_id)""",
        """CREATE INDEX IF NOT EXISTS pert_algorithm_index ON perturbations(algorithm_id)""",
        ]

    def __init__(self, db_filename):
        self.db_filename = db_filename
        self.conn = sqlite3.connect(self.db_filename)
        self.c = self.conn.cursor()
        
        # TODO: Create tables.
        for sql in Db.SETUP_SQLS:
            self.execute_and_commit(sql)

    def __enter__(self):
        LOG.debug("Entering db.")
        return self

    def __exit__(self, type, value, traceback):
        LOG.debug("Exiting db.")
        self.conn.commit()
        self.conn.close()

    def execute(self, sql, values=None):
        if values is None:
            LOG.debug("Executing SQL: '%s'." % (sql))
            self.c.execute(sql)
        else:
            LOG.debug("Executing SQL: '%s' with values: '%s'." % (sql, values))
            self.c.execute(sql, values)
        LOG.debug("Committing SQL.")

    def execute_and_commit(self, sql, values=None):
        self.execute(sql, values)
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

    def find_or_create_algorithm_id(self, algorithm_name):
        """ Find the id of the satellite name in the database"""

        # First... make sure it is in lowercase in the database.
        algorithm_name = algorithm_name.lower().strip()

        # Check if it is in the cache...
        if algorithm_name not in _ID_CACHE["algorithm_id"]:
            # It is not in the cache.
            # Check if it is in the database.
            self.execute("SELECT id FROM algorithms WHERE name = ? LIMIT 1", (algorithm_name, ))
            algorithm_id = self.c.fetchone()
            if algorithm_id is not None:
                # It was in the database.
                algorithm_id = int(algorithm_id[0])
            else:
                # It was not in the database.
                # Insert it.
                self.execute_and_commit("INSERT INTO algorithms (name) VALUES (?)", (algorithm_name, ))
                algorithm_id = self.c.lastrowid

                # Make sure it was actually inserted.
                if algorithm_id is None:
                    raise RuntimeException("Could not set the satellite name...")

            # Set the cache.
            _ID_CACHE["algorithm_id"][algorithm_name] = algorithm_id

        # Return the cached number.
        return _ID_CACHE["algorithm_id"][algorithm_name]


    def find_or_create_satellite_id(self, satellite_name):
        """ Find the id of the satellite name in the database"""
        
        # First... make sure it is in lowercase in the database.
        satellite_name = satellite_name.lower().strip()

        # Check if it is in the cache...
        if satellite_name not in _ID_CACHE["satellite_id"]:
            # It is not in the cache.
            # Check if it is in the database.
            self.execute("SELECT id FROM satellites WHERE name = ? LIMIT 1", (satellite_name, ))
            satellite_id = self.c.fetchone()
            if satellite_id is not None:
                # It was in the database.
                satellite_id = int(satellite_id[0])
            else:
                # It was not in the database.
                # Insert it.
                self.execute_and_commit("INSERT INTO satellites (name) VALUES (?)", (satellite_name, ))
                satellite_id = self.c.lastrowid

                # Make sure it was actually inserted.
                if satellite_id is None:
                    raise RuntimeException("Could not set the satellite name...")

            # Set the cache.
            _ID_CACHE["satellite_id"][satellite_name] = satellite_id

        # Return the cached number.
        return _ID_CACHE["satellite_id"][satellite_name]


    def insert_swath_values(self, satellite_name, **kwargs):
        """
        Returns the id of the inserted swath pixel.
        """
        # Make sure all the values actually exist in the databae.
        for k in kwargs.keys():
            if k not in _SWATH_KEYS:
                raise RuntimeError("%s must be one of '%s'" % (k, ", ".join(_SWATH_KEYS)))

        # Get the satellite ID.
        satellite_id = self.find_or_create_satellite_id(satellite_name)

        # Insert all the given values. Build the sql.
        variable_string = ", ".join([str(k) for k in kwargs.keys()])
        value_string = ", ?"*len(kwargs)
        sql = "INSERT INTO swath_inputs (satellite_id, %s) VALUES (%i%s)" % (variable_string, satellite_id, value_string)
        self.execute(sql, kwargs.values())
        return self.c.lastrowid

    def insert_perturbation_values(self, swath_input_id, algorithm_name, **kwargs):
        # Make sure all the values actually exist in the databae.
        for k in kwargs.keys():
            if k not in _PERTURBATION_KEYS:
                raise RuntimeError("%s must be one of '%s'" % (k, ", ".join(_PERTURBATION_KEYS)))

        # Get the satellite ID.
        algorithm_id = self.find_or_create_algorithm_id(algorithm_name)

        # Insert all the given values. Build the sql.
        variable_string = ", ".join([str(k) for k in kwargs.keys()])
        value_string = ", ?"*len(kwargs)
        sql = "INSERT INTO perturbations (swath_input_id, algorithm_id, %s) VALUES (%i, %i%s)" % (variable_string, swath_input_id, algorithm_id, value_string)
        self.execute(sql, kwargs.values())

        
if __name__ == "__main__":

    with Db("/tmp/fisk.db") as db:
        for sql in sql_list:
            db.execute(sql)
            
