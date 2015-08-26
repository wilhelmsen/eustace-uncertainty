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

class ASST_ALGORITHM:
    DAY, NIGHT, TWILIGHT = range(3)

class SurfaceTemperatureAlgorithm:
    NOALGORITHM, SSTDAY, SSTNIGHT, SSTTWILIGHT, IST, MIZTSSTDAYIST, MIZTSSTNIGHTIST = range(7)

sst_algo=SurfaceTemperatureAlgorithm.NOALGORITHM

def steta(sat_zenit_angle):
    return 1.0 / np.cos(np.radians(sat_zenit_angle)) - 1.0

def surface_temperature(satellite_id, temp_11, temp_12, temp_37, sun_zenit_angle, sat_zenit_angle, ch3_data_exists):
    with coefficients.Coefficients(satellite_id) as c:
        print c

def validate_Ts(Ts, T11, T12):
    if (T11-T12) > 2.0:
        if 268.95 <= T11 and T11 < 270.95:
            return 141.0
        if T11 >= 270.95:
            return 142.0
    if Ts < T11:
        return 140
    if Ts < 150.0:
        return 144.0
    if Ts > 350.0:
        return 145.0
    return Ts

def select_asst_algorithm(sun_zenit_angle, ch3data_exist):
    if sun_zenit_angle <= 90 or not ch3data_exist:
        return ASST_ALGORITHM.DAY
    else:
        if sun_zenit_angle < 110:
            return ASST_ALGORITHM.TWILIGHT
        else:
            return ASST_ALGORITHM.NIGHT

def ist(coeff, T11, T12, s_teta):
    # IST split window algorithm from Key et al 1997
    a, b, c, d = coeff.get_coefficients(T11)
    return a + b * T11 + c * (T11 - T12) + d * ((T11 - T12) * s_teta)

def sst_day(c, T11, T12, s_teta, t_clim):
    # Arctic SST algorithm for 'day' and 'night' from PLBorgne 2010
    a_d, b_d, c_d, d_d, e_d, f_d, g_d = c.get_day_coefficients()
    return (a_d + b_d * s_teta) * (T11) + (c_d + d_d * s_teta + e_d * (t_clim)) * (T11-T12) + f_d + g_d * s_teta

def sst_night(c, T11, T12, T37, s_teta):
    a_n, b_n, c_n, d_n, e_n, f_n, cor_n = c.get_night_coefficients(s_teta)
    return (a_n + b_n * s_teta) * (T37) + (c_n + d_n * s_teta) * (T11 - T12) + e_n + f_n * s_teta + cor_n

def sst_twilight(c, sun_zenit_angle, T11, T12, T37, s_teta, t_clim):
    asst_night = sst_night(c, T11, T12, T37, s_teta)
    asst_day = sst_day(c, T11, T12, s_teta, t_clim)
    return ((sun_zenit_angle - 110) * (-0.05) * asst_day) + ((sun_zenit_angle - 90) * (0.05) * asst_night)

def get_asst(asst_algorithm, c, T11, T12, T37, sun_zenit_angle, t_clim):
    s_teta = steta(sun_zenit_angle)
    if asst_algorithm == ASST_ALGORITHM.DAY:
        return sst_day(c, T11, T12, s_teta, t_clim)
    elif asst_algorithm == ASST_ALGORITHM.TWILIGHT:
        return sst_twilight(c, sun_zenit_angle, T11, T12, T37, s_teta, t_clim)
    elif asst_algorithm == ASST_ALGORITHM.NIGHT:
        return sst_night(c, T11, T12, T37, s_teta)
    else:
        raise RuntimeError("Unknown asst algorithm.")

# GAC svarer til noaa
# ist svarer til s_nwc

if __name__ == "__main__":
    surface_temperature(args['<sat-id>'], 1, 1, 1, 1, 1, 1)

    asst_algorithm = select_asst_algorithm(sun_zenit_angle, ch3data_exist)
    asst = get_asst(asst_algorithm)
