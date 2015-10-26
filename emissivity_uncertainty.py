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

    sat zenit angle 0:
      avg(tb_11_K), std(tb_11_K)
      avg(tb_12_K), std(tb_12_K)
      avg(tb_37_K), std(tb_37_K)

    sat zenit angle 30:
      avg(tb_11_K), std(tb_11_K)
      avg(tb_12_K), std(tb_12_K)
      avg(tb_37_K), std(tb_37_K)

    sat zenit angle 60:
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
            # Pick algorithm.
            tb_11_K = values["tb_11_K"][i]
            tb_37_K = values["tb_37_K"][i]
            algorithm = eustace.surface_temperature.select_surface_temperature_algorithm(
                sun_zenith_angle,
                tb_11_K,
                tb_37_K)

            t_clim_K = tb_11_K
            # Calculate the temperature.
            st_truth_K = eustace.surface_temperature.get_surface_temperature(algorithm,
                                                                             coeff,
                                                                             tb_11_K,
                                                                             values["tb_12_K"][i],  # tb_12_K,
                                                                             tb_37_K,
                                                                             t_clim_K,
                                                                             sun_zenith_angle,
                                                                             sat_zenith_angle)

            yield algorithm, st_truth_K


if __name__ == "__main__":
    import docopt
    __doc__ = """
File: {filename}

Usage:
  {filename} <satellite_id> <sun_zenith_angle> <emissivity_sat_zen_00_filename> <emissivity_sat_zen_30_filename> <emissivity_sat_zen_60_filename> [-d|-v] [options]
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help                                Show this screen.
  --version                                Show version.
  -v --verbose                             Show some diagostics.
  -d --debug                               Show some more diagostics.
  --dpi=dp                                 The dpi of the output image, [default: 300].
  --output-dir=<dir>                       Output directory.
""".format(filename=__file__)
    args = docopt.docopt(__doc__, version='0.1')
    if args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    LOG.info(args)

    values_from_file = {}
    sat_zenith_angles = [0, 30, 60]
    colors = {0: "r", 30: "g", 60: "b"}
    for sat_zenith_angle in sat_zenith_angles:
        values_from_file["sat_zen_%02i" % (sat_zenith_angle)] = load_values_from_file(args["<emissivity_sat_zen_%02i_filename>" % (sat_zenith_angle)])
    
    stats = calc_stats(values_from_file)

    for angle_key in stats.keys():
        for temp_key in stats[angle_key].keys():
            for stat_type in stats[angle_key][temp_key].keys():
                print angle_key, temp_key, stat_type, stats[angle_key][temp_key][stat_type]

    sat_zenith_angle_temps = {}
    # Calculate the temperatures.
    for sat_zenith_angle in sat_zenith_angles:
        surface_temperatures=[]
        i = 0
        for algorithm, st_truth in get_temperatures(args["<satellite_id>"],
                                                    int(args["<sun_zenith_angle>"]),  # sun_zenith_angle,
                                                    sat_zenith_angle,
                                                    values_from_file["sat_zen_%02i" % (sat_zenith_angle)],):
            if np.isnan(st_truth):
                LOG.debug("st_truth was NaN.")
                continue

            surface_temperatures.append(st_truth)
        sat_zenith_angle_temps[sat_zenith_angle] = np.array(surface_temperatures)
    st_stds = []
    st_avgs = []
    tb_stds = []
    tb_avgs = []
    for sat_zenith_angle in sat_zenith_angles:
        st_stds.append(np.std(sat_zenith_angle_temps[sat_zenith_angle]))
        st_avgs.append(np.average(sat_zenith_angle_temps[sat_zenith_angle]))
        tb_stds.append(np.std(values_from_file["sat_zen_%02i" % (sat_zenith_angle)]["tb_11_K"]))
        tb_avgs.append(np.average(values_from_file["sat_zen_%02i" % (sat_zenith_angle)]["tb_11_K"]))



    LOG.debug("Clearing plt")
    """
    plt.title("Std")
    plt.plot(sat_zenith_angles, st_stds, "r-", label="std(st)")
    plt.plot(sat_zenith_angles, tb_stds, "g-", label="std(tb_11_K)")

    plt.ylabel(r"$\mathtt{std}$")
    plt.xlabel(r"$\mathtt{sat\_zenit\_angle}$")
    plt.legend(loc="upper left")
    # plt.show()

    plt.clf()
    max_temp = -1e20
    min_temp = 1e20
    for sat_zenith_angle in sat_zenith_angles:
        max_temp = max(np.max(sat_zenith_angle_temps[sat_zenith_angle]), max_temp)
        min_temp = min(np.min(sat_zenith_angle_temps[sat_zenith_angle]), max_temp)

    _bins = np.linspace(min_temp, max_temp, 50)
    for sat_zenith_angle in sat_zenith_angles:
        plt.clf()
        for tb in ["tb_11_K", "tb_12_K", "tb_37_K"]:
            n, bins, patches = plt.hist(values_from_file["sat_zen_%02i" % (sat_zenith_angle)][tb],
                                        _bins,
                                        alpha=0.5,
                                        label=tb)
        plt.legend(loc="upper left")
        plt.show()
    """

    plt.clf()
    max_temp = -1e20
    min_temp = 1e20
    for sat_zenith_angle in sat_zenith_angles:
        max_temp = max(np.max(sat_zenith_angle_temps[sat_zenith_angle]), max_temp)
        min_temp = min(np.min(sat_zenith_angle_temps[sat_zenith_angle]), max_temp)

    #_bins = np.linspace(min_temp, max_temp, 100)
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
        
        # Avoid "offset xaxis".
        plt.gca().get_xaxis().get_major_formatter().set_useOffset(False)

        # Create a filename.
        filename = "emissivity_histogram_sat_zenit_angle_%02i" % sat_zenith_angle
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

        plt.title(r"$\mathtt{sat\_zenith\_angle:\ %02i}$" %(sat_zenith_angle))
        plt.ylabel(r"$\mathtt{N_{perturbations}}$")
        plt.xlabel(r"$\mathtt{sat\_zenith\_angle}$")
        x1,x2,y1,y2 = plt.axis()
        plt.axis((x1, x2, 0, 450))

        LOG.debug("Saving plot to %s" %(filename))
        plt.savefig(filename, dpi=int(args['--dpi']))
        
