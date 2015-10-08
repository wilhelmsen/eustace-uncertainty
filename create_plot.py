#!/usr/bin/env python
# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.gridspec
import pylab
import eustace.db
import numpy as np
import logging
import datetime

LOG = logging.getLogger(__name__)

def get_bin_indexes(x_intervals, y_intervals, x, y):
    assert(x_intervals is not None)
    assert(y_intervals is not None)
    x_index = np.min(np.where((x <= x_intervals) == True))
    y_index = np.min(np.where((y <= y_intervals) == True))
    return x_index, y_index


def count(bin_counter, x_intervals, y_intervals, x, y):
    assert(bin_counter is not None)
    x_index, y_index = get_bin_indexes(x_intervals, y_intervals, x, y)

    try:
        bin_counter[x_index][y_index] += 1
    except Exception:
        try:
            bin_counter[x_index][y_index] = 1
        except Exception:
            bin_counter[x_index] = {}
            bin_counter[x_index][y_index] = 1

def get_color_array_(x_array, y_array, number_of_x_bins, number_of_y_bins):
    assert(len(x_array) == len(y_array))
    
    t = datetime.datetime.now()

    x_intervals = np.linspace(np.min(x_array), np.max(x_array), number_of_x_bins)
    y_intervals = np.linspace(np.min(y_array), np.max(y_array), number_of_y_bins)
    bin_counter = {}

    LOG.debug("Counting, and inserting into bins.")
    for x, y in zip(x_array, y_array):
        count(bin_counter, x_intervals, y_intervals, x, y)
    LOG.debug("Took, %s" % (str(datetime.datetime.now() - t)))

    LOG.debug("Creating color array")
    t = datetime.datetime.now()
    color_array = np.empty_like(x_array)
    for i in range(len(x_array)):
        x_i, y_i = get_bin_indexes(x_intervals, y_intervals, x_array[i], y_array[i])
        color_array[i] = bin_counter[x_i][y_i]
    LOG.debug("Took, %s" % (str(datetime.datetime.now() - t)))

    return color_array



def get_color_array(x_array, y_array, number_of_x_bins, number_of_y_bins):
    assert(len(x_array) == len(y_array))
    
    t = datetime.datetime.now()

    LOG.debug("Setup")

    x_intervals = np.linspace(np.min(x_array), np.max(x_array), number_of_x_bins)
    y_intervals = np.linspace(np.min(y_array), np.max(y_array), number_of_y_bins)
    colors = np.empty_like(x_array)
    averages = np.empty_like(x_intervals)
    stds = np.empty_like(x_intervals)
    
    LOG.debug("Setup took: %s" % (str(datetime.datetime.now() - t)))
    t = datetime.datetime.now()
    # import pdb; pdb.set_trace()

    LOG.debug("Counting, and inserting into bins.")
    for x_i in range(len(x_intervals)-1):
        t = datetime.datetime.now()
        x_min = x_intervals[x_i]
        x_max = x_intervals[x_i + 1]

        x_mask = (x_array >= x_min) & (x_array <= x_max)

        if not x_mask.any():
            averages[x_i] = np.NaN
            stds[x_i] = np.NaN
            continue

        averages[x_i] = np.average(y_array[x_mask])
        stds[x_i] = np.std(y_array[x_mask])

        for y_i in range(len(y_intervals)-1):
            y_min = y_intervals[y_i]
            y_max = y_intervals[y_i + 1]
            
            mask = x_mask & (y_array >= y_min) & (y_array <= y_max)

            # import pdb; pdb.set_trace()
            # print len(x_array[mask])
            colors[np.where(mask)] = len(x_array[mask])
        LOG.debug("Setting colors (%i) took: %s" % (x_i, str(datetime.datetime.now() - t)))

    return colors, x_intervals, y_intervals, averages, stds




if __name__ == "__main__":
    #if args["--debug"]:
    logging.basicConfig(level=logging.DEBUG)
    #elif args["--verbose"]:
    #    logging.basicConfig(level=logging.INFO)
    #else:
    #    logging.basicConfig(level=logging.WARNING)
    # dpi = 90
    dpi = 2400


    variables = ("s.sun_zenit_angle", "s.sat_zenit_angle", "s.surface_temp", "s.cloud_mask", "s.t_11 - s.t_12")
    number_of_x_bins = 201
    number_of_y_bins = 201
    y = []
    x = {}
    for variable in variables:
        x[variable]=[]

    with eustace.db.Db("/data/hw/eustace_uncertainty_100_pertubations.sqlite3") as db:
        for row in db.get_perturbed_values(variables):
            y.append(row[0])
            for i in range(len(variables)):
                if row[i + 1] == None:
                    x[variables[i]].append(np.NaN)
                else:
                    x[variables[i]].append(row[i + 1])

    LOG.info("%i samples" %(len(y)))

    y_array = np.array(y)

    for variable in variables:
        LOG.debug("Plotting %s." % variable)
        x_array = np.array(x[variable])

        LOG.debug("Clearing plt")
        plt.clf()
        fig = plt.figure()
        plt.title(r"$\mathtt{%s}$" % variable.replace("_", "\_"))
        gs = matplotlib.gridspec.GridSpec(2, 1, height_ratios=[5, 1])
        ax = plt.subplot(gs[0])

        # plt.title(r"$\mathtt{%s}$" % variable.replace("_", "\_"))
        # plt.xlabel(r"$\mathtt{%s}$" % variable.replace("_", "\_"))
        plt.ylabel(r'$\mathtt{st_{pert} (K) - st_{true} (K)}$')
        # cmap = plt.get_cmap('seismic')

        LOG.debug("Getting color array.")
        colors, x_intervals, y_intervals, averages, stds = get_color_array(x_array, y_array, number_of_x_bins, number_of_y_bins)
        # colors = get_color_array(x_array, y_array, number_of_x_bins, number_of_y_bins)

        LOG.debug("Create scatter plot")
        plt.scatter(x[variable],
                    y_array,
                    s=1,
                    c=colors, # x,#errors.T,
                    # vmin=-np.abs(errors.max()),
                    # vmax=np.abs(errors.max()),
                    #alpha=0.75,
                    marker=',',
                    edgecolors='none')
        # cmap=cmap)
        color_bar = plt.colorbar()

        # import pdb; pdb.set_trace()
        # Statistics.
        plt.plot(x_intervals, averages, "w-")
        plt.plot(x_intervals, averages-stds, "w--")
        plt.plot(x_intervals, averages+stds, "w--")
        ax.set_xlim(np.min(x_intervals), np.max(x_intervals))
        ax.set_ylim(-2, 2)


        # Histogram
        ax = plt.subplot(gs[1])
        plt.xlabel(r"$\mathtt{%s}$" % variable.replace("_", "\_"))
        plt.ylabel(r"$\mathtt{N_{samples}}$")
        n, bins, patches = plt.hist(x[variable],
                                    number_of_x_bins,
                                    #alpha=0.5,
                                    )
        ax.set_xlim(np.min(x_intervals), np.max(x_intervals))


        fig.subplots_adjust(right=0.75)

        for label in ax.yaxis.get_ticklabels()[::2]:
            label.set_visible(False)

        filename = "/tmp/ramdisk/euastace_%s.png" % (variable)
        LOG.debug("Save the figure to '%s'." % filename)
        plt.savefig(filename, dpi=dpi)
        LOG.info("'%s' saved." % filename)

        # plt.show()
    
