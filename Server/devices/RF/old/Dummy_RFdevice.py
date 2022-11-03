"""
Created on Aug 26, 2021.
@author: Jiyong Kang
@Editor: Kyungmin Lee
This file includes concrete classes implementing actual or virtual RF source device.
Included classes:
    - Windfreak SynthNV(SerialPortRFSource)
"""

import math
import numpy as np


def requires_connection(func):
    """Decorator that checks the connection before calling func.
    Raises:
        RuntimeError - the func is called without connection.
    """
    def wrapper(self, *args):
        if self.is_connected():
            return func(self, *args)
        else:
            raise RuntimeError('{} is called with no connection.'
                               .format(func.__name__))
    return wrapper

def check_range(val, min_, max_, label=None):
    """Checks the given value fits in the range [min_, max_].
    Raises:
        ValueError - val does not fit in the range.
    """
    if val > max_ or val < min_:
        raise ValueError('{}{} is out of range: min={}, max={}.'
                         .format('' if label is None else label + '=',
                                 val, min_, max_))

def find_nearest_idx(array, value):
    return (np.abs(array - value)).argmin()

class WindfreakTech():
    """
    This class is for Windfreak Tech rf devices which is used for sideband generator.
    All the commands and behaviours are currently based on serial communication manual.

    - Default units
        - power:        dBm
        - frequency:    Hz
        - attenuator:   dBm
    """
    def __init__(self, min_power, max_power, min_freq, max_freq, port=None, device_name=None):
        """
        The serial port can be assigned later by set_port(port_name).
        """
        self.min_power, self.max_power = min_power, max_power
        self.min_frequency, self.max_frequency = min_freq, max_freq
        self.__output_enabled = False
        self.__power = min_power
        self.__freq = 1000e6 # 1GHz
        self.device_name = device_name[-2:]
        self.__chan = 'A'
        self.__is_connected = False
        self.__output_enabled = False
        
        if self.device_name == 'NV':
            self.__power_dbm_list = np.linspace(-13.49, 18.35, 64)

    
    def connect(self):
        """Overrides connect() of SerialPortRFSource.
        """
        if self.is_connected():
            print('Already Connected')
        else:
            self.__is_connected = True
            print('Connected')
        self.__init()
        
    def disconnect(self):
        """Overrides disconnect() of SerialPortRFSource.
        """
        if self.is_output_enabled():
            self.disable_output()
        if self.is_connected():
            self.__is_connected = False
            print("The device is closed.")
        else:
            print("The device is alrady closed.")

    def __init(self):
        self.setPower(self.__power)
        self.setFrequency(self.__freq)
        
    @requires_connection
    def enableOutput(self):
        """Enables the output by applying the power as self.__power.
        Raises:
            AssertError - power must be set before enabling the output.
        """
        if not self.__output_enabled:
            if self.device_name == 'NV':
                self.__output_enabled = True
                print('Output Enabled')
            if self.device_name == 'HD':
                self.__output_enabled = True
                print('Output Enabled')

    @requires_connection
    def disableOutput(self):
        """Simply applies the power to be zero.
        """
        if self.__output_enabled:
            if self.device_name == 'NV':
                self.__output_enabled = False
                print('Output Disnabled')
            if self.device_name == 'HD':
                self.__output_enabled = False
                print('Output Disabled')

    @requires_connection
    def setPower(self, power):
        """Sends the command only if the output is currently enabled.
        Raises:
            ValueError - power is out of range.
        """
        check_range(power, self.min_power, self.max_power, 'power')
        if self.device_name == 'NV':
            self.__power_idx = find_nearest_idx(self.__power_dbm_list, power)
            self.__power = self.__power_dbm_list[self.__power_idx]
            print('Power set as {}'.format(round(self.__power,2)))
        
        elif self.device_name == 'HD':
            power = round(power, 3)
            self.__power = power
            print('Power set as {}'.format(self.__power))

    @requires_connection
    def setFrequency(self, freq: float):
        """
        Raises:
            ValueError - freq is out of range.
        """
        freq = round(freq, 1)
        self.__freq = freq
        check_range(freq, self.min_frequency, self.max_frequency, 'frequency')
        print('Frequency set as {} MHz'.format(freq/1e6))

    @requires_connection
    def setChannel(self, chan: str):
        if self.device_name == 'HD':
            if chan == 'A' or chan == 'a':
                print('Set Channel: {}'.format(chan))
            elif chan == 'B' or chan == 'b':
                print('Set Channel: {}'.format(chan))
            else:
                print('Wrong Channel Index')
            self.__chan = chan
        else:
            e = 'No Channel Available for Synth' + self.device_name
            print(e)
        
    @requires_connection
    def getPower(self) -> float:
        if self.device_name == 'NV':  
            power = self.__power
            print(self.__power)
            return round(self.__power,2)

        elif self.device_name == 'HD':         
            power = self.__power
            print(power)
            return power
    
    @requires_connection
    def getFrequency(self) -> str:
        freq = self.__freq
        return freq * 1e6 # Turn to Hz
    
    @requires_connection
    def getChannel(self) -> str:
        if self.device_name == 'HD':
            chan = self.__chan
            print('Channel: {}'.format(chan))
            return chan
        else:
            pass

    @requires_connection
    def is_output_enabled(self) -> bool:
        return self.__output_enabled

    def is_connected(self):
        return self.__is_connected
    
    @property
    def power_dbm_list(self):
        if self.device_name == 'NV':
            return self.__power_dbm_list
        elif self.device_name == 'HD':
            print('SynthHD has no power dbm list')

class SynthNV(WindfreakTech):
    """
    Power range: [0 63] for [-13.49, +18.55] dBm
    Frequency range: [34e6, 4.5e9] Hz
    """
    def __init__(self, port=None, min_power=-13.49, max_power=18.55, 
                 min_freq=34e6, max_freq=4.5e9):
        assert min_power >= -13.49, 'min_power should be at least 0(-13.49dBm).'
        assert max_power <= 18.55, 'max_power should be at most 63(18.55dBm).'
        assert min_freq >= 34e6, 'min_frequency should be at least 34MHz.'
        assert max_freq <= 4.5e9, 'max_frequency shuold be at most 4500MHz.'
        assert min_power <= max_power, 'min_power is greater than max_power.'
        assert min_freq <= max_freq, 'min_frequency is greater than max_frequency.'
        super().__init__(min_power, max_power, min_freq, max_freq, port=port, device_name='SynthNV')


class SynthHD(WindfreakTech):
    """
    Power range: [-50, +20] dBm 0.001dB resolution
    Frequency range: [10e6, 15e9] Hz 0.1Hz resolution
    """
    def __init__(self, port=None, min_power=-50, max_power=20, 
                 min_freq=10e6, max_freq=15e9):
        assert min_power >= -50, 'min_power should be at least -50dBm.'
        assert max_power <= 20, 'max_power should be at most 20dBm.'
        assert min_freq >= 10e6, 'min_frequency should be at least 34MHz.'
        assert max_freq <= 15e9, 'max_frequency shuold be at most 4500MHz.'
        assert min_power <= max_power, 'min_power is greater than max_power.'
        assert min_freq <= max_freq, 'min_frequency is greater than max_frequency.'
        super().__init__(min_power, max_power, min_freq, max_freq, port=port, device_name='SynthHD')