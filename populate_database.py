#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Built in.
import logging
LOG = logging.getLogger(__name__)
import datetime
import random
import multiprocessing

# Third party
import numpy as np
import netCDF4
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import pylab

# Own.
import eustace.surface_temperature
import models.avhrr_hdf5
import coefficients
import eustace.db


if __name__ == "__main__":
    import docopt
    __doc__ = """
File: {filename}

Usage:
  {filename} <database_filename> <avhrr-filename> <sunsatangle-filename> <cloudmask-filename> [-d|-v] [options]
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help                         Show this screen.
  --version                         Show version.
  -v --verbose                      Show some diagostics.
  -d --debug                        Show some more diagostics.
  --number-of-perturbations = NoP   The number of perturbations per pixel, [default: 10].
""".format(filename=__file__)
    args = docopt.docopt(__doc__, version='0.1')
    print args
    if args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    LOG.info(args)

    with models.avhrr_hdf5.Hdf5(args["<avhrr-filename>"],
                                args["<sunsatangle-filename>"],
                                args["<cloudmask-filename>"]) as avhrr_model:
        print avhrr_model
        assert(avhrr_model.lat.shape == avhrr_model.lon.shape)
        resulting_st_K = np.ma.masked_all_like(avhrr_model.lat)

        sigma_1 = 0.12
        sigma_2 = 0.12
        sigma_3 = 0.12

        max_error = 0
        total_st_count = 0
        parent_st_count = 0
        counter = 0
        started = 0

        random.seed(1)

        output_queue = multiprocessing.Queue()
        
        start_time = datetime.datetime.now()
        with coefficients.Coefficients(avhrr_model.satellite_id) as coeff:
            # Creating ramdisk:
            # mkdir /tmp/ramdisk
            # mount -t tmpfs -o size=2048m tmpfs /tmp/ramdisk
            with eustace.db.Db(args["<database_filename>"] ) as db:
                for row_index in np.arange(avhrr_model.lon.shape[0]):
                    print "ROW:", row_index, "st_count", total_st_count, "time", datetime.datetime.now() - start_time,\
                        "st. pr. seconds", total_st_count / (datetime.datetime.now() - start_time).total_seconds()
                    for col_index in np.arange(avhrr_model.lon.shape[1]):
                        counter += 1

                        cloud_mask = avhrr_model.cloud_mask[row_index, col_index] 
                        if cloud_mask != 1 and cloud_mask != 4:
                            LOG.info("Bad cloudmask: %i" % (cloudmask))
                            continue

                        # T11 is channel 4.
                        t11_K = avhrr_model.ch4[row_index, col_index]

                        # T11 is channel 5.
                        t12_K = avhrr_model.ch5[row_index, col_index]

                        # T37 is channel 3b.
                        t37_K = avhrr_model.ch3b[row_index, col_index]

                        if np.isnan(t11_K) or np.isnan(t12_K):
                            # t11 and t12 are both needed for all calculations.
                            # Is something wrong if they are both missing?
                            # Consider what to do.
                            raise RuntimeException("Missing T11 or T12")

                        # Angles.
                        sun_zenit_angle = float(avhrr_model.sun_zenit_angle[row_index, col_index])
                        sat_zenit_angle = float(avhrr_model.sat_zenit_angle[row_index, col_index])

                        # Missing climatology
                        t_clim_K = t11_K

                        lat = avhrr_model.lat[row_index, col_index]
                        lon = avhrr_model.lon[row_index, col_index]
                        if lat is None or np.isnan(lat) or lon is None or np.isnan(lon):
                            continue

                        # Pick algorithm.
                        algorithm = eustace.surface_temperature.select_surface_temperature_algorithm(
                            sun_zenit_angle,
                            t11_K,
                            t37_K)

                        # Calculate the temperature.
                        st_truth_K = eustace.surface_temperature.get_surface_temperature(algorithm,
                                                                                         coeff,
                                                                                         t11_K,
                                                                                         t12_K,
                                                                                         t37_K,
                                                                                         t_clim_K,
                                                                                         sun_zenit_angle,
                                                                                         sat_zenit_angle)

                        if np.isnan(st_truth_K):
                            # No need to do more for this pixel, if the output is not a number.
                            continue

                        swath_input_id = db.insert_swath_values(
                            str(avhrr_model.satellite_id),
                            surface_temp=st_truth_K, # float(true_st_K),
                            t_11=float(t11_K),
                            t_12=float(t12_K),
                            sat_zenit_angle=sat_zenit_angle,
                            sun_zenit_angle=sun_zenit_angle,
                            cloud_mask=int(avhrr_model.cloudmask[row_index, col_index]),
                            swath_datetime=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            lat=float(lat),
                            lon=float(lon)
                            )
                        
                        
                        # Do the perturbations...
                        for i in range(int(args["--number-of-perturbations"])):
                            perturbed_t11_K = random.gauss(t11_K, sigma_1)
                            perturbed_t12_K = random.gauss(t12_K, sigma_2)
                            perturbed_t37_K = random.gauss(t37_K, sigma_3) \
                                if np.isnan(t37_K) else np.NaN
                            
                            # Pick algorithm.
                            algorithm = eustace.surface_temperature.select_surface_temperature_algorithm(
                                sun_zenit_angle,
                                perturbed_t11_K,
                                perturbed_t37_K)

                            # Calculate the temperature.
                            st_K = eustace.surface_temperature.get_surface_temperature(algorithm,
                                                                                       coeff,
                                                                                       perturbed_t11_K,
                                                                                       perturbed_t12_K,
                                                                                       perturbed_t37_K,
                                                                                       t_clim_K,
                                                                                       sun_zenit_angle,
                                                                                       sat_zenit_angle)

                            if np.isnan(st_K):
                                # No need to do more for this pixel, if the output is not a number.
                                continue

                            db.insert_perturbation_values(swath_input_id, algorithm,
                                                          epsilon_11 = float(perturbed_t11_K-t11_K),
                                                          epsilon_12 = float(perturbed_t12_K-t12_K),
                                                          epsilon_37 = float(perturbed_t37_K-t37_K),
                                                          surface_temp = st_K)
                            total_st_count += 1

                        db.conn.commit()
                        parent_st_count += 1

            print "Antal lat/lon:", counter
            print "Antal st'er:", total_st_count
            print "Antal parents:", parent_st_count
