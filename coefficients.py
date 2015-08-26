#!/usr/bin/env python
# coding: utf-8
import os
import numpy as np

class Coefficients(object):
    DEFAULT_COEFFICIENT_FILE = "calibration_nh_ktuned_20140814.txt"

    def __init__(self,
                 sat_id,
                 filename = DEFAULT_COEFFICIENT_FILE,
                 split_text="##1 COMMENT LINE ONLY::"):
        self.sat_id = sat_id
        self.filename = filename
        self.split_text = split_text
        assert(self.sat_id in [id for id in Coefficients.satellite_ids(filename)])

    def __enter__(self):
        with open(self.filename, 'r') as fp:
            # Header line
            line = fp.readline()
            headers = self.get_headers(line)

            sat_found = False
            for line in fp:
                if line.split()[0] == self.sat_id:
                    for header, value in zip(headers, line.split()):
                        self.__dict__[header] = value
                    sat_found = True
                    break
            assert(sat_found)
        return self

    def __exit__(self, type, value, traceback):
        pass
        
    def get_headers(self, line):
        assert(self.split_text in line)
        return line.split(self.split_text, 1)[1].split()

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__self__()

    @staticmethod
    def satellite_ids(filename = DEFAULT_COEFFICIENT_FILE):
        assert(os.path.isfile(filename))
        with open(filename, 'r') as fp:
            line = fp.readline()
            for line in fp:
                if not line.startswith("#") and line.strip() != "":
                    yield line.split()[0]


    def get_night_coefficients(self):
        a_n = self.a_sst_night
        b_n = self.b_sst_night
        c_n = self.c_sst_night
        d_n = self.d_sst_night
        e_n = self.e_sst_night
        f_n = self.f_sst_night
        cor_n = self.gain_sst_night * s_teta + self.offset_sst_night

    def get_day_coefficients(self):
        a_d = self.a_sst_day
        b_d = self.b_sst_day
        c_d = self.c_sst_day
        d_d = self.d_sst_day
        e_d = self.e_sst_day
        f_d = self.f_sst_day
        g_d = self.g_sst_day

    def get_coefficient(self, T11):
        # /* coefficients for noaa 12 from Key et al 1997 */
        if T11 < 240.0:
            a = self.a_ist_lss240
            b = self.b_ist_lss240
            c = self.c_ist_lss240
            d = self.d_ist_lss240
        elif (T11 >= 240.0 && T11 < 260.0):
            a = self.a_ist_range240_260
            b = self.b_ist_range240_260
            c = self.c_ist_range240_260
            d = self.d_ist_range240_260
        else:
            a = self.a_ist_grt260
            b = self.b_ist_grt260
            c = self.c_ist_grt260
            d = self.d_ist_grt260
        return a, b, c, d


        

if __name__ == "__main__":
    """
    Kind of a test...
    """
    try:
        Coefficients("noaa3")
    except AssertionError, e:
        pass
    else:
        raise Exception("Should fail.")

    c = Coefficients("noaa7")
    with c:
        print c.__dict__

    with Coefficients("noaa9") as c:
        print c.__dict__
    with Coefficients("noaa11") as c:
        print c.__dict__
