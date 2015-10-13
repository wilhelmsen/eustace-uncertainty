#!/usr/bin/env python
# coding: utf-8
import logging
import eustace.coefficients
import numpy as np
import random

LOG = logging.getLogger(__name__)


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
    MIZT_SST_IST_DAY = "MIZT_SST_IST_DAY"
    MIZT_SST_IST_NIGHT = "MIZT_SST_IST_NIGHT"
    MIZT_SST_IST_TWILIGHT = "MIZT_SST_IST_TWILIGHT"


def sat_teta(sat_zenit_angle):
    """
    """
    return 1.0 / np.cos(np.radians(sat_zenit_angle)) - 1.0


def sanity_check_surface_temperature(t_surface, t11, t12):
    """
    Sanity checkking the surface temperature.
    I.e. if some conditions are not set, the output is set to different
    values outside the valid range.
    """
    if (t11 - t12) > 2.0:
        # The difference between t11 and t12 is too big.
        if 268.95 <= t11 and t11 < 270.95:
            # Indication that there might be ice fog.
            # return 141.0
            pass

        if t11 >= 270.95:
            # Indication that there might be ice fog.
            #return 142.0
            pass

    if t_surface < t11:
        # The surface temperature should not be greater than the T11
        return np.NaN # 140

    if t_surface < 150.0:
        # Surface temperature too low
        return np.NaN # 144.0

    if t_surface > 350.0:
        # Surface temperature too high.
        return np.NaN # 145.0

    # No unvalid conditions were met...
    return t_surface


def _get_day_state(sun_zenit_angle, t37):
    """
    Picks the state of the day, based on the angle.

    Outputs:
    Days, twilight, night.
    """
    if sun_zenit_angle <= 90 or t37 is None or np.isnan(t37):
        return DAY_STATE.DAY
    else:
        if sun_zenit_angle < 110:
            return DAY_STATE.TWILIGHT
        else:
            return DAY_STATE.NIGHT


def select_surface_temperature_algorithm(sun_zenit_angle, t11, t37):
    """
    Selects which algorithm to use for different conditions.
    """
    # Gets the state of the day. Possible outputs are day, night, twilight.
    day_state = _get_day_state(sun_zenit_angle, t37)

    if t11 >= 268.95 and t11 < 270.95:
        # MIZT - Transition zone between water and ice weighted mean SST-IST,
        # from Vincent et al 2008*/
        if day_state == DAY_STATE.DAY:
            return ST_ALGORITHM.MIZT_SST_IST_DAY
        elif ((day_state == DAY_STATE.NIGHT)):
            return ST_ALGORITHM.MIZT_SST_IST_NIGHT
        elif day_state == DAY_STATE.TWILIGHT:
            return ST_ALGORITHM.MIZT_SST_IST_TWILIGHT
        else:
            raise SstException("Missing day state for mizt sst ist...")
    elif t11 >= 270.95:
        # Arctic SST
        if day_state == DAY_STATE.DAY:
            return ST_ALGORITHM.SST_DAY
        elif day_state == DAY_STATE.NIGHT:
            return ST_ALGORITHM.SST_NIGHT
        elif day_state == DAY_STATE.TWILIGHT:
            return ST_ALGORITHM.SST_TWILIGHT
        else:
            raise SstException("Missing day state for arctic sst...")
    else:
        # IST
        return ST_ALGORITHM.IST


