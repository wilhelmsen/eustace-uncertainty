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


def get_stats_and_colors(x_array, y_array, x_intervals, y_intervals):
    assert(len(x_array) == len(y_array))
    
    # Time it...
    t = datetime.datetime.now()

    LOG.debug("Setup")

    colors = np.empty_like(x_array)
    averages = np.empty_like(x_intervals)
    stds = np.empty_like(x_intervals)
    
    LOG.debug("Setup took: %s" % (str(datetime.datetime.now() - t)))
    t = datetime.datetime.now()

    LOG.debug("Counting, and inserting into bins.")
    for x_i in range(len(x_intervals)-1):
        t = datetime.datetime.now()
        x_min = x_intervals[x_i]
        x_max = x_intervals[x_i + 1]

        # Including minimum value, but not maximum value.
        x_mask = (x_array >= x_min) & (x_array < x_max)

        if not x_mask.any():
            averages[x_i] = np.NaN
            stds[x_i] = np.NaN
            continue

        # Only calculate the stats if there are many values.

        #import pdb; pdb.set_trace()
        if len(x_array[x_mask]) < 50:
            averages[x_i] = np.NaN
            stds[x_i] = np.NaN
        else:
            averages[x_i] = np.average(y_array[x_mask])
            stds[x_i] = np.std(y_array[x_mask])

        # For every bin.
        for y_i in range(len(y_intervals)-1):
            y_min = y_intervals[y_i]
            y_max = y_intervals[y_i + 1]

            # Including minimum value, but not maximum value.
            mask = x_mask & (y_array >= y_min) & (y_array < y_max)
            colors[np.where(mask)] = len(x_array[mask])

        LOG.debug("Setting colors (%i) took: %s" % (x_i, str(datetime.datetime.now() - t)))

    return colors, x_intervals, y_intervals, averages, stds


def get_axis_range(interval, padding_pct=1):
    """
    Getting the axis range. Adding padding in % to both sides.
    """
    axis_min, axis_max = np.min(interval), np.max(interval)
    # Add 1% extra to the axis range.
    padding = (axis_max - axis_min) * padding_pct / 100.0
    axis_min -= padding
    axis_max += padding
    return axis_min, axis_max


