#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Built in.
import logging
LOG = logging.getLogger(__name__)
import datetime
import random
import multiprocessing
import glob
import os

# Third party
import numpy as np
import netCDF4
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import pylab

# Own.
import eustace.surface_temperature
import models.avhrr_hdf5
import eustace.coefficients
import eustace.db
import eustace.sigmas

def running_perturbations_in_multiprocessor(output):
    


def populate_from_files(database_filename, avhrr_filename, sun_sat_angle_filename, cloudmask_filename, number_of_perturbations):
    LOG.info("db_filename:          %s" % (database_filename))
    LOG.info("avhrr_filename:       %s" % (avhrr_filename))
    LOG.info("sunsatangle_filename: %s" % (sunsatangle_filename))
    LOG.info("cloudmask_filename:   %s" % (cloudmask_filename))

    with models.avhrr_hdf5.Hdf5(avhrr_filename,
                                sun_sat_angle_filename,
                                cloudmask_filename) as avhrr_model:
        LOG.info(avhrr_model)
        assert(avhrr_model.lat.shape == avhrr_model.lon.shape)
        resulting_st_K = np.ma.masked_all_like(avhrr_model.lat)

        sigmas = eustace.sigmas.get_sigmas(avhrr_model.satellite_id)
        LOG.info(sigmas)

        max_error = 0
        total_perturbed_st_count = 0
        parent_st_count = 0
        counter = 0
        started = 0

        random.seed(1)

        output_queue = multiprocessing.Queue()
        number_of_cpus = multiprocessing.cpu_count()

        start_time = datetime.datetime.now()
        with eustace.coefficients.Coefficients(avhrr_model.satellite_id) as coeff:
            ## Creating ramdisk:
            # mkdir /tmp/ramdisk
            #
            ## A 3Gb ram disk.
            # mount -t tmpfs -o size=3072m tmpfs /tmp/ramdisk
            #
            ## or
            #
            ## For a 12Gb ram disk.
            # mount -t tmpfs -o size=$((12 * 1024))m tmpfs /tmp/ramdisk
            with eustace.db.Db(database_filename) as db:

                # Rows.
                for row_index in np.arange(avhrr_model.lon.shape[0]):
                    # Some diagnostics while running.
                    LOG.info("ROW: %i.   total st_count: %i.   total_time: %s.   sts./sec: %f" % (row_index, total_perturbed_st_count, str(datetime.datetime.now() - start_time), (total_perturbed_st_count / (datetime.datetime.now() - start_time).total_seconds())))
                    # Cols.
                    for col_index in np.arange(avhrr_model.lon.shape[1]):
                        counter += 1

                        # Reading in the values.
                        cloudmask = avhrr_model.cloudmask[row_index, col_index] 
                        if cloudmask != 1 and cloudmask != 4:
                            LOG.debug("Bad cloudmask: %i" % (cloudmask))
                            continue

                        # T11 is channel 4.
                        t11_K = avhrr_model.ch4[row_index, col_index]

                        # T12 is channel 5.
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

                        # Missing climatology. Using t11_K in stead.
                        t_clim_K = t11_K

                        # Lat / lon.
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
                            cloudmask=int(avhrr_model.cloudmask[row_index, col_index]),
                            swath_datetime=avhrr_model.swath_datetime,
                            lat=float(lat),
                            lon=float(lon)
                            )

                        perturbations = eustace.surface_temperature.get_n_perturbed_temeratures(coeff,
                                                                                                number_of_perturbations,
                                                                                                t11_K,
                                                                                                t12_K,
                                                                                                t37_K,
                                                                                                t_clim_K,
                                                                                                sigmas["sigma_11"],
                                                                                                sigmas["sigma_12"],
                                                                                                sigmas["sigma_37"],
                                                                                                sun_zenit_angle,
                                                                                                sat_zenit_angle,
                                                                                                random_seed=counter)

                        for algorithm, epsilon_11, epsilon_12, epsilon_37, st_K in perturbations:
                            if np.isnan(st_K):
                                # No need to do more for this perturbation, if the output is not a number.
                                continue
                                
                            db.insert_perturbation_values(swath_input_id, algorithm,
                                                          epsilon_11 = epsilon_11,
                                                          epsilon_12 = epsilon_12,
                                                          epsilon_37 = epsilon_37,
                                                          surface_temp = st_K)
                            total_perturbed_st_count += 1

                        db.conn.commit()
                        parent_st_count += 1

            LOG.info("Counter %i" % (counter))
            LOG.info("Antal st'er: %i" % (total_perturbed_st_count))
            LOG.info("Antal parents: %i" % (parent_st_count))










if __name__ == "__main__":
    import docopt
    __doc__ = """
File: {filename}

Usage:
  {filename} <database-filename> (<satellite-id> [<data-directory>] | <avhrr-filename> <sunsatangle-filename> <cloudmask-filename>) [-d|-v] [options]
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help                         Show this screen.
  --version                         Show version.
  -v --verbose                      Show some diagostics.
  -d --debug                        Show some more diagostics.
  --number-of-perturbations=<NoP>   The number of perturbations per pixel, [default: 10].
  --result-directory=<directory>    Where to put the database after run.
""".format(filename=__file__)
    args = docopt.docopt(__doc__, version='0.1')
    if args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    LOG.info(args)

    number_of_perturbations = int(args["--number-of-perturbations"])

    if args["<satellite-id>"] is not None:
        LOG.info(args["<satellite-id>"])
        if args["<data-directory>"] is None:
            args["<data-directory>"] = os.path.curdir

        # Getting all avhrr files with satellite id in name from data directory.
        avhrr_files = glob.glob(os.path.join(args["<data-directory>"], "*%s*avhrr*" % (args["<satellite-id>"])))
        if len(avhrr_files) == 0:
            raise RuntimeException("No %s files in %s." % (args["<satellite-id>"], args["<data-directory>"]))

        for avhrr_filename in avhrr_files:
            file_id = avhrr_filename.rsplit("_", 1)[0]
            cloudmask_filename = "%s_cloudmask.h5" % file_id
            sunsatangle_filename = "%s_sunsatangles.h5" % file_id
            populate_from_files(args["<database-filename>"],
                                avhrr_filename,
                                sunsatangle_filename,
                                cloudmask_filename,
                                number_of_perturbations)
    else:
        populate_from_files(args["<database-filename>"],
                            args["<avhrr-filename>"],
                            args["<sunsatangle-filename>"],
                            args["<cloudmask-filename>"],
                            number_of_perturbations)

    if args["--result-directory"] is not None:
        LOG.info("Moving database '%s' filename to '%s'." % (args["<database-filename>"], args["--result-directory"]))
        if not os.path.isdir(args["--result-directory"]):
            raise RuntimeException("%s does not exist " % args["--result-directory"])

        os.rename(arg["<database-filename>"],
                  os.path.join(args["--result-directory"],
                               os.path.basename(arg["<database-filename>"])
                               )
                  )

