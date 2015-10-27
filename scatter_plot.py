#!/usr/bin/env python
# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.gridspec
import pylab
import eustace.db
import eustace.surface_temperature
import numpy as np
import logging
import datetime
import random
import os

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

def get_color_array(x_array_pruned, y_array_pruned, x_interval_centers, y_interval_centers):
        LOG.debug("Getting color array.")
        LOG.debug("Counting...")
        t = datetime.datetime.now()
        bins_count = {}
        x_len = len(x_array_pruned)
        for i, x_ in enumerate(x_array_pruned):
            if i % 100000 == 0:
                print i, "/", x_len
            x_i = get_bin_index(x_interval_centers, x_array_pruned[i])
            y_i = get_bin_index(y_interval_centers, y_array_pruned[i])
            increment_bins(bins_count, x_i, y_i)
        LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))


        LOG.debug("Creating colors...")
        t = datetime.datetime.now()
        colors = np.empty_like(x_array_pruned)
        for i, c in enumerate(colors):
            if i % 100000 == 0:
                print i, "/", x_len
            x_i = get_bin_index(x_interval_centers, x_array_pruned[i])
            y_i = get_bin_index(y_interval_centers, y_array_pruned[i])
            colors[i] = bins_count[x_i][y_i]
        LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))
        return colors

def randomly_prune(x_array, y_array, fraction_to_keep):
        LOG.debug("Pruning the data for plot...")
        t = datetime.datetime.now()
        y_array_pruned = []
        x_array_pruned = []
        for i in np.arange(y_array_length):
            if np.isnan(x_array[i]):
                continue
            if random.random() >= fraction_to_keep:
                continue
            y_array_pruned.append(y_array[i])
            x_array_pruned.append(x_array[i])
        LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))
        return x_array_pruned, y_array_pruned

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


def get_interval_center_points(min_value, max_value, number_of_cells):
    """
    Creates a linspace and then converts it to its centerpoints.

    That is...
    Create a linspace which are the "edges" of the bin cells. One extra,
    to cover the last cell.

    |---|---|---|---|---|---|---|
    '   '   '   '   '   '   '   '

    Then the intervals are shifted to the right, to point to the center
    points.
    |---|---|---|---|---|---|---|
      '   '   '   '   '   '   '   '

    And then the last one is removed.

    |---|---|---|---|---|---|---|
      '   '   '   '   '   '   '

    We now have <number_of_cells> center points.
    """
    interval_centers = np.linspace(min_value, max_value, number_of_cells+1)
    offset = (max_value - min_value)/float(number_of_cells)/2.0 
    return offset, [i+offset for i in interval_centers[:-1]]

def get_marker_size(variable_name, x_offset):
    # if variable_name.replace(" ", "").lower() == "s.sea_ice_fraction":
    #    marker_size = x_offset/2.0
    #else:
    marker_size = 0.1
    LOG.debug("Marker size set to %f." % (marker_size))
    return marker_size


