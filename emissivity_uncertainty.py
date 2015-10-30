import os
import numpy as np
import logging
import matplotlib.pyplot as plt
import eustace.surface_temperature
import eustace.coefficients
import matplotlib.ticker
LOG = logging.getLogger(__name__)

def load_values_from_file(emissivity_filename):
    """
    Loads the temperatures from the file.
    """
    # A line in the file looks like this.
    # Id  -               -         emissivity_11  emissivity_12  emissivity_37  tb_11_K       tb_12_K       tb_37_K
    # 0 206.768685832 282.659909404 0.988527449772 0.993135765454 0.982494177159 258.880819891 258.880819891 258.880819891
    keys = ["id", "grain_size", "density", "emissivity_11", "emissivity_12", "emissivity_37", "tb_11_K", "tb_12_K", "tb_37_K"]

    # Make sure that the results is ready for appending values.
    results = {}
    for key in keys:
        results[key] = []
    
    with open(emissivity_filename, "r") as fp:
        for line in fp:
            if line.strip() == "":
                continue
            line_parts = line.strip().split()
            for i, key in enumerate(keys):
                if i == 0:
                    results[key].append(int(line_parts[i]))
                else:
                    results[key].append(float(line_parts[i]))
    return results


def calc_stats(values):
    """
    Calculate the statistics for all the loaded values.

    That is, for now:

    sat zenith angle 0:
      avg(tb_11_K), std(tb_11_K)
      avg(tb_12_K), std(tb_12_K)
      avg(tb_37_K), std(tb_37_K)

    sat zenith angle 30:
      avg(tb_11_K), std(tb_11_K)
      avg(tb_12_K), std(tb_12_K)
      avg(tb_37_K), std(tb_37_K)

    sat zenith angle 60:
      avg(tb_11_K), std(tb_11_K)
      avg(tb_12_K), std(tb_12_K)
      avg(tb_37_K), std(tb_37_K)
    """
    stats = {}
    for sat_zen_angle_key in values.keys():
        stats[sat_zen_angle_key] = {}
        for temperature_key in values[sat_zen_angle_key].keys():
            a = np.array(values[sat_zen_angle_key][temperature_key])
            stats[sat_zen_angle_key][temperature_key] = {}
            stats[sat_zen_angle_key][temperature_key]["average"] = np.average(a)
            stats[sat_zen_angle_key][temperature_key]["std"] = np.std(a)

        a = np.array(values[sat_zen_angle_key]["tb_11_K"]) - np.array(values[sat_zen_angle_key]["tb_12_K"])
        stats[sat_zen_angle_key]["t11-t12"] = {}
        stats[sat_zen_angle_key]["t11-t12"]["average"] = np.average(a)
        stats[sat_zen_angle_key]["t11-t12"]["std"] = np.std(a)
    return stats


def get_temperatures(satellite_id, sun_zenith_angle, sat_zenith_angle, values):
    """
    Calculate the temperature for all the values in the files.
    """
    with eustace.coefficients.Coefficients(satellite_id) as coeff:
        for i in range(len(values["tb_11_K"])):
            tb_11_K = values["tb_11_K"][i]
            tb_12_K = values["tb_12_K"][i]
            tb_37_K = values["tb_37_K"][i]
            t_clim_K = tb_11_K

            # Pick algorithm.
            algorithm = eustace.surface_temperature.select_surface_temperature_algorithm(
                sun_zenith_angle,
                tb_11_K,
                tb_37_K)

            # Calculate the temperature.
            surface_temperature_K = eustace.surface_temperature.get_surface_temperature(algorithm,
                                                                             coeff,
                                                                             tb_11_K,
                                                                             tb_12_K,
                                                                             tb_37_K,
                                                                             t_clim_K,
                                                                             sun_zenith_angle,
                                                                             sat_zenith_angle)

            yield algorithm, surface_temperature_K


