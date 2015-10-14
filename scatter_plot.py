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

def get_bin_index(interval_centers, value):
    return np.abs(interval_centers - value).argmin()

def get_bin_indexes(x_interval_centers, y_interval_centers, x, y):
    return get_bin_index(x_interval_centers, x), get_bin_index(y_interval_centers, y)

def count(bin_counter, x_interval_centers, y_interval_centers, x, y):
    assert(bin_counter is not None)
    x_index, y_index = get_bin_indexes(x_interval_centers, y_interval_centers, x, y)

    try:
        bin_counter[x_index][y_index] += 1
    except Exception:
        try:
            bin_counter[x_index][y_index] = 1
        except Exception:
            bin_counter[x_index] = {}
            bin_counter[x_index][y_index] = 1


def increment_bins(bins, x_idx, y_idx):
    if bins.has_key(x_idx):
        if bins[x_idx].has_key(y_idx):
            bins[x_idx][y_idx] += 1
        else:
            bins[x_idx][y_idx] = 1
    else:
        bins[x_idx] = {}    
        bins[x_idx][y_idx] = 1


def get_x_stats(x_array, y_array, x_interval_centers, offset):
    assert(len(x_array) == len(y_array))
    
    # Time it...
    t = datetime.datetime.now()
    LOG.debug("Setup get_stats...")

    averages = []
    standard_deviations = []
    
    LOG.debug("Setup took: %s" % (str(datetime.datetime.now() - t)))
    t = datetime.datetime.now()

    LOG.debug("Getting x stats and inserting into bins...")
    t = datetime.datetime.now()
    for x_center in x_interval_centers:
        x_min = x_center - offset
        x_max = x_center + offset

        # Including minimum value, but not maximum value.
        x_mask = (x_array >= x_min) & (x_array < x_max)

        if not x_mask.any() or len(x_array[x_mask]) < 50:
            averages.append(np.NaN)
            standard_deviations.append(np.NaN)
        else:
            averages.append(np.average(y_array[x_mask]))
            standard_deviations.append(np.std(y_array[x_mask]))

    LOG.debug("get_x_stats took: %s" % (str(datetime.datetime.now() - t)))
    return np.array(averages), np.array(standard_deviations)


def get_interval_centers(min_value, max_value, number_of_cells):
    offset = (max_value - min_value)/float(number_of_cells)/2.0 
    interval_centers = np.linspace(min_value, max_value, number_of_cells+1)
    return offset, [i-offset for i in interval_centers[1:]]


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
                             each of the axes will be divided into. [default: 200].
  --y-min=y-min              Set the minimum y value in the plots. [default: -5]
  --y-max=y-max              Set the maximum y value in the plots. [default:  5]
  --limit=limit              Limit the number of pixels to get from the database.
  --grid                     Include grid in the plot.

