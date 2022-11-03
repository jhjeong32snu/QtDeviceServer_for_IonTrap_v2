"""
Created on Aug 26, 2021.
@author: Jiyong Kang
@Editor: Kyungmin Lee
This file includes concrete classes implementing actual or virtual RF source device.
Included classes:
    - Windfreak SynthNV(SerialPortRFSource)
"""

import serial, socket, math
import numpy as np
from DummyRFbase import SerialPortRFSource, SocketRFSource


def requires_connection(func):
    """Decorator that checks the connection before calling func.
    Raises:
        RuntimeError - the func is called without connection.
    """
    def wrapper(self, *args, **kwargs):
        if self.is_connected():
            return func(self, *args, **kwargs)
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
        
def print_msg(src, msg):
    """Prints msg followed by src, in format
    [src]: msg
    Params:
        src - source object who emits the message.
        msg - message body.
    """
    print("[{}]: {}".format(src, msg))

def find_nearest_idx(array, value):
    return (np.abs(array - value)).argmin()

class WindfreakTech(SerialPortRFSource):
    """
    This class is for Windfreak Tech rf devices which is used for sideband generator.
    All the commands and behaviours are currently based on serial communication manual.

    - Default units
        - power:        dBm
        - frequency:    Hz
        - attenuator:   dBm
    """
    def __init__(self, min_power, max_power, min_freq, max_freq,
                 output_enabled, power, freq, phase,
                 port=None, device_name=None):
        """
        The serial port can be assigned later by set_port(port_name).
        """
        super().__init__(min_power, max_power, min_freq, max_freq,
                         port=port, baudrate=9600, bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO)
        self.__output_enabled, self.__power, self.__freq, self.__phase = output_enabled, power, freq, phase
        self.device_name = device_name[-2:]
        if self.device_name == 'NV':
            self.__power_dbm_list = np.linspace(-13.49, 18.35, 64)\
        
    def __output_mapping(self, output_enabled, power, freq, phase):
        self.__output_enabled, self.__power, self.__freq, self.__phase = output_enabled, power, freq, phase
        
    @requires_connection
    def enableOutput(self, output_type:int=0):
        """Enables the output by applying the power as self.__power.
        Raises:
            AssertError - power must be set before enabling the output.
        """
        if not self.__output_enabled[output_type]:
            self.__output_enabled[output_type] = True

    @requires_connection
    def disableOutput(self, output_type:int=0):
        """Simply applies the power to be zero.
        """
        if self.__output_enabled[output_type]:
            self.__output_enabled[output_type] = False

    @requires_connection
    def setPower(self, power: float, output_type:int=0):
        """Sends the command only if the output is currently enabled.
        Raises:
            ValueError - power is out of range.
        """
        self.setChannel(output_type)
        check_range(power, self.min_power, self.max_power, 'power')
        if self.device_name == 'NV':
            power = round(power, 2)
            self.__power_idx = find_nearest_idx(self.__power_dbm_list, power)
            self.__power[output_type] = self.__power_dbm_list[self.__power_idx]
        
        elif self.device_name == 'HD':
            power = round(power, 2)
            self.__power[output_type] = power

    @requires_connection
    def setFrequency(self, freq: float, output_type:int=0):
        """
        Raises:
            ValueError - freq is out of range.
        """
        self.setChannel(output_type)
        freq = round(freq, 1)
        check_range(freq, self.min_frequency, self.max_frequency, 'frequency')
        self.__freq[output_type] = freq
    
    @requires_connection
    def setPhase(self, phase: float, output_type:int=0):
        self.setChannel(output_type)
        net_phase = float(phase % 360)
        self.__phase[output_type] = net_phase
    
    def setChannel(self, output_type):
        self.__curr_chan = output_type
    
    @requires_connection
    def getPower(self, output_type:int=0) -> float:
        """Caution: this may return None when the output has been disabled
        during the whole connection and the power has never been set.
        """
        return round(self.__power[output_type],2)
        
    @requires_connection
    def getFrequency(self, output_type:int=0) -> float:
        return round(self.__freq[output_type],2)
            
    def getPhase(self, output_type:int=0) -> float:
        return self.__phase[output_type]

    @requires_connection
    def is_output_enabled(self, output_type:int=0) -> bool:
        return self.__output_enabled[output_type]

    """
    Following two private methods are wrappers for the protected methods
    _send_command and _query_command, respectively.
    These are just for convenience of writing codes.
    """

    def __send_command(self, cmd: str) -> bool:
        """Sends command in the device protocol, such as terminators, etc.
        This private method simply appends a space and a terminator.
        The device does not take the command if there is no space in front
        of the terminator.
        """
        return self._send_command(cmd, encoding='ascii')

    def __query_command(self, cmd: str, size=1, trim=True):
        """Sends command and receives the response, through the device
        protocol.
        This private method simply appends a space and a terminator at the
        end of the command, just like self.__send_command does.
        """
        return self._query_command(cmd, encoding='ascii',
                                   terminator='\n', size=size, trim=trim)
    
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
        self.__output_mapping(min_power)
        super().__init__(min_power, max_power, min_freq, max_freq, 
                         self.__output_enabled, self.__power, self.__freq, self.__phase,
                         port=port, device_name='SynthNV',
                         )

    def __output_mapping(self, min_power):
        # Possible output number for power/freq/phase
        self._num_power = 1
        self._num_freq = 1
        self._num_phase = 1
        self._output_mapping = {
            'power':{0:'Single'},
            'freq':{0:'Single'},
            'phase':{0:'Single'}
            }
        self.__output_enabled = [False]
        self.__power = [min_power]
        self.__freq = [1000e6] # 1GHz
        self.__phase = [0]

