# -*- coding: utf-8 -*-
"""
Created on Wed Jan  3 16:14:43 2024

@author: QCP75
"""
from PyQt5.QtCore import QObject

class RF_Device_Client(QObject):
    
    _device_parameters = ["out",
                          "power",
                          "freq",
                          "phase",
                          "max_power"]
    
    def __init__(self, parent, device_nick, device_type, num_channels):
        super().__init__()
        self.settings = {}
        self.parent = parent
        self.gui_update_signal = self.parent._gui_update_signal
        
        self.device_nick = device_nick
        self.device_type = device_type
        self.num_channels = num_channels
        
        self._setupDevice(self.num_channels)
        
    def __call__(self):
        return self.settings
        
    def _setupDevice(self, num_channels=1):
        for ch in range(num_channels):
            self.settings[ch] = {param: None for param in self._device_parameters}
            self.settings[ch]["out"] = False
            
    def setValue(self, param, value, channel=0):
        if param in ["o", "out"]:
            self.setOutput(value, channel)
        elif param in ["p", "power"]:
            self.setPower(value, channel)
        elif param in ["f", "freq", "frequency"]:
            self.setFrequency(value, channel)
        elif param in ["ph", "phase"]:
            self.setPhase(value, channel)
        elif param in ["mp", "max_power"]:
            self.setMaxPower(value, channel)
        else:
            raise ValueError("An Unknown parameter has been found whild handling the RF client (%s, %s)" % (self.device_nick, param))
            return
            
        k = param[0]
        self.gui_update_signal.emit(self.device_nick, k, value, channel)
            
    def setOutput(self, output, channel=0):
        self.settings[channel]["out"] = output
        
    def setPower(self, power, channel=0):
        self.settings[channel]["power"] = power
        
    def setFrequency(self, frequency, channel=0):
        self.settings[channel]["freq"] = frequency
        
    def setPhase(self, phase, channel=0):
        self.settings[channel]["phase"] = phase
        
    def setMaxPower(self, max_power, channel=0):
        self.settings[channel]["max_power"] = max_power
        
    def getValue(self, parameter, channel=0):
        if parameter == "frequency":
            parameter = "freq"
            
        return self.settings[channel][parameter]
        