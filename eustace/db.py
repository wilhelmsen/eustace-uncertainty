# coding: UTF-8
import sqlite3
import logging
import numpy as np

# Define the logger
LOG = logging.getLogger(__name__)

# Temp structure that should be removed.
# Valid values to insert into the different tables. There are more values in the tables, and this functionality
# should be removed when the structure is more decided.
_SWATH_KEYS = ["satellite_name", "surface_temp", "t_11", "t_12", "t_37", "sat_zenith_angle", "sun_zenith_angle", "sea_ice_fraction", "cloudmask", "swath_datetime", "lat", "lon"]
_PERTURBATION_KEYS = ["epsilon_11", "epsilon_12", "epsilon_37", "surface_temp"]


class Db:
    # Create tables.
    SETUP_SQLS = [
        """CREATE TABLE IF NOT EXISTS swath_inputs (
           id INTEGER PRIMARY KEY,
           satellite TEXT NOT NULL,
           surface_temp REAL NOT NULL,
           t_11 REAL NOT NULL,
           t_12 REAL NOT NULL,
           t_37 REAL,
           sat_zenith_angle REAL NOT NULL,
           sun_zenith_angle REAL NOT NULL,
           sea_ice_fraction REAL,
           cloudmask INT NOT NULL,
           swath_datetime DATETIME NOT NULL,
           lat REAL NOT NULL,
           lon REAL NOT NULL
        )""",
        """CREATE INDEX IF NOT EXISTS swath_satellite_index ON swath_inputs(satellite)""",
        """CREATE INDEX IF NOT EXISTS swath_datetime_index ON swath_inputs(swath_datetime)""",
        """CREATE INDEX IF NOT EXISTS swath_lat_index ON swath_inputs(lat)""",
        """CREATE INDEX IF NOT EXISTS swath_lon_index ON swath_inputs(lon)""",
        """CREATE INDEX IF NOT EXISTS swath_sun_zenith_index ON swath_inputs(sun_zenith_angle)""",
        """CREATE INDEX IF NOT EXISTS swath_sat_zenith_index ON swath_inputs(sat_zenith_angle)""",

        """CREATE TABLE IF NOT EXISTS perturbations (
           id INT PRIMARY KEY,
           swath_input_id INT NOT NULL,
           algorithm TEXT NOT NULL,
           epsilon_11 REAL NOT NULL,
           epsilon_12 REAL NOT NULL,
           epsilon_37,
           surface_temp REAL NOT NULL,
           FOREIGN KEY(swath_input_id) REFERENCES swath_inputs(id)
        )""",
        """CREATE INDEX IF NOT EXISTS pert_swath_input_index ON perturbations(swath_input_id)""",
        """CREATE INDEX IF NOT EXISTS pert_algorithm_index ON perturbations(algorithm)""",
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
        if values is None or len(values) == 0:
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
        if where_values is None or len(where_values) == 0:
            LOG.debug("Executing SQL: '%s'." % (sql))
            for row in self.c.execute(sql):
                yield row
        else:
            LOG.debug("Executing SQL: '%s' with values: '%s'." % (sql, where_values))
            for row in self.c.execute(sql, where_values):
                yield row

    def insert_swath_values(self, satellite_name, **kwargs):
        """
        Returns the id of the inserted swath pixel.
        """
        # Make sure all the values actually exist in the databae.
        for k in kwargs.keys():
            if k not in _SWATH_KEYS:
                raise RuntimeError("%s must be one of '%s'" % (k, ", ".join(_SWATH_KEYS)))

        # Insert all the given values. Build the sql.
        variable_string = ", ".join([str(k) for k in kwargs.keys()])
        value_string = ", ?"*len(kwargs)
        sql = "INSERT INTO swath_inputs (satellite, %s) VALUES ('%s'%s)" % (variable_string, satellite_name, value_string)
        self.execute_and_commit(sql, kwargs.values())
        return self.c.lastrowid


    def insert_perturbation_values(self, swath_input_id, algorithm_name, **kwargs):
        # Make sure all the values actually exist in the databae.
        for k in kwargs.keys():
            if k not in _PERTURBATION_KEYS:
                raise RuntimeError("%s must be one of '%s'" % (k, ", ".join(_PERTURBATION_KEYS)))

        # Insert all the given values. Build the sql.
        variable_string = ", ".join([str(k) for k in kwargs.keys()])
        value_string = ", ?"*len(kwargs)
        sql = "INSERT INTO perturbations (swath_input_id, algorithm, %s) VALUES (%i, '%s'%s)" % (variable_string, swath_input_id, algorithm_name, value_string)
        self.execute(sql, kwargs.values())

    def insert_many_perturbations(self, swath_input_id, perturbations):
        counter = 0
        for algorithm, epsilon_11, epsilon_12, epsilon_37, st_K in perturbations:
            if np.isnan(st_K) or st_K is None:
                # No need to do more for this perturbation, if the output is not a number.
                continue

            self.insert_perturbation_values(swath_input_id, algorithm,
                                            epsilon_11 = epsilon_11,
                                            epsilon_12 = epsilon_12,
                                            epsilon_37 = epsilon_37,
                                            surface_temp = st_K)
            counter += 1
        self.conn.commit()
        return counter



    """
    def get_perturbed_statistics(self, variable, where=None):
        result = {}
        sql = "SELECT algorithm, AVG({variable}) AS AVG, AVG({variable}*{variable}) - AVG({variable})*AVG({variable}) AS variance FROM perturbations GROUP BY algorithm;".format(variable=variable)

        LOG.debug(sql)
        for row in self.get_rows(sql):
            result[row[0]] = [row[1], row[2]]
        return result
       """


    def build_where_sql(self, lat_less_than=None, lat_greater_than=None,
                        st_less_than=None, st_greater_than=None,
                        tb_11_minus_tb_12_limit=None, algorithm=None):
        # TODO: Move this to db.py
        #
        # Where...
        # or...
        where_sql_or = []
        if lat_less_than is not None:
            where_sql_or.append("s.lat < %s" % (lat_less_than))
        if lat_greater_than is not None:
            where_sql_or.append("s.lat > %s" % (lat_greater_than))
        where_sql = " OR ".join(where_sql_or)
        if len(where_sql_or) > 0:
            where_sql = "(%s)" % (where_sql)

        # and...
        where_sql_and = [where_sql,] if len(where_sql) > 0 else []
        if tb_11_minus_tb_12_limit is not None:
            where_sql_and.append("ABS(s.t_11 - s.t_12) < %s" % (tb_11_minus_tb_12_limit))
            where_sql_and.append("ABS(s.t_11 + p.epsilon_11 - s.t_12 + p.epsilon_12) < %s" % (tb_11_minus_tb_12_limit))

        if algorithm is not None:
            where_sql_and.append("p.algorithm IS '%s'" % (algorithm))

        if st_less_than is not None:
            where_sql_and.append("p.surface_temp <= %i" % (st_less_than))

        if st_greater_than is not None:
            where_sql_and.append("p.surface_temp > %i" % (st_greater_than))

        # Join it all.
        where_sql = " AND ".join(where_sql_and)
        return where_sql

 
    def get_perturbed_values(self, swath_variables=None, lat_less_than=None,
                             lat_greater_than=None, tb_11_minus_tb_12_limit=None,
                             st_less_than=None, st_greater_than=None,
                             algorithm=None, limit=None):
        """
        Gets the (perturbed) values from the database.
        """
        # The values to get from the database.
        swath_variables_string = ", %s" % (", ".join(swath_variables)) if swath_variables is not None else ""

        # Build the sql.
        sql = "SELECT p.surface_temp - s.surface_temp {swath_variables_string} FROM swath_inputs AS s JOIN perturbations AS p ON p.swath_input_id = s.id".format(swath_variables_string = swath_variables_string)

        # Build the where sql.
        where_sql = self.build_where_sql(lat_less_than=lat_less_than,
                                         lat_greater_than=lat_greater_than,
                                         tb_11_minus_tb_12_limit=tb_11_minus_tb_12_limit,
                                         st_less_than=st_less_than,
                                         st_greater_than=st_greater_than,
                                         algorithm=algorithm)

        # Add the where string.
        if where_sql is not None and where_sql.strip() != "":
            sql += " WHERE %s" %(where_sql)

        # Add the limit.
        if limit is not None:
            sql += " LIMIT %i" % (limit)

        # Log the full sql string.
        LOG.debug(sql)

        # Get the results.
        for row in self.get_rows(sql):
            yield row


if __name__ == "__main__":
    with Db("/tmp/fisk.db") as db:
        for sql in sql_list:
            db.execute(sql)
