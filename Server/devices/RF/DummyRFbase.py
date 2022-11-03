"""
Created on Aug 26, 2021.
@author: Jiyong Kang
@Editor: Kyungmin Lee
This file includes abstract classes, which are base classes for other
concrete classes.
Included classes:
    - SerialPortRFSource
    - SocketPortRFSource
"""

import serial, socket
import serial.tools.list_ports as sp


class RFSource:
    """
    This class is an interface for interacting with RF source devices.
    - Every class implementing RFsource device should inherit this class.
    - Note that exceptions may occur in each method depending on devices.
    - Default units
        - power:        dBm
        - frequency:    Hz
        - phase:        degree
    """

    def __init__(self, min_power, max_power, min_freq, max_freq):
        # device properties
        self.__min_power = min_power
        self.__max_power = max_power
        self.__min_freq = min_freq
        self.__max_freq = max_freq

    def connect(self):
        """Connects to the device."""
        not_implemented('connect', self)

    def disconnect(self):
        """Disconnects from the device."""
        not_implemented('disconnect', self)

    def is_connected(self) -> bool:
        """Returns whether the device is currently connected."""
        not_implemented('is_connected', self)

    def enable_output(self):
        """Enables the output of the device."""
        not_implemented('enable_output', self)

    def disable_output(self):
        """Disables the output of the device."""
        not_implemented('disable_output', self)

    def is_output_enabled(self) -> bool:
        """Returns whether the device output is currently enabled."""
        not_implemented('is_output_enabled', self)

    def setPower(self, power: float):
        """Applies power as given, in dBm."""
        not_implemented('apply_power', self)

    def setFrequency(self, freq: float):
        """Applies frequency as given, in Hz."""
        not_implemented('apply_frequency', self)

    def setPhase(self, phase: float):
        """Applies phase as given, in degrees."""
        not_implemented('apply_phase', self)

    def getPower(self) -> float:
        """Returns the current power of the output in dBm."""
        not_implemented('read_power', self)

    def getFrequency(self) -> float:
        """Returns the current frequency of the output in Hz."""
        not_implemented('read_frequency', self)

    def getPhase(self) -> float:
        """Returns the current phase of the output in degrees."""
        not_implemented('read_phase', self)

    def is_locked(self) -> bool:
        """Returns whether the current output is locked."""
        not_implemented('is_locked', self)

    @property
    def min_power(self) -> float:
        """Returns minimum power limit of the device in dBm."""
        return self.__min_power

    @property
    def max_power(self) -> float:
        """Returns maximum power limit of the device in dBm."""
        return self.__max_power

    @property
    def min_frequency(self) -> float:
        """Returns minimum frequency limit of the device in Hz."""
        return self.__min_freq

    @property
    def max_frequency(self) -> float:
        """Returns maximum frequency limit of the device in Hz."""
        return self.__max_freq


class SerialPortRFSource(RFSource):
    """
    This class is an abstract class for the devices which use serial port
    communication.
    Package 'serial' is required.
    This inherits RFSource, hence a lot of abstract methods exist.
    However, some of them are implemented(overridden):
    - connect
    - disconnect
    - is_connected
    These are an additional public property which is not in RFSource interface:
    - port (setter, getter)
    Moreover, this class provides some protected methods:
    - _send_command
    - _query_command
    """
    def __init__(self, min_power, max_power, min_freq, max_freq,
                 port=None, **serial_kwargs):
        """Initializes object properties.
        serial.Serial object is created without connection.
        Even if the given port is not None, Serial constructor calls open()
        when the port is not None, hence it gives the port after construction.
        Params:
            port - serial port name e.g. 'COM32'.
                   when it is None, it can be set later.
            **serial_kwargs - keyword arguments for Serial constructor.
        """
        super().__init__(min_power, max_power, min_freq, max_freq)
        self.__connected = False
        self.__port = port

    def connect(self):
        print('connected')
        self.__connected = True

    def disconnect(self):
        print('disconnected')
        self.__connected = False

    def is_connected(self) -> bool:
        return self.__connected

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, port):
        """Sets serial port.
        When the port is currently open, the current port is closed and it
        opens the given port.
        """
        self.__port = port

    """
    Protected methods
    Methods below are for classes which inherit this class.
    """
    def _send_command(self, cmd, encoding='ascii') -> bool:
        print('Command: {}'.format(cmd))
        return True

    def _query_command(self, cmd, encoding='ascii',
                       terminator='\r\n', size=1, trim=True):
        print('Command: {}'.format(cmd))
        return True

class SocketRFSource(RFSource):
    def __init__(
        self, min_power, max_power, min_freq, max_freq, tcp_ip="", tcp_port=0
    ):
        super().__init__(min_power, max_power, min_freq, max_freq)
        self.__connected = False
        self.__tcp_ip = tcp_ip
        self.tcp_port = tcp_port

    def connect(self, *args, **kwargs):
        print('connected')
        self.__connected = True

    def disconnect(self):
        print('disconnected')
        self.__connected = False

    def is_connected(self):
        return self.__connected

    @property
    def tcp_ip(self):
        return self.__tcp_ip

    @tcp_ip.setter
    def tcp_ip(self, tcp_ip):
        self.__tcp_ip = tcp_ip

    @property
    def tcp_port(self) -> int:
        return self.__tcp_port

    @tcp_port.setter
    def tcp_port(self, tcp_port):
        try:
            self.__tcp_port = int(tcp_port)
        except:
            TypeError("tcp_port shoule be either number type or string of number")

    def _send_command(self, cmd, encoding="ascii"):
        print('Command: {}'.format(cmd))
        return True

    def _query_command(
            self, cmd, encoding="ascii", terminator="\n", size=1, bufsize=1024, trim=True):
        print('Command: {}'.format(cmd))
        return True




def not_implemented(func, obj):
    """Raises NotImplementedError with the given function name.
    This is a helper function, which is NOT included in RFSource class.
    """
    raise NotImplementedError("method '{}' is not supported on device '{}'"
                              .format(func, obj.__class__.__name__))