def get_axis_range(interval, offset, padding_pct=1):
    """
    Getting the axis range. Adding padding in % to both sides.
    """
    axis_min, axis_max = np.nanmin(interval)-offset, np.nanmax(interval)+offset
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
  {filename} <database-filename> [-d|-v] [--output-dir=<output-dir>] [options] <variables>...
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help                  Show this screen.
  --version                  Show version.
  -v --verbose               Show some diagostics.
  -d --debug                 Show some more diagostics.
  --dpi=dp                   The dpi of the output image, [default: 300].
  --interval-bins=bins       Both the x-axis and the y-axis are divided into intervals that
                             creates a grid of cells. This is the number of small intervals
                             each of the axes will be divided into. [default: 200].
  --y-min=y-min              Set the minimum y value in the plots [default: -5].
  --y-max=y-max              Set the maximum y value in the plots [default:  5].
  --limit=limit              Limit the number of pixels to get from the database.
  --grid                     Include grid in the plot.
  --output-dir=<output-dir>  Output directory.
  --lat-lt=<lat>             Include lats less than.
  --lat-gt=<lat>             Include lats greater than.
  --t11-t12-limit=<limit>    Only include values where t_11 - t12 is less than this value.
  --algorithm=<algo>         Only include values calculated with the given algorithm.

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
    number_of_y_bins = int(args["--interval-bins"])
    y_array = []

    x_arrays = {}
    for variable in variable_names:
        x_arrays[variable]=[]

    random.seed(1)

    LOG.debug("Get the values from the database.")
    t = datetime.datetime.now()
    with eustace.db.Db(args["<database-filename>"]) as db:
        # Where sql used for the title in the plots.
        where_sql = db.build_where_sql(lat_less_than=args["--lat-lt"]
                                       lat_greater_than=args["--lat-gt"],
                                       tb_11_minus_tb_12_limit=args["--t11-t12-limit"],
                                       algorithm=args["--algorithm"])
        # Get the values.
        for row in db.get_perturbed_values(variable_names,
                                           lat_less_than=args["--lat-lt"],
                                           lat_greater_than=args["--lat-gt"],
                                           tb_11_minus_tb_12_limit=args["--t11-t12-limit"],
                                           algorithm=args["--algorithm"],
                                           limit=limit):
            y_array.append(row[0])
            for i in range(len(variable_names)):
                if row[i + 1] == None:
                    x_arrays[variable_names[i]].append(np.NaN)
                else:
                    x_arrays[variable_names[i]].append(row[i + 1])
    LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))

    LOG.info("%i samples" %(len(y_array)))
    y_array = np.array(y_array)

    y_array_is_not_nan = y_array[~np.isnan(y_array)]
    average_all = np.average(y_array_is_not_nan)
    std_all = np.std(y_array_is_not_nan)
    y_array_length = len(y_array)
    number_of_points_wished_in_plot = 5e5
    y_range_min, y_range_max = float(args["--y-min"]), float(args["--y-max"])
    y_offset, y_interval_centers = get_interval_center_points(y_range_min, y_range_max, number_of_y_bins)
    minimum_number_of_values_to_plot = 100
    
    for variable_name in variable_names:
        LOG.debug("#" * 30)
        LOG.debug("Plotting %s." % variable_name)
        LOG.debug("#" * 30)

        # Make sure the array is a numpy array.
        x_array = np.array(x_arrays[variable_name])
        
        LOG.debug("Remove the nans from the x_array and sort what is left.")
        t = datetime.datetime.now()  # Diagnostics.
        x_array_without_nans_sorted = np.sort(x_array[~np.isnan(x_array)])
        LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))
        LOG.info("%i values when NaN is removed." % (x_array_without_nans_sorted.size))

        if x_array_without_nans_sorted.size < minimum_number_of_values_to_plot:
            LOG.info("Not enough valid values for '%s'. Moving on to the next plot." % (variable_name))
            continue

        # Set up the plot. Clearing it, ranges and so.
        LOG.debug("Clearing plt")
        plt.clf()
        fig = plt.figure()

        # Center points.
        # This is used to create the colors in the scatter plot.
        # The axis ranges (the visual area) of the scatter plot is divided
        # into bins. Each bin is defined by its center point.
        # The x_array is then connected to every the closest center point. This last
        # detail also means that if a point in the x_array is outside the visual area,
        # the closest bin is on the edge.
        # The y_bins are the same for all x_variables, which is why only the
        # x_intervals_centers are set here.
        LOG.debug("Getting interval center points.")
        t = datetime.datetime.now()  # Diagnostics.

        # Set the x-axis intervals.
        if variable_name.replace(" ", "").lower() == "s.t_11-s.t_12":
            x_min, x_max = -0.5, 3.0
        else:
            x_min, x_max = x_array_without_nans_sorted[0], x_array_without_nans_sorted[-1]
        
        number_of_x_bins = int(args["--interval-bins"])
        if variable_name.replace(" ", "").lower() == "s.sea_ice_fraction":
            number_of_x_bins = 20

        x_offset, x_interval_centers = get_interval_center_points(x_min, x_max,
                                                                  number_of_x_bins)
        LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))

        # Getting the statistics for each column. This is used to plot the line
        # in the uppermost plot that shows how the statistcs change over time.
        LOG.debug("Getting stats.")
        t = datetime.datetime.now()  # Diagnostics.
        averages, standard_deviations = get_x_stats(x_array, y_array,
                                                    x_interval_centers, x_offset)
        LOG.debug("Took: %s" % (str(datetime.datetime.now() - t)))

        # Getting x-axis ranges. It just adds a little on the edges.
        x_range_min, x_range_max = get_axis_range(x_interval_centers, x_offset)

        # The plot uses a gridspec. 3 rows. 1 col.
        gs = matplotlib.gridspec.GridSpec(3, 1, height_ratios=[1, 5, 1])

        ###################################
        #  Average and standard deviation #
        ###################################
        LOG.debug("Create the statistics plot / top bar.")
        
        # Set the image grid.
        ax = plt.subplot(gs[0])  # The first column.
        ax.grid(args["--grid"])  # Grid in the plot or not.

        # Set the title.
        title = os.path.basename(args["<database-filename>"]).replace(".sqlite3", "").replace("db", "").replace("_", "\_")
        title += " (%s)" % args["--algorithm"] if args["--algorithm"] is not None else ""
        title += ": %s" % variable_name
        title = r"$\mathtt{%s}$" % title
        if where_sql is not None and where_sql.strip() != "":
            title += "\n"
            title += r"$ \mathtt{ %s} $" % (where_sql)

        title = title.replace("_", "\_")

        for index in [11, 12, 37]:
            title = title.replace("t\_%i" % (index), "t_{%i}" % (index))
            title = title.replace("epsilon\_%i" % (index), "\epsilon_{%i}" % (index))

        LOG.debug("Title:")
        LOG.debug(title)

        ax.set_title( title )

        # Plot average for all values.
        plt.plot([x_range_min, x_range_max], [average_all, average_all], linewidth=0.1, color="black")

        # Plot std for all values.
        plt.plot([x_range_min, x_range_max], [std_all, std_all], linewidth=0.1, color="black")

        # The average for each x axis interval.
        plt.plot(x_interval_centers, averages, "b-", linewidth=0.5)
        plt.plot(x_interval_centers, standard_deviations, "r-", linewidth=0.5)

        # Set the range of the xaxis.
        ax.set_xlim(x_range_min, x_range_max)
        ax.set_ylim(y_range_min/4.0, y_range_max/2.0)

        # 5% out to the left.
        ax.annotate('A: %0.2f' % (average_all), xy=(x_range_max, average_all), xycoords='data',
                    xytext=(20, -5), textcoords='offset points',
                    arrowprops=dict(arrowstyle="->"),
                    annotation_clip=False)

        ax.annotate('S: %0.2f' % (std_all), xy=(x_range_max, std_all), xycoords='data',
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

        # Determine the fraction of the array to put in the plot.
        fraction_to_keep = min(number_of_points_wished_in_plot / float(x_array_without_nans_sorted.size), 1)

        # Get the randomly pruned x_array.
        x_array_pruned, y_array_pruned = randomly_prune(x_array, y_array, fraction_to_keep)

        # Get the colors array
        colors = get_color_array(x_array_pruned, y_array_pruned, x_interval_centers, y_interval_centers)

        # Set the image grid.
        ax = plt.subplot(gs[1])
        ax.grid(args["--grid"])

        # Set the scatter plot marker size.
        marker_size = get_marker_size(variable_name, x_offset)

        # Do the scatter plot.
        plt.scatter(x_array_pruned,
                    y_array_pruned,
                    s=marker_size,
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

        # Set the range of axis.
        ax.set_xlim(x_range_min, x_range_max)
        ax.set_ylim(y_range_min, y_range_max)


        #############
        # Histogram #
        #############
        ax = plt.subplot(gs[2])  # Last grid point. 
        ax.grid(args["--grid"])  # Grid in the plot or not.

        # Axis labels.
        plt.xlabel(r"$\mathtt{%s}$" % variable_name.replace("_", "\_"))
        plt.ylabel(r"$\mathtt{N_{samples}}$")

        # Do the plot.
        n, bins, patches = plt.hist(x_array_without_nans_sorted, number_of_x_bins)

        # Set the range of the xaxis.
        ax.set_xlim(x_range_min, x_range_max)

        # Hide the xaxis labels.
        for label in ax.xaxis.get_ticklabels():
            label.set_visible(False)

        # Hide every second yaxis labels.
        for label in ax.yaxis.get_ticklabels()[::2]:
            label.set_visible(False)

        # Printing the number of samples...
        ax.annotate(r'$\mathtt{N_{total}}:$',
                    xy=(1.05, 0.6),
                    xycoords='axes fraction',
                    annotation_clip=False)
        ax.annotate(r'$\mathtt{%s}$' % ("{:,}".format(x_array_without_nans_sorted.size)),
                    xy=(1.05, 0.2),
                    xycoords='axes fraction',
                    annotation_clip=False)

        ###################
        # Saving the plot #
        ###################

        # Align all the sub plots.
        fig.subplots_adjust(right=0.75)

        # Create a filename.
        filename = "%s" % (os.path.basename(args["<database-filename>"]).replace(".sqlite3", ""))
        filename += "_%s" % args["--algorithm"] if args["--algorithm"] is not None else ""
        filename += "_%s" % variable_name
        filename += ".png"
        # Replacing all spaces with underscores.
        filename = filename.replace(" ", "_")

        # Append to output directory, if set.
        if args["--output-dir"] is not None:
            # Make sure that the output directory exits.
            if not os.path.isdir(args["--output-dir"]):
                # Create the output directory.
                LOG.warning("Output directory, '%s', did not exist. Creating it." % args["--output-dir"])
                os.makedirs(args["--output-dir"])

            # Put the files in the output directory.
            filename = os.path.join(args["--output-dir"], filename)

        # Save to file.
        LOG.debug("Save the figure to '%s'." % filename)
        plt.savefig(filename, dpi=int(args['--dpi']))
        LOG.info("'%s' saved." % filename)
        # plt.show()
    
