# -*- coding: utf-8 -*-
"""
@author: KMLee
"""

import time, sys, traceback, os
from PyQt5.QtCore import QThread
from configparser import ConfigParser
from serial.tools import list_ports
import numpy as np
from queue import Queue
from DummyRFdevice import *
from RFsettings import Device_list

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

class RFController(QThread):
    
    _work_list = []
    _client_list = []
    _status = "standby"
    # Available rf device model list
    rf_device_model_list = {'synthnv':SynthNV, 
                            'synthhd':SynthHD, 
                            'sg384':SG384, 
                            'apsyn420':APSYN420}
    
    def logger_decorator(func):
        """
        It writes logs when an exception happens.
        """
        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except Exception as err:
                if not self.logger == None:
                    self.logger.error("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
                else:
                    print("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
        return func
    
    
    def __init__(self, logger=None, device=None, parent=None):
        super().__init__()
        self.device = device
        # device = 'RF' is for extra action -> passing initial rf settings of server
        if self.device == 'RF':
            self.rf_dev_settings = Device_list
        if not self.device == 'RF' or self.device == None:
            self._readRFconfig()
            self._getDevice()
            self._init_settings() 

        self.logger = logger
        self.queue = Queue()

    @logger_decorator
    def _readRFconfig(self):
        self.cp = ConfigParser()
        self.cp.read(dirname + "/RFconfig.ini")
        self._conn_type = self.cp.get(self.device, 'type').lower()
        self._device_model = self.cp.get(self.device, 'model').lower()
        
        if self._conn_type == 'serial':
            self._serial_num = self.cp.get(self.device, 'serial_number')
            local_ser_list = [dev.serial_number for dev in list_ports.comports()]
            local_com_list = [dev.device for dev in list_ports.comports()]
            if self._serial_num in local_ser_list:
                dev_idx = local_ser_list.index(self.serial_num)
                self._port = local_com_list[dev_idx]
            else: 
                self._port = None
        elif self._conn_type == 'socket':
            self._ip = self.cp.get(self.device, 'ip')
            self._port = self.cp.get(self.device, 'port')
        
    @logger_decorator
    def _getDevice(self):
        if self._device_model in self.rf_device_model_list:
            if self._conn_type == 'serial':
                self.synth = self.rf_device_model_list[self._device_model](port=self._port)
            elif self._conn_type == 'socket':
                self.synth = self.rf_device_model_list[self._device_model](tcp_ip=self._ip, tcp_port=self._port)
        
    @logger_decorator
    def _init_settings(self):
        self.rf_settings = {'on': [False for i in range(self.synth._num_power)], 
                            'power': [None for i in range(self.synth._num_power)],
                            'freq': [None for i in range(self.synth._num_freq)],
                            'phase': [None for i in range(self.synth._num_phase)]
                            }
        self.rf_read_functions = {'on': self.synth.is_output_enabled,
                                  'power': self.synth.getPower,
                                  'freq': self.synth.getFrequency, 
                                  'phase': self.synth.getPhase
                                  }
        self.output_mapping = self.synth._output_mapping

    @logger_decorator
    def openDevice(self, serial_num=None):
        print('\n Open Device')
        if self.synth.is_connected():
            msg = 'Hello, Device is already opened \n'
            msg += 'Output: {}, freq: {}, power: {}, phase: {}'.format(self.rf_settings['on'], self.rf_settings['freq'], 
                                                                      self.rf_settings['power'], self.rf_settings['phase'])
            print(msg)
        else:
            self.synth.connect()
            self.readSettings()
            self.synth.disableOutput()
            self.setPower([self.synth.min_power])
            msg = 'Hello, Device is opened \n'
            msg += 'Current freq: {}, power: {}, Output: {}'.format(self.rf_settings['freq'], self.rf_settings['power'], self.rf_settings['on'])
            print(msg)
        if self.synth.is_connected():
            return [True]
        else:
            return [False]
        
    @logger_decorator
    def closeDevice(self):
        print('\n Close Device')
        self.setPower([self.synth.min_power])
        self.synth.disableOutput()
        self.synth.disconnect()
        self._init_settings()
        if not self.synth.is_connected():
            return [True]
        else:
            return [False]
    
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
        while True:
            work = self.queue.get()
            self._status  = "running"
            # decompose the job
            work_type, command = work[:2]
            client = work[-1]
            
            if not client in self._client_list:
                self._client_list.append(client)
                
            print(work_type, command)
            
            if work_type == "C":
                data = work[2]
                if command == "FREQ":
                    result, toall = self.setFrequency(data), True
                elif command == "POWER":
                    result, toall = self.setPower(data), True
                elif command == "PHASE":
                    result, toall = self.setPhase(data), True
                elif command == "OUT":
                    result, toall = self.enableOutput(data), True
                elif command == "INIT":
                    result, toall = [self.rf_dev_settings], False
                # if command == "TOFF":
                #     result, toall = self.disableOutput(data), True
                
                elif command == "ON":
                    """
                    When a client is connected, opens the devcie and send voltage data to the client.
                    """
                    print("opening the device")
                    result = self.openDevice()
                    toall = False
                    
                elif command == "OFF":
                    """
                    When a client is disconnected, terminate the client and close the device if no client left.
                    """
                    if client in self._client_list:
                        self._client_list.remove(client)
                        result = 'Other clients still extists. You are just deleted from client list'
                    # When there's no clients connected to the server. close the device.
                    if not len(self._client_list):
                        result = self.closeDevice()
                        self.toLog("info", "No client is connected. Closing the device.")
                    toall = False
                
            elif work_type == "Q":
                if command == "FREQ":
                    data = work[2]
                    result, toall = self.getFrequency(), False
                elif command == "POWER":
                    data = work[2]
                    result, toall = self.getPower(), False
                elif command == "PHASE":
                    data = work[2]
                    result, toall = self.getPhase(), False
                elif command == "OUT":
                    data = work[2]
                    result, toall = self.getOutput(), False
                    
            else:
                self.toLog("critical", "Unknown work type(%s) has been detected." % work_type)
        
            # Return Message got form
            # ['D', Device, Command, Result]
            result.append(self.device) # To inform client which rf device is used
            # Send message to clinet's device dict with name 'RF'
            msg = ['D', 'RF', command, result]
            if toall == True:
                self.informClients(msg, self._client_list)
            else:
                self.informClients(msg, client)
            
            self._status = "standby"
                         
    
    '''
    RF Setting data from device
    'Rf type': {'freq':'real hardware info', 
                'power': 'device number(serial number/IP&PORT)'}
    If device is not connected and not read, it might be None value
    '''
    @logger_decorator
    def readSettings(self, verbal=False):
        for key in self.rf_settings:
            for i in range(len(self.rf_settings[key])):
                self.rf_settings[key][i] = self.rf_read_functions[key](output_type = i)
        print('Output Enabled: {}'.format(self.rf_settings['on']))
        print('Current freq: {} Hz'.format(self.rf_settings['freq']))
        print('Current power: {} dBm'.format(self.rf_settings['power']))
        print('Current phase: {}'.format(self.rf_settings['phase']))
        
    @logger_decorator
    def getPower(self):
        return self.rf_settings['power']

    @logger_decorator
    def getFrequency(self):
        return self.rf_settings['freq']
        
    @logger_decorator
    def getPhase(self):
        return self.rf_settings['phase']
    
    @logger_decorator
    def getOutput(self):
        return self.rf_settings['on']
        
    @logger_decorator
    def is_output_enabled(self):
        return self.rf_settings['on']
    
    '''fdata is list of frequency in Hz'''
    @logger_decorator
    def setFrequency(self, fdata):
        # SG384 Shares freq & phase for both output type -> Only first value is used
        dev = self.synth
        for idx, curr_power in enumerate(self.rf_settings['freq']):
            dev.setFrequency(fdata[idx], output_type=idx)
        self.readSettings()
        print('\n Set Frequency {}'.format(self.rf_settings['freq']))
        return self.rf_settings['freq']

    '''
    pdata is list of power in dBm
    SynthNV
    power range from [-10.84, +18.35] dBm
    SynthHD
    power range from [-50, +20] dBm
    APSYN
    Power is not adjustable(+23dBM).
    SG384
    Power range (Type-N): [-110, +16.50] dBm to [-110, +13] dBm over 3GHz
    Power range (BNC): [-47, +13] dBm
    ==> Fixed both as [-47, +13] dBm
    '''        
    @logger_decorator
    def setPower(self, pdata):
        dev = self.synth
        for idx, curr_power in enumerate(self.rf_settings['power']):
            power_val = pdata[idx]
            power_step = 0.2
            if curr_power > power_val:
                power_step *= -1
            power_step_range = np.round(np.arange(curr_power, power_val, power_step), 2)
            for p in power_step_range:
                dev.setPower(power = p, output_type = idx)
                time.sleep(0.05)
            dev.setPower(power=power_val, output_type = idx)
        self.readSettings()
        print('\n Set Power {}'.format(self.rf_settings['power']))
        return self.rf_settings['power']

    '''phdata is list of phase in degree'''
    @logger_decorator
    def setPhase(self, phdata):
        # SG384 Shares freq & phase for both output type -> Only first value is used
        dev = self.synth
        for idx, curr_power in enumerate(self.rf_settings['phase']):
            dev.setPhase(phdata[idx], output_type=idx)
        self.readSettings()
        print('\n Set Phase {}'.format(self.rf_settings['phase']))
        return self.rf_settings['phase']

    @logger_decorator
    def enableOutput(self, odata):
        dev = self.synth
        '''
        odata : list of True(output on) / False(output off) for each output for device.
        '''
        for idx, curr_output in enumerate(self.rf_settings['on']):
            output = bool(odata[idx])
            if dev.is_output_enabled(output_type=idx)==False and output == True:
                curr_power, reduce_power = self.rf_settings['power'].copy(), self.rf_settings['power'].copy()
                reduce_power[idx] = self.synth.min_power
                # Reduce object output channel power to minimum 
                self.setPower(reduce_power)
                dev.enableOutput(output_type=idx)
                # Recover power
                self.setPower(curr_power)

            elif dev.is_output_enabled(output_type=idx)==True and output == False:
                reduce_power = self.rf_settings['power'].copy()
                reduce_power[idx] = self.synth.min_power
                self.setPower(reduce_power)
                dev.disableOutput(output_type=idx)
                
        self.readSettings()
        print('\n Enabled Output {}'.format(self.rf_settings['on']))
        return self.rf_settings['on']
    
    # @logger_decorator
    # def disableOutput(self):
    #     dev = self.synth
    #     curr_power = self.rf_settings['curr power']
    #     for idx, output in enumerate(self.rf_settings['on']):
    #         if not dev.is_output_enabled(output_type=idx):
    #             self.setPower(self.synth.min_power, output_type=idx)
    #             dev.disableOutput(output_type=idx)
    #     self.readSettings()
    #     self.rf_settings['curr power'] = curr_power
    #     print('\n Disnabled Output {}'.format(self.rf_settings['on']))
    #     return self.rf_settings['on']
        
        
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

    @logger_decorator
    def informClients(self, msg, client):
        if type(client) != list:
            client = [client]
        
        # print("To the client:", msg)
        for clt in client:
            clt.sendMessage(msg)
            
class DummyClient():
    
    def __init__(self):
        pass
    
    def sendMessage(self, msg):
        print(msg)
        
