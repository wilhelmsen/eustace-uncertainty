#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Built in.
import logging
LOG = logging.getLogger(__name__)
import multiprocessing

# Third party
import numpy as np
import netCDF4
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import pylab
# Own.
import surface_temperature
import models.avhrr_hdf5
import coefficients

def calculate_sst(queue, row_index, col_index, t11_K, t12_K, t37_K, t_clim_K, sun_zenit_angle, sat_zenit_angle, coeff):
    algorithm = surface_temperature.select_surface_temperature_algorithm(
        sun_zenit_angle,
        t11_K,
        t37_K)
    st = surface_temperature.get_surface_temperature(algorithm,
                                                     coeff,
                                                     t11_K,
                                                     t12_K,
                                                     t37_K,
                                                     t_clim_K,
                                                     sun_zenit_angle,
                                                     sat_zenit_angle)
    queue.put([row_index, col_index, algorithm, st])
    

if __name__ == "__main__":
    import docopt
    __doc__ = """
File: {filename}

Usage:
  {filename} <truth-filename> <avhrr-filename> <sunsatangle-filename> <cloudmask-filename> [-d|-v]
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  -v --verbose  Show some diagostics.
  -d --debug    Show some more diagostics.
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
    

    ZERO_C_IN_K = 273.15
    nc_file = netCDF4.Dataset(args["<truth-filename>"])
    try:
        with models.avhrr_hdf5.Hdf5(args["<avhrr-filename>"],
                                    args["<sunsatangle-filename>"],
                                    args["<cloudmask-filename>"]) as avhrr_model:
            print avhrr_model
            assert(avhrr_model.lat.shape == avhrr_model.lon.shape)
            resulting_st_K = np.ma.masked_all_like(avhrr_model.lat)
            errors = np.ma.masked_all_like(avhrr_model.lat)

            # Get the true values.
            nc_st = nc_file.variables['surface_temperature'][0]
            nc_sst = nc_file.variables['sea_surface_temperature'][0]

            max_error = 0
            st_count = 0
            counter = 0
            started = 0

            number_of_cpus = multiprocessing.cpu_count()
            output_queue = multiprocessing.Queue()

            with coefficients.Coefficients(avhrr_model.satellite_id) as coeff:
                for row_index in np.arange(avhrr_model.lon.shape[0]):

                    print "ROW:", row_index
                    for col_index in np.arange(avhrr_model.lon.shape[1]):
                        counter += 1

                        # import pdb; pdb.set_trace()
                        true_st_K = nc_st[row_index, col_index]
                        if not isinstance(true_st_K, np.float32):
                            # If the value is a float, it has no mask, and the value
                            # is it self...
                            try:
                                # In here we assume it has a mask.
                                if true_st_K.mask:
                                    # If the values is masked, it is not valid.
                                    continue
                                true_st_K = true_st_K.data
                            except Exception:
                                print LOG.error("Unhandled data...")
                                raise

                        # Input temperatures.
                        t37_K = np.NaN # Default not a number.
                        if not np.isnan(avhrr_model.ch3b[row_index, col_index]):
                            # If t37 actually is a temp, put it in here!
                            t37_K = avhrr_model.ch3b[row_index, col_index]

                        # T11 is channel 4.
                        t11_K = avhrr_model.ch4[row_index, col_index]

                        # T11 is channel 5.
                        t12_K = avhrr_model.ch5[row_index, col_index]

                        if np.isnan(t11_K) or np.isnan(t12_K):
                            # t11 and t12 are both needed for all calculations.
                            # Is something wrong if they are both missing?
                            # Consider what to do.
                            raise RuntimeException("Missing T11 or T12")

                        # Angles.
                        sun_zenit_angle = avhrr_model.sun_zenit_angle[row_index, col_index]
                        sat_zenit_angle = avhrr_model.sat_zenit_angle[row_index, col_index]

                        # Missing climatology
                        t_clim_K = t11_K

                        with db.Db("/tmp/noaa.sqlite3"):
                            # Pick algorithm.
                            algorithm = surface_temperature.select_surface_temperature_algorithm(
                                sun_zenit_angle,
                                t11_K,
                                t37_K)

                            # Calculate the temperature.
                            st_K = surface_temperature.get_surface_temperature(algorithm,
                                                                               coeff,
                                                                               t11_K,
                                                                               t12_K,
                                                                               t37_K,
                                                                               t_clim_K,
                                                                               sun_zenit_angle,
                                                                               sat_zenit_angle)

                        resulting_st_K[row_index, col_index] = st_K

                        # errors[row_index, col_index].mask = True
                        errors[row_index, col_index] = st_K - true_st_K
                        st_count += 1

                        """
                        if started > number_of_cpus:
                            # Start getting results when enough processes has
                            # been started.
                            r_idx, c_idx, algoritm, st = output_queue.get()
                            r_idx, c_idx = int(r_idx), int(c_idx)
                            # print "getting", r_idx, c_idx
                            resulting_st_K[r_idx, c_idx] = st
                            # resulting_algorithms[r_idx][c_idx] = str(algoritm)
                            errors[r_idx, c_idx] = st - nc_st[r_idx, c_idx]


                        # Start the calculus lamas.
                        p = multiprocessing.Process(
                            target=calculate_sst,
                            args=(output_queue,
                                  row_index,
                                  col_index,
                                  t11_K,
                                  t12_K,
                                  t37_K,
                                  t_clim_K,
                                  sun_zenit_angle,
                                  sat_zenit_angle,
                                  coeff
                                  ),
                            )
                        p.start()
                        started += 1
                        # print "started", row_index, col_index
            for i in range(number_of_cpus):
                # Get the last results.
                r_idx, c_idx, algoritm, st = output_queue.get()
                resulting_st_K[r_idx, c_idx] = st
            print resulting_st_K
                        """


            print "Antal lat/lon:", counter
            print "Antal st'er:", st_count
            print "Avg error:", np.ma.average(errors)
            print "Std error:", np.ma.std(errors)
            print "Min error:", np.ma.min(errors)
            print "Max error:", np.ma.max(errors)

            
            """
            print "Creating plot"
            n, bins, patches = pylab.hist(errors, 50, range=(np.min(errors), np.max(errors)))
            plt.title("st_K - true_st_K")
            plt.xlabel('st_K - true_st_K')
            plt.ylabel('Count')
            plt.show()



            cmap = plt.get_cmap('seismic')
            im = plt.scatter(avhrr_model.lon,
                             avhrr_model.lat,
                             s=1,
                             c=errors.T,
                             vmin=-np.abs(errors.max()),
                             vmax=np.abs(errors.max()),
                             marker='s',
                             edgecolors='none',
                             cmap=cmap)
            plt.title("st_K - true_st_K\n" + avhrr_model.avhrr_filename)
            plt.xlabel("lon")
            plt.ylabel("lat")
            plt.colorbar()
            plt.show()
            """
            """
            true_surface_temperature = nc_st[row_index, col_index]
            true_sst = nc_sst[row_index, col_index]
            
            if isinstance(true_surface_temperature, np.float32):
            true_st = true_surface_temperature
                        elif isinstance(true_sst, np.float32):
                            true_st = true_sst.data
                        else:
                            continue

                        t37_K = np.NaN
                        if not np.isnan(avhrr_model.ch3b[row_index, col_index]):
                            t37_K = avhrr_model.ch3b[row_index, col_index]

                            # import pdb; pdb.set_trace()
                        t11_K = avhrr_model.ch4[row_index, col_index]
                        t12_K = avhrr_model.ch5[row_index, col_index]


                        if np.isnan(t11_K) or np.isnan(t12_K):
                            resulting_surface_temperature_K[row_index, col_index] = None
                            print row_index, col_index, "avhrr_c"
                            continue

                        sun_zenit_angle = avhrr_model.sun_zenit_angle[row_index, col_index]
                        sat_zenit_angle = avhrr_model.sat_zenit_angle[row_index, col_index]

                        # Missing climatology
                        t_clim_K = t11_K
                    
                        # Find the algoritm to use.
                        
                        algorithm = surface_temperature.select_surface_temperature_algorithm(
                            sun_zenit_angle,
                            t11_K,
                            t37_K)
                        st = surface_temperature.get_surface_temperature(algorithm,
                                                                         coeff,
                                                                         t11_K,
                                                                         t12_K,
                                                                         t37_K,
                                                                         t_clim_K,
                                                                         sun_zenit_angle,
                                                                         sat_zenit_angle)
                        st_count += 1
                        st = round(st, 2)
                        resulting_surface_temperature_K[row_index, col_index] = st
                        error = st - true_st
                        errors[row_index, col_index] = error

                        """
            """
                        if error != 0:
                            errors[row_index, col_index] = error
                        else:
                            errors[row_index, col_index] = 0.1
                        """ 
            """
                        counter += 1
                        if error != 0:
                            error_count += 1

                        if False: #error > 0.01 and sun_zenit_angle > 90:#max_error:
                            max_error = error
                            print "-"*10, algorithm, ":", error, "-"*10
                            print "sun:", sun_zenit_angle, "sat:", sat_zenit_angle
                            print "t11, t12, t37, tclim:", t11_K, t12_K, t37_K, t_clim_K
                            #print avhrr_model.lat[row_index, col_index] - nc_file.variables['lat'][0][row_index, col_index], \
                            #    avhrr_model.lon[row_index, col_index] - nc_file.variables['lon'][0][row_index, col_index], \
                            #    "input", t11_K, t12_K, t37_K, \
                            #    "calc", st, \
                            #    "truth", true_st, true_sst, \
                            #    "diff", st-true_st, st-true_sst
                            
                    # print row_index
            print "Creating plot"
            cmap = plt.get_cmap('PiYG')
            im = plt.scatter(avhrr_model.lon, avhrr_model.lat,  s=1, c=errors.T,  marker='s', edgecolors='none')
            # plt.axis([avhrr_model.lat.min(), avhrr_model.lat.max(), avhrr_model.lon.min(), avhrr_model.lon.max()])
            plt.title('pcolormesh with levels')
            plt.colorbar()
            plt.show()

            """
    # print (resulting_surface_temperature - surface_temperature)
    finally:
        nc_file.close()



