#!/usr/bin/env python
# coding: utf-8
import os
import numpy as np


class CoefficientsException(Exception):
    pass


class Coefficients(object):
    DEFAULT_COEFFICIENT_FILE = "calibration_nh_ktuned_20140814.txt"

    def __init__(self,
                 sat_id,
                 filename=DEFAULT_COEFFICIENT_FILE,
                 split_text="::"):
        self.sat_id = sat_id
        self.filename = filename
        assert(os.path.isfile(self.filename))
        self.split_text = split_text

        if self.sat_id not in [id for id in
                               Coefficients.satellite_ids(self.filename)]:
            raise CoefficientsException("Satellite id, '%s', must be one of "
                                        "'%s'. Config file used: %s." % (
                    self.sat_id,
                    "', '".join(Coefficients.satellite_ids(self.filename)),
                    self.filename
                    ))

    def __enter__(self):
        with open(self.filename, 'r') as fp:
            # Header line
            line = fp.readline()
            headers = self.get_headers(line)

            sat_found = False
            for line in fp:
                if line.split()[0] == self.sat_id:
                    for header, value in zip(headers, line.split()):
                        try:
                            self.__dict__[header] = float(value)
                        except ValueError:
                            self.__dict__[header] = value
                    sat_found = True
                    break
            assert(sat_found)
        return self

    def __exit__(self, type, value, traceback):
        pass

    def get_headers(self, line):
        assert(self.split_text in line)
        assert(line.startswith("#"))
        comment, ids = line.split(self.split_text)
        return ids.split()

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return self.__self__()

    @staticmethod
    def _get_sat_index_from_comment_line(line):
        assert(line.startswith("#"))
        assert("::" in line)
        assert("sat_id" in line)
        comment, ids = line.split("::")
        return ids.split().index("sat_id")

    @staticmethod
    def satellite_ids(filename=DEFAULT_COEFFICIENT_FILE):
        assert(os.path.isfile(filename))
        with open(filename, 'r') as fp:
            line = fp.readline()
            sat_id_index = Coefficients._get_sat_index_from_comment_line(line)
            for line in fp:
                if not line.startswith("#") and line.strip() != "":
                    yield line.split()[sat_id_index]

    def get_sst_night_coefficients(self, s_teta):
        a_n = self.a_sst_night
        b_n = self.b_sst_night
        c_n = self.c_sst_night
        d_n = self.d_sst_night
        e_n = self.e_sst_night
        f_n = self.f_sst_night
        cor_n = self.gain_sst_night * s_teta + self.offset_sst_night
        return a_n, b_n, c_n, d_n, e_n, f_n, cor_n

    def get_sst_day_coefficients(self):
        a_d = self.a_sst_day
        b_d = self.b_sst_day
        c_d = self.c_sst_day
        d_d = self.d_sst_day
        e_d = self.e_sst_day
        f_d = self.f_sst_day
        g_d = self.g_sst_day
        return a_d, b_d, c_d, d_d, e_d, f_d, g_d

    def get_ist_coefficients(self, t11):
        # /* coefficients for noaa 12 from Key et al 1997 */
        if t11 < 240.0:
            a = self.a_ist_lss240
            b = self.b_ist_lss240
            c = self.c_ist_lss240
            d = self.d_ist_lss240
        elif t11 < 260.0:
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
