#!/usr/bin/env python
# coding: utf-8
__doc__="""Eustace uncertainity

Usage:
  eustace_uncertainity.py <sat-id> <data-filename> [--speed=<kn>] [-d|-v] [options]

Options:
  -h --help                   Show this screen.
  --version                   Show version.
  -d, --debug                 Output a lot of info..
  -v, --verbose               Output less less info.
  --log-filename=logfilename  Name of the log file.
"""
import logging
import docopt
import math
import coefficients
import numpy as np

LOG = logging.getLogger(__name__)
args = docopt.docopt(__doc__, version="1.0")

if args["--debug"]:
    logging.basicConfig( filename=args["--log-filename"], level=logging.DEBUG )
elif args["--verbose"]:
    logging.basicConfig( filename=args["--log-filename"], level=logging.INFO )
else:
    logging.basicConfig( filename=args["--log-filename"], level=logging.WARNING )
LOG.debug(args)

DEGREE_2_RADIANS = 2*math.pi/360.0
ABS_ZERO=273.15


class SST_State:
    NOSTATE, DAY, NIGHT, TWILIGHT = range(4)

class SurfaceTemperatureAlgorithm:
    NOALGORITHM, SSTDAY, SSTNIGHT, SSTTWILIGHT, IST, MIZTSSTDAYIST, MIZTSSTNIGHTIST = range(7)

sst_algo=SurfaceTemperatureAlgorithm.NOALGORITHM


def surface_temperature(satellite_id, temp_37, temp_11, temp_12, sun_zenit_angle, sat_zenit_angle, ch3_data_exists):
    with coefficients.Coefficients(satellite_id) as c:
        steta = 1.0 / np.cos(np.radians(sat_zenit_angle)) - 1.0
        cor_n = c.gain_sst_night * steta + c.offset_sst_night


if __name__ == "__main__":
    surface_temperature(args['<sat-id>'], 1, 1, 1, 1, 1, 1)
