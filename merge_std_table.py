import os
import glob
import logging
LOG=logging.getLogger(__name__)


if __name__ == "__main__":
    import docopt
    __doc__ = """
File: {filename}

Usage:
  {filename} <stat-files-dir> [<output-filename>] [-d|-v] [options]
  {filename} (-h | --help)
  {filename} --version

Options:
  -h --help                  Show this screen.
  --version                  Show version.
  -v --verbose               Show some diagostics.
  -d --debug                 Show some more diagostics.
  -f --force                 Remove existing ouput file.
""".format(filename=__file__)
    args = docopt.docopt(__doc__, version='0.1')
    if args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    elif args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    LOG.info(args)

    if os.path.isfile(args["<output-filename>"]):
        if args["--force"]:
            os.remove(args["<output-filename>"])
        else:
            raise RuntimeError("File already exists: %s. Use -f to overwrite." % (args["<output-filename>"]))
        
    std_index = 2
    algos = ["satellite_id",]

    first_file = True
    for root, dirs, files in os.walk(args["<stat-files-dir>"]):
        files.sort()
        for f in files:
            res_list = []
            filename = os.path.join(root, f)
            LOG.debug("Opening %s" % (filename))
            with open(filename, "r") as fp:
                satellite_id = fp.next().strip("#").split()[0]
                LOG.debug("satellite_id: %s" % (satellite_id))
                res_list.append(satellite_id)
                assert("std" == fp.next().strip().strip("#").split()[std_index])
                for line in fp:
                    line = line.strip()
                    LOG.debug(line)
                    if first_file:
                        algos.append(line.strip().split()[0])
                    res_list.append(line.strip().split()[std_index])

            if args["<output-filename>"]:
                with open(args["<output-filename>"], 'a') as fp:
                    if first_file:
                        fp.write(" ".join(algos) + "\n")
                    fp.write(" ".join(res_list) + "\n")
                        
            else:
                if first_file:
                    print " ".join(algos)
                print " ".join(algos)

            first_file = False
    if args["<output-filename>"]:
        LOG.info("File written: %s." % args["<output-filename>"])