class SynthHD(WindfreakTech):
    """
    Power range: [0 63] for [-50, +20] dBm 0.001dB resolution
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
        self.__output_mapping(min_power, min_freq)
        super().__init__(min_power, max_power, min_freq, max_freq,
                         self.__output_enabled, self.__power, self.__freq, self.__phase,
                         port=port, device_name='SynthHD')
 
    def __output_mapping(self, min_power, min_freq):
        # Possible output number for power/freq/phase
        self._num_power = 2
        self._num_freq = 2
        self._num_phase = 2
        self._output_mapping = {
            'power':{0:'Channel A', 1:'Channel B'},
            'freq':{0:'Channel A', 1:'Channel B'},
            'phase':{0:'Channel A', 1:'Channel B'}
            }
        self.__output_enabled = [False for i in range(self._num_power)]
        self.__power = [min_power for i in range(self._num_power)]
        self.__freq = [min_freq for i in range(self._num_freq)]
        self.__phase = [0 for i in range(self._num_phase)]

class APSYNxxx(SocketRFSource):
    """
    This class is for APSYN series devices, which are high frequency signal generators
    from AnaPico.
    All the commands and behaviours are currently based on 'Programmer’s Manual V2.03
    Signal Source Models'.
    Methods:
        - enable/disable_output
        - is_output_enabled
        - set/getFrequency
        - set/getPhase
        - lockFrequency
        - is_locked
    """
    def __init__(
            self, min_power, max_power, min_freq, max_freq,
            output_enabled, power, freq, phase,
            tcp_ip="", tcp_port=""):
        """
        tcp_ip and tcp_port can be assigned later by setters.
        """
        super().__init__(min_power, max_power, min_freq, max_freq,
                         tcp_ip=tcp_ip, tcp_port=tcp_port)
        self.__output_enabled, self.__power, self.__freq, self.__phase = output_enabled, power, freq, phase
        
    @requires_connection
    def enableOutput(self, output_type:int=0):
        self.__send_command(":OUTPut 1")
        self.__output_enabled[output_type] = True

    @requires_connection
    def disableOutput(self, output_type:int=0):
        self.__send_command(":OUTPut 0")
        self.__output_enabled[output_type] = False

    @requires_connection
    def is_output_enabled(self, output_type:int=0) -> bool:
        return self.__output_enabled[output_type]

    @requires_connection
    def setFrequency(self, freq: float, output_type:int=0):
        """
        Frequency unit: Hz
        Raises:
            ValueError - target frequency is out of range.
        """
        check_range(freq, self.min_frequency, self.max_frequency, "frequency")
        self.__send_command(f":FREQuency {freq:.2f}")
        self.__freq[output_type] = freq

    @requires_connection
    def setPower(self, power: float, output_type:int=0):
        """
        APSYN power is not adjustable
        """
        self.__power[output_type] = 23
        pass
    
    @requires_connection
    def setPhase(self, phase: float, output_type:int=0):
        phase_net = (phase % 360)
        self.__phase[output_type] = phase_net

    @requires_connection
    def getFrequency(self, output_type:int=0) -> float:
        """
        Frequency unit: Hz
        """
        return self.__freq[output_type]

    @requires_connection
    def getPower(self, output_type:int=0):
        """
        APSYN power is fixed as 23dBm
        """
        return self.__power[output_type]
    

    @requires_connection
    def getPhase(self, output_type:int=0) -> float:
        """
        Phase unit: degree
        """
        # Converts radian to degree
        return self.__phase[output_type]

    @requires_connection
    def lockFrequency(self, ext_ref_freq=10e6):
        """
        Conveys the expected reference frequency value of an externally applied reference
        to the signal generator.
        Frequency range: 1MHz - 250MHz (default: 10MHz)
        Raises:
            ValueError - ext_ref_freq is out of range.
        """
        check_range(ext_ref_freq, 1e6, 250e6, "external reference frequency")
        self.__send_command(f":ROSCillator:EXTernal:FREQuency {ext_ref_freq:.0f}")

    @requires_connection
    def is_locked(self) -> bool:
        return "1" == self.__query_command(":ROSCillator:LOCKed?")

    """
    Following two private methods are wrappers for the protected methods
    _send_command and _query_command, respectively.
    These are just for convenience of writing codes.
    """
    def __send_command(self, cmd: str) -> bool:
        """
        Sends command in the device protocol, such as terminators, etc.
        This private method simply appends a terminator.
        """
        return self._send_command(cmd + "\n", encoding="ascii")

    def __query_command(self, cmd: str, size=1, trim=True):
        """
        Sends command and receives the response, through the device
        protocol.
        This private method simply appends a terminator at the
        end of the command, just like self.__send_command does.
        """
        return self._query_command(
            cmd + "\n", encoding="ascii", terminator="\n", size=size, trim=trim)


class APSYN420(APSYNxxx):
    """
    This class implements a particular device, APSYN420, which is in the APSYNxxx series.
    Power is not adjustable(+23dBM).
    Frequency range: [0.01e9, 20.0e9] Hz
    Frequency resolution: 0.001Hz
    Phase resolution: 0.1 deg
    """
    def __init__(
            self, min_freq=10e6, max_freq=20.0e9, tcp_ip="", tcp_port=""):
        assert min_freq >= 10e6, "min_frequency should be at least 10MHz."
        assert max_freq <= 20.0e9, "max_frequency shuold be at most 20.0GHz."
        assert min_freq <= max_freq, "min_frequency is greater than max_frequency."
        self.__output_mapping(23, min_freq)
        super().__init__(None, None, min_freq, max_freq, 
                         self.__output_enabled, self.__power, self.__freq, self.__phase,
                         tcp_ip=tcp_ip, tcp_port=tcp_port)
        

    def __output_mapping(self, min_power, min_freq):
        # Possible output number for power/freq/phase
        self._num_power = 1
        self._num_freq = 1
        self._num_phase = 1
        self._output_mapping = {
            'power':{0:'Single'},
            'freq':{0:'Single'},
            'phase':{0:'Single'}
            }
        self.__output_enabled = [False for i in range(self._num_power)]
        self.__power = [min_power for i in range(self._num_power)]
        self.__freq = [min_freq for i in range(self._num_freq)]
        self.__phase = [0 for i in range(self._num_phase)]


class SG38x(SocketRFSource):
    """
    This class is for SG38x series devices, which are high frequency signal
    generators from Stanford Research Systems(SRS).
    All the commands and behaviours are currently based on SG384 manual.
    Methods:
        - enable/disable_output
        - is_output_enabled
        - set/getPower
        - set/getFrequency
        - set/getPhase
    """
    def __init__(
            self, min_power, max_power, min_freq, max_freq, 
            output_enabled, power, freq, phase,
            tcp_ip="", tcp_port=""):
        """
        tcp_ip and tcp_port can be assigned later by setters.
        """
        super().__init__(min_power, max_power, min_freq, max_freq,
                         tcp_ip=tcp_ip, tcp_port=tcp_port)
        self.__output_enabled, self.__power, self.__freq, self.__phase = output_enabled, power, freq, phase
        
    @requires_connection
    def enableOutput(self, output_type:int=0):
        if output_type == 0: # BNC
            self.__send_command("ENBL 1")
        elif output_type == 1: # N-Type
            self.__send_command("ENBR 1")
        else:
            raise ValueError('Undefined output type')
        self.__output_enabled[output_type] = True

    @requires_connection
    def disableOutput(self, output_type:int=0):
        if output_type == 0: # BNC
            self.__send_command("ENBL 0")
        elif output_type == 1: # N-Type
            self.__send_command("ENBR 0")
        else:
            raise ValueError('Undefined output type')
        self.__output_enabled[output_type] = False

    @requires_connection
    def is_output_enabled(self, output_type:int=0) -> bool:
        return self.__output_enabled[output_type]

    @requires_connection
    def setPower(self, power: float, output_type:int=0):
        """
        Power unit: dBm
        output type: BNC(0) / N-Type(1)
        Raises:
            ValueError - power is out of range.
        """
        check_range(power, self.min_power, self.max_power, "power")
        self.__power[output_type] = power

    @requires_connection
    def setFrequency(self, freq: float, output_type:int=0):
        """
        Frequency unit: Hz
        Raises:
            ValueError - frequency is out of range.
        """
        check_range(freq, self.min_frequency, self.max_frequency, "frequency")
        if freq >= 3e9:
            print_msg(self, "Warning - power may decrease above 3 GHz.")
        self.__freq[output_type] = freq

    @requires_connection
    def setPhase(self, phase: float, output_type:int=0):
        """
        Phase unit: degree
        Phase resolution:
            - DC to 100MHz -> 0.01
            - 100MHz to 1GHz -> 0.1
            - 1GHz to 8.1GHz -> 1
        """
        net_phase = phase % 360
        self.__phase[output_type] = net_phase

    @requires_connection
    def getPower(self, output_type:int=0) -> float:
        """
        Power unit: dBm
        output type: BNC(0) / N-Type(1)
        """
        return self.__power[output_type]

            
    @requires_connection
    def getFrequency(self, output_type:int=0) -> float:
        """
        Frequency unit: Hz
        """
        return self.__freq[output_type]

    @requires_connection
    def getPhase(self, output_type:int=0) -> float:
        """
        Phase unit: degree
        """
        return self.__phase[output_type]

    def __send_command(self, cmd: str) -> bool:
        """
        Sends command in the device protocol, such as terminators, etc.
        This private method simply appends a terminator.
        """
        return self._send_command(cmd + "\n", encoding="ascii")

    def __query_command(self, cmd: str, size=1, trim=True):
        """
        Sends command and receives the response, through the device
        protocol.
        This private method simply appends a terminator at the
        end of the command, just like self.__send_command does.
        """
        return self._query_command(
            cmd + "\n", encoding="ascii", terminator="\r\n", size=size, trim=trim)


class SG384(SG38x):
    """
    This class implements a particular device, SG384, which is in the SG38x series.
    Power range (Type-N): [-110, +16.50] dBm to [-110, +13] dBm over 3GHz
    Power range (BNC): [-47, +13] dBm
    Power resolution 0.01 dBm
    Frequency range (Type-N): [950kHz, 4.050GHz]
    Frequency range (BNC): [DC, 62.5MHz]
    Frequency resolution: 0.000001 Hz (1uHz)
    ==> I Set Power & Frequency Range with narrower bound
    """
    def __init__(
            self, min_power=-47, max_power=13, min_freq=950e3, max_freq=62.5e6,
            tcp_ip="", tcp_port=""):
        assert min_power >= -47, "min_power should be at least -47dBm."
        assert max_power <= 13, "max_power should be at most 16.50dBm."
        assert min_freq >= 950e3, "min_frequency should be at least 950kHz."
        assert max_freq <= 62.5e6, "max_frequency shuold be at most 62.5MHz."
        assert min_power <= max_power, "min_power is greater than max_power."
        assert min_freq <= max_freq, "min_frequency is greater than max_frequency."
        self.__output_mapping(min_power, min_freq)
        super().__init__(min_power, max_power, min_freq, max_freq, 
                         self.__output_enabled, self.__power, self.__freq, self.__phase,
                         tcp_ip=tcp_ip, tcp_port=tcp_port)
        
    def __output_mapping(self, min_power, min_freq):
        # Possible output number for power/freq/phase
        self._num_power = 2
        self._num_freq = 1
        self._num_phase = 1
        self._output_mapping = {
            'power':{0:'BNC', 1:'NTYPE'},
            'freq':{0:'Common'},
            'phase':{0:'Common'}
            }
        self.__output_enabled = [False for i in range(self._num_power)]
        self.__power = [min_power for i in range(self._num_power)]
        self.__freq = [min_freq for i in range(self._num_freq)]
        self.__phase = [0 for i in range(self._num_phase)]
