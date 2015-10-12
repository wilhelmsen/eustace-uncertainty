import os
import h5py
import numpy as np
from base_model import BaseModel
import eustace.surface_temperature

import logging
LOG = logging.getLogger(__name__)

class Hdf5(BaseModel):
    def __init__(self, avhrr_filename, sunsatangle_filename, cloudmask_filename):
        self.avhrr_filename = avhrr_filename
        self.sunsatangle_filename = sunsatangle_filename
        self.cloudmask_filename = cloudmask_filename

        self.avhrr_file = h5py.File(self.avhrr_filename, 'r')
        self.sunsatangle_file = h5py.File(self.sunsatangle_filename, 'r')
        self.cloudmask_file = h5py.File(self.cloudmask_filename, 'r')
        self.cache = {}

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        LOG.debug("Closing the files.")
        try:
            self.avhrr_file.close()
        except:
            LOG.error("Could not close cloud mask file.")

        try:
            self.sunsatangle_file.close()
        except:
            LOG.error("Could not close cloud mask file.")

        try:
            self.cloudmask_file.close()
        except:
            LOG.error("Could not close cloud mask file.")

    def __repr__(self):
        return "Measurements from %s" % self.satellite_id

    def _get_data(self, data_file, key):
        """
        Getting the data from the key from the specified data file.
        """
        if not self.cache.has_key(key):
            d = data_file[key]
            data_values = d["data"].value
            
            no_data_mask = data_values == d["what"].attrs["nodata"]
            missing_data_mask = data_values == d["what"].attrs["missingdata"]
            false_data_mask = no_data_mask | missing_data_mask
            data_values = np.where(false_data_mask, np.NaN, data_values)

            self.cache[key] = data_values * d["what"].attrs["gain"] + d["what"].attrs["offset"]
        return self.cache[key]
        
    def _get_avhrr_data(self, key):
        """
        Getting data from the avhrr file.
        """
        return self._get_data(self.avhrr_file, key)

    def _get_sun_sat_data(self, key):
        """
        Getting data from the sunsat file.
        """
        return self._get_data(self.sunsatangle_file, key)

    @property
    def satellite_id(self):
        key = "satetllite_id"
        if not self.cache.has_key(key):
            self.cache[key] = self.avhrr_file['how'].attrs['platform']
        return self.cache[key]

    @property
    def sun_zenit_angle(self):
        """
        image1, SUNZ
        # return self._get_sun_sat_angle_value("image1", "SUNZ")
        """
        return self._get_sun_sat_data("image1")

    @property
    def sat_zenit_angle(self):
        """
        image2, SATZ
        return self._get_sun_sat_angle_value("image2", "SATZ")
        """
        return self._get_sun_sat_data("image2")

    @property
    def ch1(self):        
        # 'image1:channel': '1', 'image1:description': 'AVHRR ch1',
        return self._get_avhrr_data("image1")

    @property
    def ch2(self):
        # 'image2:channel': '2', 'image2:description': 'AVHRR ch2',
        return self._get_avhrr_data("image2")

    @property
    def ch3b(self):
        # 'image3:channel': '3b', 'image3:description': 'AVHRR ch3b',
        return self._get_avhrr_data("image3")

    @property
    def ch3a(self):
        # 'image6:channel': '3a', 'image6:description': 'AVHRR ch3a',
        return self._get_avhrr_data("image6")

    @property
    def ch4(self):
        #  'image4:channel': '4', 'image4:description': 'AVHRR ch4',
        return self._get_avhrr_data("image4")

    @property
    def ch5(self):
        # 'image5:channel': '5', 'image5:description': 'AVHRR ch5',
        return self._get_avhrr_data("image5")

    @property
    def lon(self):
        return self._get_avhrr_data("where/lon")

    @property
    def lat(self):
        # h["where/lat/what"].attrs["gain"]
        return self._get_avhrr_data("where/lat")

    @property
    def cloudmask(self):
        key = "cloudmask"
        if not self.cache.has_key(key):
            self.cache[key] = self.cloudmask_file['cloudmask'].value
        return self.cache[key]


if __name__ == "__main__":
    import docopt
    __doc__ = """
File: {filename}

Usage:
  {filename} <avhrr_filename> <sunsatangle-filename> <cloudmask-filename> [-d|-v]
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
    with Hdf5(args["<avhrr_filename>"], args["<sunsatangle-filename>"], args["<cloudmask-filename>"]) as model:
        print len(model.cloudmask)
        idx = np.where(model.cloudmask == 3)
        # print idx
        for i in range(len(idx[0])):
            print model.cloudmask[idx[i][0]][idx[i][1]], \
                model.ch4[idx[i][0]][idx[i][1]], \
                model.ch5[idx[i][0]][idx[i][1]], \
                model.ch3b[idx[i][0]][idx[i][1]]
            import pdb; pdb.set_trace()



        import sys; sys.exit()

        print model.satellite_id
        print model
        print model.ch3b
        print model.ch3a
        print model.ch1
        print model.ch2
        print model.sun_zenit_angle
        print model.sat_zenit_angle
        print model.cloudmask
        print model.lat
        print model.lon
