#!/usr/bin/env python
# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.gridspec
import pylab
import eustace.db
import eustace.surface_temperature
import numpy as np
import logging
import datetime
import os

LOG = logging.getLogger(__name__)

_ALGORITHMS = [eustace.surface_temperature.ST_ALGORITHM.SST_DAY,
               eustace.surface_temperature.ST_ALGORITHM.SST_NIGHT,
               eustace.surface_temperature.ST_ALGORITHM.SST_TWILIGHT,
               eustace.surface_temperature.ST_ALGORITHM.IST,
               eustace.surface_temperature.ST_ALGORITHM.IST + "_GT_260",
               eustace.surface_temperature.ST_ALGORITHM.IST + "_LT_240",
               eustace.surface_temperature.ST_ALGORITHM.IST + "_GT_240_LT_260",
               eustace.surface_temperature.ST_ALGORITHM.MIZT_SST_IST_DAY,
               eustace.surface_temperature.ST_ALGORITHM.MIZT_SST_IST_NIGHT,
               eustace.surface_temperature.ST_ALGORITHM.MIZT_SST_IST_TWILIGHT]

if __name__ == "__main__":
    import docopt
    __doc__ = """
File: {filename}

Usage:
  {filename} <database-filename> [-d|-v] [--output-dir=<output-dir>] [options]
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help                  Show this screen.
  --version                  Show version.
  -v --verbose               Show some diagostics.
  -d --debug                 Show some more diagostics.
  --limit=limit              Limit the number of pixels to get from the database.
  --lat-lt=<lat>             Include lats less than.
  --lat-gt=<lat>             Include lats greater than.
  --t11-t12-limit=<limit>    Only include values where t_11 - t12 is less than this value.
  --algorithm=<algo>         Only include values calculated with the given algorithm. Must be one of '{algorithms}'.
  --output-dir=<output-dir>  Output directory, [default: .].
""".format(filename=__file__, algorithms="', '".join(_ALGORITHMS))
    args = docopt.docopt(__doc__, version='0.1')
    if args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    LOG.info(args)

    limit = None if args["--limit"] is None else int(args["--limit"])
    if args["--algorithm"] is not None:
        assert(args["--algorithm"] in _ALGORITHMS)
        algorithms = [args["--algorithm"],]
    else:
        algorithms = _ALGORITHMS

    satellite_id = os.path.basename(args["<database-filename>"]).replace(".sqlite3", "")
    output_filename = os.path.abspath(os.path.join(args["--output-dir"], satellite_id + ".stat"))

    if os.path.isfile(output_filename):
        LOG.info("Removing %s" % (output_filename))
        os.remove(output_filename)

    with open(output_filename, "a") as fp:
        fp.write("# %s\n" % (satellite_id))
        fp.write("# algo avg std N\n")
    
    with eustace.db.Db(args["<database-filename>"]) as db:
        for algorithm in algorithms:
            LOG.debug("Get the values from the database.")
            t = datetime.datetime.now()
            if algorithm == eustace.surface_temperature.ST_ALGORITHM.IST + "_LT_240":
                st_less_than = 240
                st_greater_than = None
                algo = eustace.surface_temperature.ST_ALGORITHM.IST
            elif algorithm == eustace.surface_temperature.ST_ALGORITHM.IST + "_GT_260":
                st_greater_than = 260
                st_less_than = None
                algo = eustace.surface_temperature.ST_ALGORITHM.IST
            elif algorithm == eustace.surface_temperature.ST_ALGORITHM.IST + "_GT_240_LT_260":
                st_less_than = 260
                st_greater_than = 240
                algo = eustace.surface_temperature.ST_ALGORITHM.IST
            else:
                st_less_than = None
                st_greater_than = None
                algo = algorithm

            y_array = np.array([row[0] for row in db.get_perturbed_values(swath_variables=None,
                                                                          lat_less_than=args["--lat-lt"],
                                                                          lat_greater_than=args["--lat-gt"],
                                                                          tb_11_minus_tb_12_limit=args["--t11-t12-limit"],
                                                                          st_less_than=st_less_than,
                                                                          st_greater_than=st_greater_than,
                                                                          algorithm=algo,
                                                                          limit=limit)])
            LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))

            # Number of samples - total.
            LOG.info("Number of samples: %i." %(len(y_array)))

            # Make sure that there are no nan in the array.
            y_array_is_not_nan = y_array[~np.isnan(y_array)]

            # Number of samples.
            LOG.info("Number of samples without NaN: %i." %(len(y_array_is_not_nan)))

            LOG.debug("Calculating the average.")
            average_all = np.average(y_array_is_not_nan)

            LOG.debug("Calculating the standard deviation.")
            std_all = np.std(y_array_is_not_nan)

            with open(output_filename, "a") as fp:
                print ("%s %f %f %i\n" % (algorithm, average_all, std_all, len(y_array_is_not_nan)))
                fp.write("%s %f %f %i\n" % (algorithm, average_all, std_all, len(y_array_is_not_nan)))
                LOG.debug("Writing to %s" % (output_filename))
            LOG.debug("Written to %s" % (output_filename))
