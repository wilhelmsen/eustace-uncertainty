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

class SstException(Exception):
    pass

class DAY_STATE:
    DAY = "DAY"
    NIGHT = "NIGHT"
    TWILIGHT = "TWILIGHT"

class ST_ALGORITHM:
    SST_DAY = "SST_DAY"
    SST_NIGHT = "SST_NIGHT"
    SST_TWILIGHT = "SST_TWILIGHT"
    IST = "IST"
    MIZT_SST_DAY_IST = "MIZT_SST_DAY_IST"
    MIZT_SST_NIGHT_IST = "MIZT_SST_NIGHT_IST"

def sat_teta(sat_zenit_angle):
    return 1.0 / np.cos(np.radians(sat_zenit_angle)) - 1.0

def validate_surface_temperature(ts, t11, t12):
    if (t11) > 2.0:
        if 268.95 <= t11 and t11 < 270.95:
            return 141.0
        if t11 >= 270.95:
            return 142.0
    if ts < t11:
        return 140
    if ts < 150.0:
        return 144.0
    if ts > 350.0:
        return 145.0
    return ts


def select_day_state(sun_zenit_angle, t37):
    if sun_zenit_angle <= 90 or t37 is None:
        return DAY_STATE.DAY
    else:
        if sun_zenit_angle < 110:
            return DAY_STATE.TWILIGHT
        else:
            return DAY_STATE.NIGHT


def select_surface_temperature_algorithm(sun_zenit_angle, t11, t37):
    day_state = select_day_state(sun_zenit_angle, t37)

    if t11 >= 268.95 and t11 < 270.95:
        # MIZT - Transition zone between water and ice weighted mean SST-IST, from Vincent et al 2008*/
        if day_state == DAY_STATE.DAY:
            return ST_ALGORITHM.MIZT_SST_DAY_IST
        elif ((day_state == DAY_STATE.NIGHT)):
            return ST_ALGORITHM.MIZT_SST_NIGHT_IST
        else:
            raise SstException("Missing sst state for mizt...")
    elif t11 >= 270.95:
        # Arctic SST
        if day_state == DAY_STATE.DAY:
            return ST_ALGORITHM.SST_DAY
        elif day_state == DAY_STATE.NIGHT:
            return ST_ALGORITHM.SST_NIGHT
        elif day_state == DAY_STATE.TWILIGHT:
            return ST_ALGORITHM.SST_TWILIGHT
        else:
            raise SstException("Missing sst state for arctic sst...")
    else:
        # IST
        return ST_ALGORITHM.IST


def get_surface_temperature(st_algorithm, coeff, t11, t12, t37, sun_zenit_angle, s_teta, t_clim):
    if st_algorithm == ST_ALGORITHM.SST_DAY:
        return sea_surface_temperature_day(coeff, t11, t12, s_teta, t_clim)

    if st_algorithm == ST_ALGORITHM.SST_NIGHT:
        return sea_surface_temperature_night(coeff, t11, t12, t37, s_teta)

    if st_algorithm == ST_ALGORITHM.SST_TWILIGHT:
        sst_night = sea_surface_temperature_night(coeff, T11, T12, T37, s_teta)
        sst_day = sea_surface_temperature_day(coeff, T11, T12, s_teta, t_clim)
        return sst_twilight(sun_zenit_angle, sst_day, sst_night)

    # All the following contain ist.
    ist = ice_surface_temperature(coeff, t11, t12, s_teta)
    if st_algorithm == ST_ALGORITHM.IST:
        return ist

    if st_algorithm == ST_ALGORITHM.MIZT_SST_DAY_IST:
        sst = sea_surface_temperature_day(coeff, t11, t12, s_teta, t_clim)
        return marginal_ice_zone_temperature(t11, ist, sst)

    if st_algorithm == ST_ALGORITHM.MIZT_SST_NIGHT_IST:
        sst = sea_surface_temperature_night(coeff, t11, t12, t37, s_teta)
        return marginal_ice_zone_temperature(t11, ist, sst)

    raise SstException("Unknown sst algorithm, '%s'."%(str(st_algorithm)))


def ice_surface_temperature(coeff, t11, t12, s_teta):
    # IST split window algorithm from Key et al 1997
    a, b, c, d = coeff.get_ist_coefficients(t11)
    return a + b * t11 + c * (t11 - t12) + d * ((t11 - t12) * s_teta)

def marginal_ice_zone_temperature(t11, ist, sst):
    #Marginal Ice Zone Temperature
    return ((t11 - 270.95) * (-0.5) * ist) + ((t11 - 268.95) * 0.5 * sst)

def sea_surface_temperature_day(coeff, T11, T12, s_teta, t_clim):
    # Arctic SST algorithm for 'day' and 'night' from PLBorgne 2010
    a_d, b_d, c_d, d_d, e_d, f_d, g_d = coeff.get_sst_day_coefficients()
    return (a_d + b_d * s_teta) * (T11) + (c_d + d_d * s_teta + e_d * (t_clim)) * (T11-T12) + f_d + g_d * s_teta

def sea_surface_temperature_night(coeff, T11, T12, T37, s_teta):
    a_n, b_n, c_n, d_n, e_n, f_n, cor_n = coeff.get_sst_night_coefficients(s_teta)
    return (a_n + b_n * s_teta) * (T37) + (c_n + d_n * s_teta) * (T11 - T12) + e_n + f_n * s_teta + cor_n

def sea_surface_temperature_twilight(sun_zenit_angle, sst_day, sst_night):
    return ((sun_zenit_angle - 110) * (-0.05) * sst_day) + ((sun_zenit_angle - 90) * (0.05) * sst_night)

# GAC svarer til noaa
# ist svarer til s_nwc

if __name__ == "__main__":
    satellite_id = args['<sat-id>']
    t11 = 262
    t12 = 261
    t37 = 261 
    sat_zenit_angle = 20

    t11 = 261; t37 = None; sun_zenit_angle = 20
    assert(select_surface_temperature_algorithm(sun_zenit_angle, t11, t37) == ST_ALGORITHM.IST)

    t11 = 271; t37 = None; sun_zenit_angle = 20
    assert(select_surface_temperature_algorithm(sun_zenit_angle, t11, t37) == ST_ALGORITHM.SST_DAY)

    t11 = 269; t37 = None; sun_zenit_angle = 20
    assert(select_surface_temperature_algorithm(sun_zenit_angle, t11, t37) == ST_ALGORITHM.MIZT_SST_DAY_IST)
    
    s_teta = sat_teta(sat_zenit_angle)
    t_clim = 261
    with coefficients.Coefficients(satellite_id) as c:
        print get_surface_temperature(ST_ALGORITHM.MIZT_SST_DAY_IST, c, t11, t12, t37, sun_zenit_angle, s_teta, t_clim)