def get_surface_temperature(st_algorithm, coeff, t11, t12, t37, t_clim,
                            sun_zenit_angle, sat_zenit_angle):
    """
    Get the surface temperature for a specific algorithm.

    Algorithm used for the different conditions.

             DAY        TWILIGHT       NIGHT
         +----------+---------------+------------+
     SST | SST_DAY  | SST_TWILIGHT  | SST_NIGHT  |
         +----------+---------------+------------+
    MIZT | MIZT_DAY | MIZT_TWILIGHT | MIZT_NIGHT |
         +----------+---------------+------------+
     IST |                 IST                   |
         +---------------------------------------+
    """
    s_teta = sat_teta(sat_zenit_angle)
    st = None

    if st_algorithm == ST_ALGORITHM.SST_DAY:
        st = sea_surface_temperature_day(coeff, t11, t12, t_clim, s_teta)

    elif st_algorithm == ST_ALGORITHM.SST_NIGHT:
        st = sea_surface_temperature_night(coeff, t11, t12, t37, s_teta)

    elif st_algorithm == ST_ALGORITHM.SST_TWILIGHT:
        st = sea_surface_temperature_twilight(coeff, t11, t12, t37, t_clim,
                                                s_teta, sun_zenit_angle)

    elif st_algorithm == ST_ALGORITHM.IST:
        st = ice_surface_temperature(coeff, t11, t12, s_teta)

    elif st_algorithm == ST_ALGORITHM.MIZT_SST_IST_DAY:
        st= marginal_ice_zone_temperature_day(coeff, t11, t12, t_clim,
                                                 s_teta)

    elif st_algorithm == ST_ALGORITHM.MIZT_SST_IST_NIGHT:
        st = marginal_ice_zone_temperature_night(coeff, t11, t12, t37,
                                                   s_teta)

    elif st_algorithm == ST_ALGORITHM.MIZT_SST_IST_TWILIGHT:
        st = marginal_ice_zone_temperature_twilight(coeff, t11, t12, t37,
                                                      t_clim, s_teta,
                                                      sun_zenit_angle)
    else:
        raise SstException("Unknown sst algorithm, '%s'." % (str(st_algorithm)))

    return sanity_check_surface_temperature(st, t11, t12)
    


def ice_surface_temperature(coeff, t11, t12, s_teta):
    """
    Ice Surface Temperature algorithm
    IST split window algorithm from Key et al 1997.
    """
    a, b, c, d = coeff.get_ist_coefficients(t11)
    return a + b * t11 + c * (t11 - t12) + d * ((t11 - t12) * s_teta)


def marginal_ice_zone_temperature_day(coeff, t11, t12, t_clim, s_teta):
    """
    See marginal_ice_zone_temperature.
    Using the night version of the sea surface temperature.
    """
    sst = sea_surface_temperature_day(coeff, t11, t12, t_clim, s_teta)
    return marginal_ice_zone_temperature(coeff, t11, t12, sst, s_teta)


def marginal_ice_zone_temperature_night(coeff, t11, t12, t37, s_teta):
    """
    See marginal_ice_zone_temperature.
    Using the night version of the sea surface temperature.
    """
    sst = sea_surface_temperature_night(coeff, t11, t12, t37, s_teta)
    return marginal_ice_zone_temperature(coeff, t11, t12, sst, s_teta)


def marginal_ice_zone_temperature(coeff, t11, t12, sst, s_teta):
    """
    Marginal Ice Zone Temperature algorithm:
    sst and ist scaled linearly - relative to T11 in range 268.95K - 270.95K
    """
    ist = ice_surface_temperature(coeff, t11, t12, s_teta)
    return ((t11 - 270.95) * (-0.5) * ist) + ((t11 - 268.95) * 0.5 * sst)


def marginal_ice_zone_temperature_twilight(coeff, t11, t12, t37, t_clim, s_teta,
                                           sun_zenit_angle):
    mizt_day   = marginal_ice_zone_temperature_day(coeff, t11, t12, t_clim, s_teta)
    mizt_night = marginal_ice_zone_temperature_night(coeff, t11, t12, t37, s_teta)
    return surface_temperature_twilight(mizt_day, mizt_night, sun_zenit_angle)


def sea_surface_temperature_day(coeff, t11, t12, t_clim, s_teta):
    """
    Sea Surface Temperature day algorithm.

    Arctic SST algorithm for 'day' and 'night' from PLBorgne 2010
    """
    a_d, b_d, c_d, d_d, e_d, f_d, g_d = coeff.get_sst_day_coefficients()
    return (
        (a_d + b_d * s_teta) * (t11)
        + (c_d + d_d * s_teta + e_d * (t_clim)) * (t11 - t12)
        + f_d
        + g_d * s_teta
        )


def sea_surface_temperature_night(coeff, t11, t12, t37, s_teta):
    """
    Sea Surface Temperature night algorithm.
    """
    # If t37 is zero, we should never have gone in here...
    # Then something is wrong in the selection process.
    assert(t37 is not None and not np.isnan(t37))
    a_n, b_n, c_n, d_n, e_n, f_n, cor_n \
        = coeff.get_sst_night_coefficients(s_teta)
    return (
        (a_n + b_n * s_teta) * (t37)
        + (c_n + d_n * s_teta) * (t11 - t12)
        + e_n
        + f_n * s_teta
        + cor_n
        )