if __name__ == "__main__":
    import docopt
    __doc__ = """
File: {filename}

Usage:
  {filename} <database-filename> [-d|-v] [options] <variables>...
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help                  Show this screen.
  --version                  Show version.
  -v --verbose               Show some diagostics.
  -d --debug                 Show some more diagostics.
  --dpi=dp                   The dpi of the output image, [default: 72].
  --interval-bins=bins       Both the x-axis and the y-axis are divided into intervals that
                             creates a grid of cells. This is the number of small intervals
                             each of the axes will be divided into. [default: 201].
  --y-min=y-min              Set the minimum y value in the plots. [default: -2]
  --y-max=y-max              Set the maximum y value in the plots. [default:  2]

Example:
  python {filename} /data/hw/eustace_uncertainty_10_perturbations.sqlite3 s.sun_zenit_angle s.sat_zenit_angle s.surface_temp "s.cloud_mask" "s.t_11 - s.t_12"

""".format(filename=__file__)
    args = docopt.docopt(__doc__, version='0.1')
    if args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    LOG.info(args)
    # import sys; sys.exit()

    variables = args["<variables>"]
    number_of_x_bins = int(args["--interval-bins"])
    number_of_y_bins = int(args["--interval-bins"])
    y = []
    x = {}
    for variable in variables:
        x[variable]=[]

    # Get the values from the database.
    with eustace.db.Db(args["<database-filename>"]) as db:
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

        LOG.debug("Getting color array.")

        x_intervals = np.linspace(np.min(x_array), np.max(x_array), number_of_x_bins)
        y_intervals = np.linspace(np.min(y_array), np.max(y_array), number_of_y_bins)
        colors, x_intervals, y_intervals, averages, stds = get_stats_and_colors(x_array, y_array, x_intervals, y_intervals)

        # Getting x-axis ranges.
        x_range_min, x_range_max = get_axis_range(x_intervals)
        y_range_min, y_range_max = int(args["--y-min"]), int(args["--y-max"])

        # Define the image grid.
        gs = matplotlib.gridspec.GridSpec(3, 1, height_ratios=[1, 5, 1])



        ###################################
        #  Average and standard deviation #
        ###################################
        LOG.debug("Create the statistics plot / top bar.")
        
        # Set the image grid.
        ax = plt.subplot(gs[0])

        # Average for all values.
        average = np.average(y_array)
        plt.plot([x_range_min, x_range_max], [average, average], linewidth=0.1, color="black")

        # Std for all values.
        std = np.std(y_array)
        plt.plot([x_range_min, x_range_max], [std, std], linewidth=0.1, color="black")

        # The average for each x axis interval.
        plt.plot(x_intervals, averages, "b-", linewidth=0.5)
        plt.plot(x_intervals, stds, "r-", linewidth=1)

        # Set the range of the xaxis.
        ax.set_xlim(x_range_min, x_range_max)
        ax.set_ylim(y_range_min/4, y_range_max/2)

        # 5% out to the left.
        ax.annotate('A: %0.2f' % (average), xy=(x_range_max, average), xycoords='data',
                    xytext=(20, -5), textcoords='offset points',
                    arrowprops=dict(arrowstyle="->"),
                    annotation_clip=False)

        ax.annotate('S: %0.2f' % (std), xy=(x_range_max, std), xycoords='data',
                    xytext=(20, 5), textcoords='offset points',
                    arrowprops=dict(arrowstyle="->"),
                    annotation_clip=False)

        # Text on the y-axis.
        plt.ylabel(r"$\mathtt{stats}$")

        # Hide every other yaxis label.
        for label in ax.yaxis.get_ticklabels()[::2]:
            label.set_visible(False)

        # Hide all the xaxis labels.
        for label in ax.xaxis.get_ticklabels():
            label.set_visible(False)




        #############################
        #  The main (scatter) plot. #
        #############################
        LOG.debug("Create scatter plot")

        # Set the image grid.
        ax = plt.subplot(gs[1])

        # Do the scatter plot.
        plt.scatter(x[variable],
                    y_array,
                    s=0.1,
                    c=colors,
                    marker=',',  # Pixel.
                    edgecolors='none'  # No pixel edges.
                    )
        color_bar = plt.colorbar()

        # Insert the statistics on top of the scatter plot.
        plt.plot(x_intervals, averages, "-", color="black", linewidth=0.5)
        plt.plot(x_intervals, averages-stds, "-", color="black", linewidth=0.5)
        plt.plot(x_intervals, averages+stds, "-", color="black", linewidth=0.5)

        # Text on the y-axis.
        plt.ylabel(r'$\mathtt{st_{pert} (K) - st_{true} (K)}$')

        # Set the range of the xaxis.
        ax.set_xlim(x_range_min, x_range_max)
        ax.set_ylim(y_range_min, y_range_max)



        #############
        # Histogram #
        #############
        ax = plt.subplot(gs[2])
        plt.xlabel(r"$\mathtt{%s}$" % variable.replace("_", "\_"))
        plt.ylabel(r"$\mathtt{N_{samples}}$")
        n, bins, patches = plt.hist(x[variable],
                                    number_of_x_bins,
                                    #alpha=0.5,
                                    )

        # Set the range of the xaxis.
        ax.set_xlim(x_range_min, x_range_max)

        # Hide the xaxis labels.
        for label in ax.xaxis.get_ticklabels():
            label.set_visible(False)

        # Hide the yaxis labels.
        for label in ax.yaxis.get_ticklabels()[::2]:
            label.set_visible(False)



        # Align all the plots.
        fig.subplots_adjust(right=0.75)

        filename = "/tmp/ramdisk/euastace_%s.png" % (variable)
        LOG.debug("Save the figure to '%s'." % filename)
        plt.savefig(filename, dpi=int(args['--dpi']))
        LOG.info("'%s' saved." % filename)

        # plt.show()
    
