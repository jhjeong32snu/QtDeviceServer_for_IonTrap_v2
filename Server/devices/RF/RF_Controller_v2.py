# -*- coding: utf-8 -*-
"""
@author: Junho Jeong
@Tel: 010-9600-3392
@email1: jhjeong32@snu.ac.kr
@mail2: bugbear128@gmail.com
"""

import time, os
from PyQt5.QtCore import QThread
import numpy as np
from queue import Queue
# from DummyRFdevice import *

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

from RFdevice import (SynthNV, SynthHD, SG384, APSYN420, Dummy_RF)


class RF_Controller(QThread):
    
    _client_list = []
    _status = "standby"
    # Available rf device model list
    avail_device_list = {'synthnv':"SynthNV", 
                         'synthhd':"SynthHD", 
                         'sg384':"SG384", 
                         'apsyn420':"APSYN420",
                         "dummy_rf": "Dummy_RF"}
    _config_options = ["curr_freq_hz",
                       "max_power"]
    _device_parameters = ["out",
                          "power",
                          "freq",
                          "phase",
                          "max_power"]  # This max power is a kind of a software interlock. The user cannot access to the max_power value
    
    _device_dict = {}
    
    def logger_decorator(func):
        """
        It writes logs when an exception happens.
        """
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as err:
                if not self.logger == None:
                    self.logger.error("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
                else:
                    print("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
        return wrapper
    
    
    def __init__(self, parent=None, config=None, logger=None, device=None):
        super().__init__()
        self.parent = parent
        self.cp = config
        self.logger = logger
        self.device = device
        self.isConnected = False
        
        self.con = None
        self.rf = None
        self.queue = Queue()
        
        
        # print(self._device_dict)
        # print("opened the device (%s)" % device)

    def __call__(self):
        return self._device_dict
    
    @property
    def description(self):
        return "RF"
    
    def _generateDevice(self):
        self.device_type = self.cp.get("device", self.device)
        if not self.device_type in self.avail_device_list.keys():
            raise ValueError ("This is an unknwon device (%s)." % self.device_type)
            self.toLog("error", "Un unknown device type has been detected! (%s)." % self.device_type )
            return
        
        if self.device_type == "synthnv":
            self.rf = SynthNV()
        elif self.device_type == "synthhd":
            self.rf = SynthHD()
        elif self.device_type == "sg384":
            self.rf = SG384()
        elif self.device_type == "apsyn420":
            self.rf = APSYN420()
        elif self.device_type == "dummy_rf":
            self.rf = Dummy_RF()
    
    @logger_decorator
    def _readRFconfig(self): 
        self._generateDevice()
        self.num_channels = self.rf._num_channels

        for channel_idx in range(self.num_channels):
            self._device_dict[channel_idx] = {key: None for key in self._device_parameters}
        
        if "ip" in self.cp.options(self.device):
            ip = self.cp.get(self.device, "ip")
            self.con = self.rf.tcp_ip = ip
        elif "com" in self.cp.options(self.device):
            comport = self.cp.get(self.device, "com")
            self.con = self.rf.port = comport
        elif "serial_number" in self.cp.options(self.device):
            serial_number = self.cp.get(self.device, "serial_number")
            comport = self.rf._get_comport(serial_number) # This function returns the comport from the serial number.
            self.con = self.rf.port = comport
            
        else:
            raise ValueError ("A necessary information to connect to the device is missing!. Please provide any ip address or com port.")
        
        for option in self._config_options:
            for cp_option in self.cp.options(self.device):
                if option in cp_option:
                    if cp_option[-4:-1] == "_ch":
                        for channel_index in range(self.num_channels):
                            self._device_dict[channel_index][option] = float(self.cp.get(self.device, option + "_ch%d" % (channel_index+1)))
                    else:
                        self._device_dict[0][option] = self.cp.get(self.device, cp_option)
                        
    @logger_decorator
    def openDevice(self):
        self._readRFconfig()
        self.rf.connect()
        self.isConnected = True

        
    @logger_decorator
    def closeDevice(self):
        for ch in self.num_channels:
            if self._device_dict[ch]["out"]:
                self.setPowerGradually(self.rf.min_power)
                self.setOutput(ch, False)
        self.isConnected = False
    
    @logger_decorator    
    def toWorkList(self, cmd):
        client = cmd[-1]
        if not client in self._client_list:
            self._client_list.append(client)
            
        self.queue.put(cmd)
        if not self.isRunning():
            self.start()
            print("Thread started")
        
    '''
    Input message = ['Work Type', 'Command', 'Data', 'Client']
    Work Type : C(Command) / Q(Query)
    
    Command : Type of command 
    - SET Freq / SET Power / Turn On/Off OUTPUT / PHASE
    - FREQ    /  POWER     /      OUT        /  PHASE   
    
    Data : list of values for command
    - freq in Hz
    - power in dBm
    - length of list = number of rf outputs    
    
    Client : client id for this message
    Client Message : True(Success Command) / False(Fail Command)
    '''
    @logger_decorator    
    def run(self):
        while self.queue.qsize():
            work = self.queue.get()
            print(work, self._device_dict)
            self._status  = "running"
            # decompose the job
            work_type, command = work[:2]
            client = work[-1]
            
            if work_type == "C":
                if command == "CON":
                    if not self.isConnected:  # The device has not been opened.
                        self.openDevice()
                        self.readHardSettings() # To compensate an unexpected shutdown of the program.
                        self.toLog("info", "Device (%s) has been opened." % self.device)
                        
                    if not client in self._client_list:
                        self._client_list.append(client)
                    
                    msg = ["D", self.device, "HELO", []]
                    self.informClients(msg, client)
                    
                    data = self.getCurrentSettings()
                    msg = ["D", self.device, "STAT", data]
                    self.informClients(msg, client)
                 
                elif command == "DCON":
                    if client in self._client_list:
                        self._client_list.remove(client)
                    #When there's no clients connected to the server, close the device.
                    if not len(self._client_list):
                        self.toLog("info", "No client is being connectd.")
                        
                elif command == "ON":
                    channel_list = work[2]
                    for ch in channel_list:
                        if not self._device_dict[ch]["out"]:
                            self.setToMinPower(ch)
                            self.setOutput(ch, True)
                            
                    msg = ["D", self.device, "OUT", [channel_list]]
                    self.informClients(msg, self._client_list)
                    
                elif command == "OFF":
                    channel_list = work[2]
                    for ch in channel_list:
                        if self._device_dict[ch]["out"]:
                            self.setPowerGradually(self.rf.min_power, ch)
                            self.setOutput(ch, False)
                            
                    msg = ["D", self.device, "OFF", [channel_list]]
                    self.informClients(msg, self._client_list)

                elif command == "SETP": # set power
                    channel_list = work[2][::2]
                    power_list   = work[2][1::2]
                    
                    msg = ["D", self.device, "PPROC", [channel_list]] # let clients know that the powers are being gradually set. the first p stands for power, proc means processing.
                    self.informClients(msg, self._client_list)
                    for ch, power in zip(channel_list, power_list):
                        self.setPowerGradually(power, ch)
                        
                    msg = ["D", self.device, "SETP", self._getListFromDict(channel_list, "power")] # Let clients know that the powers have been set.
                    self.informClients(msg, self._client_list)
                    
                elif command == "SETF": # set frequency
                    channel_list = work[2][::2]
                    freq_list    = work[2][1::2]
                    
                    for ch, freq in zip(channel_list, freq_list):
                        self.setFrequency(freq, ch)
                        
                    msg = ["D", self.device, "SETF", self._getListFromDict(channel_list, "freq")]
                    self.informClients(msg, self._client_list)
                    
                
                elif command == "SETPH": # set phase
                    channel_list = work[2][::2]
                    phase_list   = work[2][1::2]
                     
                    for ch, phase in zip(channel_list, phase_list):
                        self.setPhase(phase, ch)
                        
                    msg = ["D", self.device, "PHASE", work[2]]
                    self.informClients(msg, self._client_list)
                    
                elif command == "MAXP": # set max power
                    channel_list   = work[2][::2]
                    max_power_list = work[2][1::2]
                    
                    for ch, max_power in zip(channel_list, max_power_list):
                        self._device_dict[ch]["max_power"] = max(min(max_power, self.rf.max_power), self.rf.min_power)
                        
                    msg = ["D", self.device, "MAXP", self._getListFromDict(channel_list, "max_power")]
                    self.informClients(msg, self._client_list)
                    
                elif command == "LOCK": # set lock
                    external_flag, lock_frequency = work[2]
                    
                    self.setFrequencyLock(external_flag, lock_frequency)
                    lock_flag = self.isLocked
                    msg = ["D", self.device, "LOCK", [lock_flag, lock_frequency]]
                    self.informClients(msg, self._client_list)
                    
                else:
                    self.toLog("error", "The user (%s) sent an unknown command (%s)." % (client.user_name, command))
                    msg = ["E", self.device, command, ["cmd"]] # Error
                    self.informClients(msg, client)
                    
                
            elif work_type == "Q":
                if command == "OUT":
                    channel_list = work[2]
                    msg = ["D", self.device, "OUT", self._getListFromDict(channel_list, "out")]
                    
                    self.informClients(msg, client)
                    
                elif command == "POWER":
                    channel_list = work[2]
                    msg = ["D", self.device, "SETP", self._getListFromDict(channel_list, "power")]
                    
                    self.informClients(msg, client)
                    
                elif command == "FREQ":
                    channel_list = work[2]
                    msg = ["D", self.device, "SETF", self._getListFromDict(channel_list, "freq")]
                    
                    self.informClients(msg, client)

                elif command == "PHASE":
                    channel_list = work[2]
                    msg = ["D", self.device, "SETPH", self._getListFromDict(channel_list, "phase")]
                    
                    self.informClients(msg, client)
                    
                elif command == "MAXP":
                    channel_list = work[2]
                    msg = ["D", self.device, "MAXP", self._getListFromDict(channel_list, "max_power")]
                    
                    self.informClients(msg, client)
                    
                elif command == "LOCK":
                    msg = ["D", self.device, "LOCK", [self.isLocked, int(10e6)]]
                    
                    self.informClients(msg, client)
                    
                else:
                    self.toLog("error", "The user (%s) queried an unknown command (%s)." % (client.user_name, command))
                    msg = ["E", self.device, command, ["cmd"]] # Error
                    self.informClients(msg, client)
                    
            else:
                self.toLog("critical", "Unknown work type(%s) has been detected." % work_type)
                msg = ["E", self.device, command, ["work"]] # Error
                self.informClients(msg, client)
            
            self._status = "standby"
                         
    
    @logger_decorator
    def readHardSettings(self, verbal=False):
        """
        This funtion quries parameters to the device.
        It updates the device dictionary.
        """
        for ch_idx in self._device_dict.keys():
            for parameter in self._device_parameters:
                if not parameter == "max_power":
                    try:    
                        self._device_dict[ch_idx][parameter] = self._getHardSetting(parameter, ch_idx)
                    except Exception:
                        raise ValueError ("The parameter (%s) is nt avalable for the device(%s, %s)." % (parameter, self._device_type, self.device))
                


    @logger_decorator
    def setOutput(self, channel, out_flag):
        if out_flag:
            self.rf.enableOutput(channel)
        else:
            self.rf.disableOutput(channel)
        self._device_dict[channel]["out"] = out_flag
        
    @logger_decorator
    def setFrequency(self, frequency, channel):
        frequency = max( min(frequency, self.rf.max_frequency), self.rf.min_frequency )
            
        self.rf.setFrequency(frequency, channel)
        self._device_dict[channel]["freq"] = frequency
    
    @logger_decorator
    def setPhase(self, phase, channel):
        self.rf.setPhase(phase, channel)
        self._device_dict[channel]["phase"] = phase

    def dBm_to_vpp(self, dBm):
        volt = 2*np.sqrt((100)/1000)*10**(dBm/20)
        return volt
        
    def vpp_to_dBm(self, vpp):
        dBm = 20*np.log10(vpp/np.sqrt(8)/(0.001 * 50)**0.5)
        return dBm

    @logger_decorator
    def setPowerGradually(self, power, ch_idx=0, voltage_resolution=0.05, time_resolution=0.2):
        # if not self._device_dict[ch_idx]["out"]:
        #     raise RuntimeError ("The device is not turned on.")
            
        init_power = self._device_dict[ch_idx]["power"]        
        final_power = max( min(power, self._device_dict[ch_idx]["max_power"]), self.rf.min_power )
        
        init_vpp = self.dBm_to_vpp(init_power)
        final_vpp = self.dBm_to_vpp(final_power)
        
        power_list = self.vpp_to_dBm(np.arange(init_vpp, final_vpp, (-1)**(init_vpp > final_vpp)*voltage_resolution))
        
        for sub_power in power_list:
            self.setPower(sub_power, ch_idx)
            print("sub_power: %.2f" % sub_power)
            time.sleep(time_resolution)
        self.setPower(final_power, ch_idx)
        self._device_dict[ch_idx]["power"] = final_power
    
    @logger_decorator
    def setPower(self, power, ch_idx):
        power = max( min(power, self._device_dict[ch_idx]["max_power"]), self.rf.min_power )
        self.rf.setPower(power, ch_idx)
        self._device_dict[ch_idx]["power"] = power

    @logger_decorator
    def setToMinPower(self, channel):
        min_power = self.rf.min_power
        self.setPower(min_power, channel)
        
    def toLog(self, log_type, log_content):
        if not self.logger == None:
            if log_type == "debug":
                self.logger.debug(log_content)
            elif log_type == "info":
                self.logger.info(log_content)
            elif log_type == "warning":
                self.logger.warning(log_content)
            elif log_type == "error":
                self.logger.error(log_content)
            else:
                self.logger.critical(log_content)           
        else:
            print(log_type, log_content)
    
    @logger_decorator
    def informClients(self, msg, client_list):
        print(msg)
        if not type(client_list) == list:
            client_list = [client_list]
        
        for client in client_list:
            client.toMessageList(msg)

    @logger_decorator
    def _getHardSetting(self, parameter, ch_idx):
        if parameter == "out":
            return self.rf.is_output_enabled(ch_idx)
        elif parameter == "power":
            return self.rf.getPower(ch_idx)
        elif parameter == "freq":
            return self.rf.getFrequency(ch_idx)
        elif parameter == "phase":
            return self.rf.getPhase(ch_idx)
        else:
            return
            
    @logger_decorator
    def readSettings(self, parameter, ch_idx=0):
        if parameter in self._device_parameters:
            return self._device_dict[ch_idx][parameter]
        else:
            raise ValueError ("The parameter (%s) is nt avalable for the device(%s, %s)." % (parameter, self.device_type, self.device))
        
    @logger_decorator
    def getCurrentSettings(self):
        """
        This functions returnes current settings data as list.
        """
        data = []
        for ch_idx in self._device_dict.keys():
            data.append(["o", self.readSettings("out", ch_idx),
                         "f", self.readSettings("freq", ch_idx),
                         "p", self.readSettings("power", ch_idx),
                         "ph", self.readSettings("phase", ch_idx),
                         "mp", self.readSettings("max_power", ch_idx)])
        return data
    
    def _getListFromDict(self, channel_list, parameter):
        if not type(channel_list) == list: # single parameter is acceptable
            channel_list = [channel_list]
        
        return_list = []
        for channel in channel_list:
            value =  self._device_dict[channel][parameter]
            temp_list = [channel, value]
            return_list += temp_list
        return return_list
    
    @logger_decorator
    def setFrequencyLock(self, lock_flag, lock_frequency):
        self.rf.lockFrequency(lock_flag, lock_frequency)
        
    @property
    def isLocked(self):
        return self.rf.is_locked()
        
            
class DummyClient():
    
    def __init__(self):
        pass
           
    def toMessageList(self, msg):
        print(msg)
        


if __name__ == "__main__":
    RF = RF_Controller(nickname="Dummy")
    RF.device_type = "dummy_rf"
    RF._generateDevice()
    
    client = DummyClient()
    
    RF.toWorkList(["C", "CON", [], client])
    RF.toWorkList(["C", "SETF", [0, 100], client])
    RF.toWorkList(["C", "ON", [0], client])
    RF.toWorkList(["C", "SETP", [0, 3], client])
    
    RF.toWorkList(["C", "OFF", [0], client])
