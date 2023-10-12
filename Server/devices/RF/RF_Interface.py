# -*- coding: utf-8 -*-
"""
@author: Junho Jeong
@Tel: 010-9600-3392
@email1: jhjeong32@snu.ac.kr
@mail2: bugbear128@gmail.com
"""

import time, os
from PyQt5.QtCore import QThread
from configparser import ConfigParser
from serial.tools import list_ports
import numpy as np
from queue import Queue
# from DummyRFdevice import *
from RFdevice import (SynthNV, SynthHD, SG384, APSYN420)
from RFsettings import Device_list

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

class RFInterface(QThread):
    
    _work_list = []
    _client_list = []
    _status = "standby"
    # Available rf device model list
    rf_device_model_list = {'synthnv':SynthNV, 
                            'synthhd':SynthHD, 
                            'sg384':SG384, 
                            'apsyn420':APSYN420}
    _device_dict = {}
    
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

    def __call__(self):
        return self._device_dict

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
                dev_idx = local_ser_list.index(self._serial_num)
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
            self.readSettings()
            print(msg)
            return [True, self.rf_settings].copy()
        else:
            self.synth.connect()
            self.readSettings()
            self.setToMinPower()
            # self.setPower([self.synth.min_power for i in range(self.synth._num_power)])
            for i in range(self.synth._num_power):
                self.synth.disableOutput(i)
            msg = 'Hello, Device is opened \n'
            msg += 'Current freq: {}, power: {}, Output: {}'.format(self.rf_settings['freq'], self.rf_settings['power'], self.rf_settings['on'])
            print(msg)
            if self.synth.is_connected():
                return [True, self.rf_settings].copy()
            else:
                return [False, self.rf_settings].copy()
        
    @logger_decorator
    def closeDevice(self):
        print('\n Close Device')
        self.readSettings()
        self.setToMinPower()
        self.enableOutput([False for i in range(self.synth._num_power)])
        self.synth.disconnect()
        # self._init_settings()
        if not self.synth.is_connected():
            return [True, self.rf_settings].copy()
        else:
            return [False, self.rf_settings].copy()
    
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
            print(work)
            self._status  = "running"
            # decompose the job
            work_type, command = work[:2]
            client = work[-1]
            
            if not client in self._client_list:
                self._client_list.append(client)
            
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
                    result, toall = [self.rf_dev_settings].copy(), False
                
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
                    print(client)
                    if client in self._client_list:
                        self._client_list.remove(client)
                        self.readSettings()
                        result = [True, self.rf_settings]
                        # result = 'Other clients still extists. You are just deleted from client list'
                    # When there's no clients connected to the server. close the device.
                    if len(self._client_list) == 0:
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
            if not command == 'INIT':
                print(msg)
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
        # print('Output Enabled: {}'.format(self.rf_settings['on']))
        # print('Current freq: {} Hz'.format(self.rf_settings['freq']))
        # print('Current power: {} dBm'.format(self.rf_settings['power']))
        # print('Current phase: {}'.format(self.rf_settings['phase']))
        
    @logger_decorator
    def getPower(self):
        return self.rf_settings['power'].copy()

    @logger_decorator
    def getFrequency(self):
        return self.rf_settings['freq'].copy()
        
    @logger_decorator
    def getPhase(self):
        return self.rf_settings['phase'].copy()
    
    @logger_decorator
    def getOutput(self):
        return self.rf_settings['on'].copy()
        
    @logger_decorator
    def is_output_enabled(self):
        return self.rf_settings['on'].copy()
    
    '''fdata is list of frequency in Hz'''
    @logger_decorator
    def setFrequency(self, fdata):
        # SG384 Shares freq & phase for both output type -> Only first value is used
        dev = self.synth
        for idx, curr_power in enumerate(self.rf_settings['freq']):
            dev.setFrequency(fdata[idx], output_type=idx)
        self.readSettings()
        print('\n Set Frequency {}'.format(self.rf_settings['freq']))
        return self.rf_settings['freq'].copy()

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
        current_power = self.rf_settings['power'].copy()
        for i, curr_out in enumerate(self.rf_settings['on']):
            print('output: {}'.format(curr_out))
            if curr_out == True:
                curr_power = current_power[i]
                power_val = pdata[i]
                power_step = 0.5
                if curr_power > power_val:
                    power_step *= -1
                power_step_range = np.round(np.arange(curr_power, power_val, power_step), 2)
                for p in power_step_range:
                    dev.setPower(power = p, output_type = i)
                    time.sleep(0.1)
                    print(p)
                dev.setPower(power=power_val, output_type = i)
            else:
                for idx, curr_power in enumerate(self.rf_settings['power']):
                    power_val = pdata[idx]
                    dev.setPower(power=power_val, output_type = idx)
        self.readSettings()
        print('\n Set Power {}'.format(self.rf_settings['power']))
        return self.rf_settings['power'].copy()

    @logger_decorator
    def setToMinPower(self):
        dev = self.synth
        min_power = dev.min_power
        for idx in range(len(self.rf_settings['on'])):
            if self.rf_settings['on'][idx] == False:
                dev.setPower(power=min_power, output_type = idx)
            else:
                self.setPower([dev.min_power for i in range(len(self.rf_settings['power']))])
                pass

    '''phdata is list of phase in degree'''
    @logger_decorator
    def setPhase(self, phdata):
        # SG384 Shares freq & phase for both output type -> Only first value is used
        dev = self.synth
        for idx, curr_power in enumerate(self.rf_settings['phase']):
            dev.setPhase(phdata[idx], output_type=idx)
        self.readSettings()
        print('\n Set Phase {}'.format(self.rf_settings['phase']))
        return self.rf_settings['phase'].copy()

    @logger_decorator
    def enableOutput(self, odata):
        dev = self.synth
        '''
        odata : list of True(output on) / False(output off) for each output for device.
        '''
        
        curr_out = self.rf_settings['on'].copy()
        for idx, curr_output in enumerate(curr_out):
            output = bool(odata[idx])
            
            if dev.is_output_enabled(output_type=idx)==False and output == True:
                curr_power = self.rf_settings['power'].copy()
                reduce_power = self.rf_settings['power'].copy()
                reduce_power[idx] = self.synth.min_power
                # self.setToMinPower()
                self.setPower(reduce_power)
                dev.enableOutput(output_type=idx)
                self.readSettings()
                # Recover power
                self.setPower(curr_power)
            
            elif dev.is_output_enabled(output_type=idx)==True and output == False:
                reduce_power = self.rf_settings['power'].copy()
                reduce_power[idx] = self.synth.min_power
                # reduce_power = [self.synth.min_power for i in range(len(self.rf_settings['on']))]
                self.setPower(reduce_power)
                dev.disableOutput(output_type=idx)
                self.readSettings()
            
            elif dev.is_output_enabled(output_type=idx)==False and output == False:
                pass
            elif dev.is_output_enabled(output_type=idx)==True and output == True:
                pass
        self.readSettings()
        print('\n Enabled Output {}'.format(self.rf_settings['on']))
        return [self.rf_settings].copy()
        
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
        if not type(client) == list:
            print("not list")
            client = [client]
        
        for client in client:
            print(client._port)
            print(client.user_name)
            client.toMessageList(msg)
            while client.status == "sending":
                time.sleep(0.01)
            
        print("informing Done!")
    
    def releaseDevice(self):
        self.synth.disconnect()
        msg = ['D', 'RF', 'REL', [True, self.device]]
        self.informClients(msg, self._client_list)
    
    def grabDevice(self):
        self.synth.connect()
        self.readSettings()
        msg = ['D', 'RF', 'REL', [False, self.device]]
        self.informClients(msg, self._client_list)
            
class DummyClient():
    
    def __init__(self):
        pass
    
    def sendMessage(self, msg):
        print(msg)
        