def create_histogram(sun_zenith_angle, sat_zenith_angles, sat_zenith_angle_temps, dpi, output_directory=None):
    """
    Create a histogram of how the perturbed values are distributed.
    """
    plt.clf()
    max_temp = -1e20
    min_temp = 1e20

    for sat_zenith_angle in sat_zenith_angles:
        max_temp = max(np.max(sat_zenith_angle_temps[sat_zenith_angle]), max_temp)
        min_temp = min(np.min(sat_zenith_angle_temps[sat_zenith_angle]), max_temp)

    offset = 0.3
    t = 260
    number_of_bins = 30
    _bins = np.linspace(t-offset, t+offset, number_of_bins)

    for sat_zenith_angle in sat_zenith_angles:
        LOG.debug("Clear the plot...")
        plt.clf()

        LOG.debug("Create the histogram.")
        n, bins, patches = plt.hist(sat_zenith_angle_temps[sat_zenith_angle],
                                    _bins,
                                    # alpha=0.5,
                                    color="#FF1493",
                                    label="%i" % sat_zenith_angle)
        #plt.legend(loc="upper left")

        # Avoid "offset xaxis". That is, when e.g. 10393200 becomes 
        # 1.0393200 + 1e-7 where 1e-7 is the offset, or something more
        # obscure.
        plt.gca().get_xaxis().get_major_formatter().set_useOffset(False)

        # Create a filename.
        filename = "emissivity_histogram_sun_zenith_angle_%i_sat_zenith_angle_%02i" % (sun_zenith_angle, sat_zenith_angle)
        filename += ".png"
        # Replacing all spaces with underscores.
        filename = filename.replace(" ", "_")

        if output_directory is not None:
            # Put the files in the output directory.
            filename = os.path.join(output_directory, filename)

        # Making the filename absolute.
        filename = os.path.abspath(filename)

        # Create the plot.
        plt.title(r"$\mathtt{sun\_zenith\_angle: %i, sat\_zenith\_angle:\ %02i}$" %(sun_zenith_angle, sat_zenith_angle))
        plt.ylabel(r"$\mathtt{N_{perturbations}}$")
        plt.xlabel(r"$\mathtt{sat\_zenith\_angle}$")
        x1,x2,y1,y2 = plt.axis()
        plt.axis((x1, x2, 0, 450))

        # Saving the figure.
        LOG.debug("Saving plot to %s" %(filename))
        plt.savefig(filename, dpi=dpi)
        LOG.info("Plot saved to %s" %(filename))


def create_line_plot(sun_zenith_angle, sat_zenith_angles, surface_temperature_stds, dpi, output_dir=None):
    """
    Creates the line plot of the standard deviations.
    """
    LOG.debug("Clearing plt")
    plt.clf()

    plt.title(r"$\mathtt{Sandard\ deviation,\ sun\_zenith\_angle:\ %i}$" %(sun_zenith_angle))
    for sat_zenith_angle, surface_temp in zip(sat_zenith_angles, surface_temperature_stds):
        LOG.info("%s %s" %(sat_zenith_angle, surface_temp))
    plt.plot(sat_zenith_angles, surface_temperature_stds, "r-", label="std(st)", color="#FF1493")

    plt.ylabel(r"$\mathtt{Standard deviation}$")
    plt.xlabel(r"$\mathtt{sat\_zenith\_angle}$")

    # Create a filename.
    filename = "emissivity_standard_deviations_sun_zenith_angle_%i" % (sun_zenith_angle)
    filename += ".png"
    # Replacing all spaces with underscores.
    filename = filename.replace(" ", "_")
    
    # Append to output directory, if set.
    if output_dir is not None:
        # Make sure that the output directory exits.
        if not os.path.isdir(output_dir):
            # Create the output directory.
            LOG.warning("Output directory, '%s', did not exist. Creating it." % output_dir)
            os.makedirs(output_dir)

        # Put the files in the output directory.
        filename = os.path.join(output_dir, filename)

    LOG.debug("Saving plot to %s" %(filename))
    plt.savefig(filename, dpi=dpi)
    LOG.info("Plot saved to %s" %(filename))