Example:
  python {filename} /data/hw/eustace_uncertainty_10_perturbations.sqlite3 s.sun_zenit_angle s.sat_zenit_angle s.surface_temp "s.cloudmask" "s.t_11 - s.t_12"

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

    variable_names = args["<variables>"]
    limit = None if args["--limit"] is None else int(args["--limit"])
    number_of_x_bins = int(args["--interval-bins"])
    number_of_y_bins = int(args["--interval-bins"])
    y_array = []

    x_arrays = {}
    for variable in variable_names:
        x_arrays[variable]=[]

    import random
    random.seed(1)
    # Get the values from the database.
    with eustace.db.Db(args["<database-filename>"]) as db:
        for row in db.get_perturbed_values(variable_names, limit=limit):
            if random.random() > 0.03:
                continue 
            y_array.append(row[0])
            
            for i in range(len(variable_names)):
                if row[i + 1] == None:
                    x_arrays[variable_names[i]].append(np.NaN)
                else:
                    x_arrays[variable_names[i]].append(row[i + 1])

    LOG.info("%i samples" %(len(y_array)))
    y_range_min, y_range_max = int(args["--y-min"]), int(args["--y-max"])
    y_array = np.array(y_array)
    y_offset, y_interval_centers = get_interval_centers(y_range_min, y_range_max, number_of_y_bins)

    for variable_name in variable_names:
        LOG.debug("Plotting %s." % variable_name)
        x_array = np.array(x_arrays[variable_name])

        LOG.debug("Clearing plt")
        plt.clf()
        fig = plt.figure()
        plt.title(r"$\mathtt{%s}$" % variable_name.replace("_", "\_"))

        x_offset, x_interval_centers = get_interval_centers(np.min(x_array), np.max(x_array), number_of_x_bins)

        LOG.debug("Getting stats.")
        averages, standard_deviations = get_x_stats(x_array, y_array, x_interval_centers, x_offset)

        LOG.debug("Getting color array.")
        LOG.debug("Counting...")
        t = datetime.datetime.now()
        bins_count = {}
        x_len = len(x_array)
        for i, x_ in enumerate(x_array):
            if i % 100000 == 0:
                print i, "/", x_len
            x_i = get_bin_index(x_interval_centers, x_array[i])
            y_i = get_bin_index(y_interval_centers, y_array[i])
            increment_bins(bins_count, x_i, y_i)
        LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))

        LOG.debug("Creating colors...")
        t = datetime.datetime.now()
        colors = np.empty_like(x_array)
        for i, c in enumerate(colors):
            if i % 100000 == 0:
                print i, "/", x_len
            x_i = get_bin_index(x_interval_centers, x_array[i])
            y_i = get_bin_index(y_interval_centers, y_array[i])
            colors[i] = bins_count[x_i][y_i]
        LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))
            
        LOG.debug("Getting colors. Counting.")

        # Getting x-axis ranges.
        x_range_min, x_range_max = get_axis_range(x_interval_centers)

        # Define the image grid.
        gs = matplotlib.gridspec.GridSpec(3, 1, height_ratios=[1, 5, 1])


        ###################################
        #  Average and standard deviation #
        ###################################
        LOG.debug("Create the statistics plot / top bar.")
        
        # Set the image grid.
        ax = plt.subplot(gs[0])
        ax.grid(args["--grid"])

        # Average for all values.
        average = np.average(y_array)
        plt.plot([x_range_min, x_range_max], [average, average], linewidth=0.1, color="black")

        # Std for all values.
        std = np.std(y_array)
        plt.plot([x_range_min, x_range_max], [std, std], linewidth=0.1, color="black")

        # The average for each x axis interval.
        plt.plot(x_interval_centers, averages, "b-", linewidth=0.5)
        plt.plot(x_interval_centers, standard_deviations, "r-", linewidth=0.5)

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
        ax.grid(args["--grid"])

        # Do the scatter plot.
        plt.scatter(x_array,
                    y_array,
                    s=0.1,
                    c=colors,
                    marker=',',  # Pixel.
                    edgecolors='none'  # No pixel edges.
                    )
        color_bar = plt.colorbar()

        # Insert the statistics on top of the scatter plot.
        plt.plot(x_interval_centers, averages, "-", color="black", linewidth=0.5)
        plt.plot(x_interval_centers, averages-standard_deviations, "-", color="black", linewidth=0.5)
        plt.plot(x_interval_centers, averages+standard_deviations, "-", color="black", linewidth=0.5)

        # Text on the y-axis.
        plt.ylabel(r'$\mathtt{st_{pert} (K) - st_{true} (K)}$')

        # Set the range of the xaxis.
        ax.set_xlim(x_range_min, x_range_max)
        ax.set_ylim(y_range_min, y_range_max)


        #############
        # Histogram #
        #############
        ax = plt.subplot(gs[2]) 
        ax.grid(args["--grid"])

        plt.xlabel(r"$\mathtt{%s}$" % variable_name.replace("_", "\_"))
        plt.ylabel(r"$\mathtt{N_{samples}}$")
        n, bins, patches = plt.hist(x_array,
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

        filename = "/tmp/euastace_%s.png" % (variable_name)
        filename = filename.replace(" ", "_")
        LOG.debug("Save the figure to '%s'." % filename)
        plt.savefig(filename, dpi=int(args['--dpi']))
        LOG.info("'%s' saved." % filename)

        # plt.show()
    
