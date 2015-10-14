import os
import logging
LOG = logging.getLogger("__name__")

SIGMAS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "NEdT_NOAAs.txt")
def get_sigmas(satellite_id):
    LOG.info("Getting sigmas for %s" % satellite_id)
    with open(SIGMAS_FILE) as fp:
        # Headerline
        header = fp.readline()
        header = header.split("::")[1]
        header_keys = header.split()
        
        # Read the values.
        for line in fp:
            line_parts = line.split()
            if line_parts[0] == satellite_id:
                sigmas = {}
                for i, key in enumerate(header_keys):
                    key = key.lower()
                    try:
                        sigmas[key] = float(line_parts[i])
                    except IndexError, e:
                        sigmas[key] = None
                    except Exception, e:
                        sigmas[key] = line_parts[i]
                return sigmas

    raise RuntimeError("Could not find sigmas for satellite: %s" % satellite_id)


if __name__ == "__main__":
    print get_sigmas("metop02")
