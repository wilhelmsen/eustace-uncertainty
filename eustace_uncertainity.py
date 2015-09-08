#!/usr/bin/env python
# coding: utf-8
__doc__ = """Eustace uncertainity

Usage:
  {filename} <sun-sat-angles-filename> [--speed=<kn>] [-d|-v] [options]

Options:
  -h --help                   Show this screen.
  --version                   Show version.
  -d, --debug                 Output a lot of info..
  -v, --verbose               Output less less info.
  --log-filename=logfilename  Name of the log file.
""".format(filename=__file__)
import logging
import docopt
import coefficients
import numpy as np
import surface_temperature
import h5py


LOG = logging.getLogger(__name__)
args = docopt.docopt(__doc__, version="1.0")

if args["--debug"]:
    logging.basicConfig(filename=args["--log-filename"], level=logging.DEBUG)
elif args["--verbose"]:
    logging.basicConfig(filename=args["--log-filename"], level=logging.INFO)
else:
    logging.basicConfig(filename=args["--log-filename"], level=logging.WARNING)
LOG.debug(args)


def get_sat_id_from_hdf5_file(filename):
    f = h5py.File(filename)
    try:
        return f['how'].attrs['platform']
    finally:
        f.close()
    

def get_hdf5_values(filename, key, str_key):
    f = h5py.File(filename)
    try:
        assert(f["%s/what"%(key)].attrs['product'] == str_key)
        gain = f["%s/what"%(key)].attrs["gain"]
        offset = f["%s/what"%(key)].attrs["offset"]
        return f["%s/data"%(key)].value[0][0]*gain + offset
    finally:
        f.close()


if __name__ == "__main__":
    # satellite_id = args["<sat-id>"]
    sun_sat_angle_filename = args['<sun-sat-angles-filename>']
    satellite_id = get_sat_id_from_hdf5_file(sun_sat_angle_filename)

    # Sun zenit angle:
    key = "image1"
    sun_zenit_angle = get_hdf5_values(sun_sat_angle_filename, "image1", "SUNZ")
    print sun_zenit_angle
    sat_zenit_angle = get_hdf5_values(sun_sat_angle_filename, "image2", "SATZ")
    print sat_zenit_angle
    sys.exit()

    # t11 svarer til ch4
    # t12 svarer til ch5
    # t37 svarer til ch3b
    
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
