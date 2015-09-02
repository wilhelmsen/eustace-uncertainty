#!/usr/bin/env python
# coding: utf-8
__doc__ = """Eustace uncertainity

Usage:
  eustace_uncertainity.py <sat-id> <data-filename> """ +
"""[--speed=<kn>] [-d|-v] [options]

Options:
  -h --help                   Show this screen.
  --version                   Show version.
  -d, --debug                 Output a lot of info..
  -v, --verbose               Output less less info.
  --log-filename=logfilename  Name of the log file.
"""
import logging
import docopt
import coefficients
import numpy as np
import surface_temperature

LOG = logging.getLogger(__name__)
args = docopt.docopt(__doc__, version="1.0")

if args["--debug"]:
    logging.basicConfig(filename=args["--log-filename"], level=logging.DEBUG)
elif args["--verbose"]:
    logging.basicConfig(filename=args["--log-filename"], level=logging.INFO)
else:
    logging.basicConfig(filename=args["--log-filename"], level=logging.WARNING)
LOG.debug(args)

if __name__ == "__main__":
    satellite_id = args["<sat-id>"]
    t11 = 262
    t12 = 261
    t37 = 261
    t_clim = 261
    sat_zenit_angle = 20
    sun_zenit_angle = 20

    t11 = 261
    t37 = None
    assert(surface_temperature.select_surface_temperature_algorithm(
            sun_zenit_angle, t11, t37) == surface_temperature.ST_ALGORITHM.IST)

    t11 = 271
    t37 = None
    assert(surface_temperature.select_surface_temperature_algorithm(
            sun_zenit_angle, t11, t37) ==
           surface_temperature.ST_ALGORITHM.SST_DAY)

    t11 = 269
    t37 = None
    assert(surface_temperature.select_surface_temperature_algorithm(
            sun_zenit_angle, t11, t37) ==
           surface_temperature.ST_ALGORITHM.MIZT_SST_IST_DAY)

    t11 = t12
    t37 = t12
    with coefficients.Coefficients(satellite_id) as coeff:
        print surface_temperature.get_surface_temperature(
            surface_temperature.ST_ALGORITHM.IST, coeff, t11, t12, t37,
            t_clim, sun_zenit_angle, sat_zenit_angle)
        print surface_temperature.get_surface_temperature(
            surface_temperature.ST_ALGORITHM.SST_DAY, coeff, t11, t12, t37,
            t_clim, sun_zenit_angle, sat_zenit_angle)
        print surface_temperature.get_surface_temperature(
            surface_temperature.ST_ALGORITHM.MIZT_SST_IST_DAY, coeff, t11,
            t12, t37, t_clim, sun_zenit_angle, sat_zenit_angle)
        print surface_temperature.get_surface_temperature(
            surface_temperature.ST_ALGORITHM.SST_NIGHT, coeff, t11, t12,
            t37, t_clim, sun_zenit_angle, sat_zenit_angle)
        print surface_temperature.get_surface_temperature(
            surface_temperature.ST_ALGORITHM.MIZT_SST_IST_NIGHT, coeff, t11,
            t12, t37, t_clim, sun_zenit_angle, sat_zenit_angle)