def calculate_surface_temperatures_by_sat_zenith_angle(satellite_id, sun_zenith_angle, sat_zenith_angles, values_from_files):
    """
    Calculate the surface temperatures based on the simulated input
    brightness temperatures.
    """
    surface_temperatures_by_sat_zenith_angle = {}
    for sat_zenith_angle in sat_zenith_angles:
        # For every sat zenith angle.
        surface_temperatures=[]
        i = 0
        for algorithm, surface_temperature_K in get_temperatures(satellite_id,
                                                                 sun_zenith_angle,
                                                                 sat_zenith_angle,
                                                                 values_from_files["sat_zen_%02i" % (sat_zenith_angle)],):
            if np.isnan(surface_temperature_K):
                LOG.debug("surface_temperature_K was NaN.")
                continue

            surface_temperatures.append(surface_temperature_K)
        # Put the collection of temperatures into the dict.
        # Converts to np.array first.
        surface_temperatures_by_sat_zenith_angle[sat_zenith_angle] = np.array(surface_temperatures)
    # Return all the calculted temperatures.
    return surface_temperatures_by_sat_zenith_angle

def get_surface_temperature_stds(surface_temperatures_by_sat_zenith_angle, sat_zenith_angles):
    surface_temperature_stds = []
    for sat_zenith_angle in sat_zenith_angles:
        surface_temperature_stds.append(np.std(surface_temperatures_by_sat_zenith_angle[sat_zenith_angle]))
    return surface_temperature_stds

        

if __name__ == "__main__":
    import docopt
    sat_zenith_angles = [0, 15, 30, 45, 60]

    __doc__ = """
File: {filename}

Usage:
  {filename} <satellite_id> <sun_zenith_angle> {emissivity_sat_zen_filenames} [-d|-v] [options]
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help                                Show this screen.
  --version                                Show version.
  -v --verbose                             Show some diagostics.
  -d --debug                               Show some more diagostics.
  --dpi=dp                                 The dpi of the output image, [default: 300].
  --output-dir=<dir>                       Output directory.
""".format(filename=__file__,
           emissivity_sat_zen_filenames="<emissivity_sat_zen_" + "_filename> <emissivity_sat_zen_".join(["%02i" % i for i in sat_zenith_angles]) + "_filename>")
    args = docopt.docopt(__doc__, version='0.1')
    if args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    LOG.info(args)

    # Append to output directory, if set.
    if args["--output-dir"] is not None:
        # Make sure that the output directory exits.
        if not os.path.isdir(args["--output-dir"]):
            # Create the output directory.
            LOG.error("Output directory, '%s', did not exist. Creating it." % args["--output-dir"])
            raise RuntimeException("Directory '%s' does not exist." % args["--output-dir"])

    # Init values.
    values_from_files = {}
    colors = {0: "r", 15: "g", 30: "b", 45: "m", 60: "c"}

    # Organize the values. That is, loading them in from the files in a specific way.
    for sat_zenith_angle in sat_zenith_angles:
        values_from_files["sat_zen_%02i" % (sat_zenith_angle)] = \
            load_values_from_file(args["<emissivity_sat_zen_%02i_filename>" % 
                                       (sat_zenith_angle)])

    # The following two uncommented lines were used for validation.
    # Calculating the stats for each sat zenith angle.
    # stats_by_sat_zenith_angle = calc_stats(values_from_files)


    # Calculate the temperatures from the emissivity brightness temperatures.
    surface_temperatures_by_sat_zenith_angle = calculate_surface_temperatures_by_sat_zenith_angle(args["<satellite_id>"],
                                                                                                  int(args["<sun_zenith_angle>"]),
                                                                                                  sat_zenith_angles,
                                                                                                  values_from_files)

    # Create the histogram
    create_histogram(float(args["<sun_zenith_angle>"]), sat_zenith_angles, surface_temperatures_by_sat_zenith_angle, int(args["--dpi"]), args["--output-dir"])


    # Get the standard deviations.
    surface_temperature_stds = get_surface_temperature_stds(surface_temperatures_by_sat_zenith_angle, sat_zenith_angles)

    # Create the plot.
    create_line_plot(float(args["<sun_zenith_angle>"]), sat_zenith_angles, surface_temperature_stds, int(args["--dpi"]), args["--output-dir"])
