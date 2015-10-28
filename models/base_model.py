from abc import ABCMeta, abstractproperty

class BaseModel(object):
    __metaclass__ = ABCMeta

    @abstractproperty
    def satellite_id(self):
        raise NotImplementedError

    @abstractproperty
    def sun_zenith_angle(self):
        raise NotImplementedError

    @abstractproperty
    def sat_zenith_angle(self):
        raise NotImplementedError

    @abstractproperty
    def ch1(self):        
        raise NotImplementedError

    @abstractproperty
    def ch2(self):
        raise NotImplementedError

    @abstractproperty
    def ch3a(self):
        raise NotImplementedError

    @abstractproperty
    def ch3b(self):
        raise NotImplementedError

    @abstractproperty
    def ch4(self):
        raise NotImplementedError

    @abstractproperty
    def ch5(self):
        raise NotImplementedError

    @abstractproperty
    def lat(self):
        raise NotImplementedError

    @abstractproperty
    def lon(self):
        raise NotImplementedError

    @abstractproperty
    def cloudmask(self):
        raise NotImplementedError