def sea_surface_temperature_twilight(coeff, t11, t12, t37, t_clim, s_teta,
                                     sun_zenit_angle):
    """
    Sea Surface Temperature twilight algorithm:
    sstday and sstnight scaled linearly between - relative to sunzen-angle.
    """
    sst_night = sea_surface_temperature_night(coeff, t11, t12, t37, s_teta)
    sst_day = sea_surface_temperature_day(coeff, t11, t12, t_clim, s_teta)
    return surface_temperature_twilight(sst_day, sst_night, sun_zenit_angle)


def surface_temperature_twilight(st_day, st_night, sun_zenit_angle):
    return (
        ((sun_zenit_angle - 110) * (-0.05) * st_day)
        + ((sun_zenit_angle - 90) * (0.05) * st_night)
        )


def get_n_perturbed_temeratures(coeff, number_of_perturbations, t11_K, t12_K, t37_K, t_clim_K, sigma_11, sigma_12, sigma_37, sat_zenit_angle, sun_zenit_angle, random_seed=None):
    """
    Getting n number of perturbed temperatures.
    Runs through a gauss with the temperature as mean and sigma as std.
    """
    if random_seed is not None:
        # Set the seed if given.
        random.seed(random_seed)

    perturbations = []
    for i in range(number_of_perturbations):
        # Calculate the gauss.
        perturbed_t11_K = random.gauss(t11_K, sigma_11)
        perturbed_t12_K = random.gauss(t12_K, sigma_12)
        perturbed_t37_K = random.gauss(t37_K, sigma_37) \
            if np.isnan(t37_K) else np.NaN
    
        # Pick algorithm for the perturbed value.
        algorithm = eustace.surface_temperature.select_surface_temperature_algorithm(
            sun_zenit_angle,
            perturbed_t11_K,
            perturbed_t37_K)

        # Calculate the perturbed temperature.
        st_K = eustace.surface_temperature.get_surface_temperature(algorithm,
                                                                   coeff,
                                                                   perturbed_t11_K,
                                                                   perturbed_t12_K,
                                                                   perturbed_t37_K,
                                                                   t_clim_K,
                                                                   sun_zenit_angle,
                                                                   sat_zenit_angle)
        # Append the result to the list of permutations.
        perturbations.append((algorithm,
                              perturbed_t11_K-t11_K, # epsilon_11,
                              perturbed_t12_K-t12_K, # epsilon_12,
                              perturbed_t37_K-t37_K, # epsilon_37,
                              st_K))
    return perturbations







# GAC svarer til noaa
# ist svarer til s_nwc
if __name__ == "__main__":
    satellite_id = "noaa7"
    t11 = 262
    t12 = 261
    t37 = 261
    t_clim = 261
    sat_zenit_angle = 20
    sun_zenit_angle = 20

    t11 = 261
    t37 = None
    assert(select_surface_temperature_algorithm(sun_zenit_angle, t11, t37)
           == ST_ALGORITHM.IST)

    t11 = 271
    t37 = None
    assert(select_surface_temperature_algorithm(sun_zenit_angle, t11, t37)
           == ST_ALGORITHM.SST_DAY)

    t11 = 269
    t37 = np.NaN
    assert(select_surface_temperature_algorithm(sun_zenit_angle, t11, t37)
           == ST_ALGORITHM.MIZT_SST_IST_DAY)

    t11 = t12
    t37 = t12
    with eustace.coefficients.Coefficients(satellite_id) as coeff:
        print get_surface_temperature(ST_ALGORITHM.IST, coeff, t11, t12, t37,
                                      t_clim, sun_zenit_angle, sat_zenit_angle)
        print get_surface_temperature(ST_ALGORITHM.SST_DAY, coeff, t11, t12,
                                      t37, t_clim, sun_zenit_angle,
                                      sat_zenit_angle)
        print get_surface_temperature(ST_ALGORITHM.MIZT_SST_IST_DAY, coeff,
                                      t11, t12, t37, t_clim, sun_zenit_angle,
                                      sat_zenit_angle)
        print get_surface_temperature(ST_ALGORITHM.SST_NIGHT, coeff, t11, t12,
                                      t37, t_clim, sun_zenit_angle,
                                      sat_zenit_angle)
        print get_surface_temperature(ST_ALGORITHM.MIZT_SST_IST_NIGHT, coeff,
                                      t11, t12, t37, t_clim, sun_zenit_angle,
                                      sat_zenit_angle)
