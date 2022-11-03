# -*- coding: utf-8 -*-
"""
Created on Mon Oct 18 01:51:36 2021

@author: KMLee
"""
import time, sys, traceback, os
from PyQt5.QtCore import QThread
from configparser import ConfigParser
from serial.tools import list_ports
import numpy as np

api_dir = 'Q://Users/KMLee/Script/RFSource'
sys.path.append(api_dir)
from queue import Queue
# from RFdevice import SynthNV, SynthHD
from Dummy_RFdevice import SynthNV, SynthHD

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

class WindfreakController(QThread):
    
    _work_list = []
    _client_list = []
    _status = "standby"
    def logger_decorator(func):
        """
        It writes logs when an exception happens.
        """
        def wrapper(self, *args):
            try:
                func(self, *args)
            except Exception as err:
                if not self.logger == None:
                    self.logger.error("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
                else:
                    print("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
        return func
    
    
    def __init__(self, logger=None, device='935SB', parent=None):
        super().__init__()
        self.rf_settings = {'On': False, 'curr freq': None, 'curr power': None, 'curr chan': None}
        self.parent = parent

        self.logger = logger
        self.queue = Queue()
                
        self.device = device
        self._readRFconfig()
        self._getDevice()
        if self.synth.__class__ == 'SynthNV':
            self.__power_dbm_list = self.synth.power_dbm_list

    def _readRFconfig(self):
        self.cp = ConfigParser()
        self.cp.read(dirname + "/RFconfig.ini")
        self.serial_num = self.cp.get(self.device, 'serial_number')
        self.synth_type = self.cp.get(self.device, 'type')
        
    def _getDevice(self):
        local_ser_list = [dev.serial_number for dev in list_ports.comports()]
        local_com_list = [dev.device for dev in list_ports.comports()]
        if self.serial_num in local_ser_list:
            dev_idx = local_ser_list.index(self.serial_num)
            self.port = local_com_list[dev_idx]
        else: 
            self.port = None
            
        if self.synth_type.lower() == 'synthnv':
            self.synth = SynthNV(port=self.port)
        elif self.synth_type.lower() == 'synthhd':
            self.synth = SynthHD(port=self.port)

    @logger_decorator
    def openDevice(self, serial_num=None):
        print('\n Open Device')
        if self.synth.is_connected():
            msg = 'Hello, Device is already opened \n'
            msg += 'Current freq: {}, power: {}, Output: {}'.format(self.rf_settings['curr freq'], self.rf_settings['curr power'], self.rf_settings['On'])
            print(msg)
        else:
            self.synth.connect()
            self.readSettings()
            self.synth.disableOutput()
            self.setPower(self.synth.min_power)
            self.setFrequency(1000e6)
            msg = 'Hello, Device is opened \n'
            msg += 'Current freq: {}, power: {}, Output: {}'.format(self.rf_settings['curr freq'], self.rf_settings['curr power'], self.rf_settings['On'])
            print(msg)
        # return msg
        if self.synth.is_connected():
            return True
        else:
            return False
        
    @logger_decorator
    def closeDevice(self):
        print('\n Close Device')
        self.outputOFF()
        self.synth.disableOutput()
        self.synth.disconnect()
        self.rf_settings['On'] = False
        self.rf_settings['curr freq'] = None
        self.rf_settings['curr power'] = None
        # return 'Device is Closed'    
        if not self.synth.is_connected():
            return True
        else:
            return False
    
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
    - SET Freq / SET Power / Turn On / Turn Off 
    - SETF    /  SETP     /  TON    /  TOFF   
    
    Data : value of command - 
    - freq in Hz
    - power in index from 0 to 63 (Correspond to -10.84 dBm to 18.35 dBm)
    
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
            rftype, command = command.split(':')[0], command.split(':')[1]
            
            if not client in self._client_list:
                self._client_list.append(client)
            
            if work_type == "C":
                data = work[2]
                if command == "SETF":
                    result, toall = self.setFrequency(data), True
                if command == "SETP":
                    result, toall = self.setPower(data), True
                if command == "TON":
                    result, toall = self.enableOutput(), True
                if command == "TOFF":
                    result, toall = self.disableOutput(), True
                if command == "CH":
                    result, toall = self.setChannel(data), True
                
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
    
                if command == "POWER":
                    data = work[2]
                    result, toall = self.getPower(), False
                
                if command == "TON":
                    data = work[2]
                    result, toall = self.is_output_enabled(), False
                
                if command == "CH":
                    result, toall = self.getChannel(), False
                    
            else:
                self.toLog("critical", "Unknown work type(%s) has been detected." % work_type)
        
            
            msg = ['D', command, command, result]
            if toall == True:
                self.informClients(msg, self.client_list)
            else:
                self.informClients(msg, client)
            
            self._status = "standby"
                         
    
    '''
    RF Setting data from device
    'Rf type': {'curr freq':'real hardware info', 
                'curr power': 'device number(serial number/IP&PORT)'}
    If device is not connected and not read, it might be None value
    '''
    @logger_decorator
    def readSettings(self, verbal=False):
        self.rf_settings['On'] = self.synth.is_output_enabled()
        self.rf_settings['freq'] = self.synth.getFrequency()
        self.rf_settings['power'] = self.synth.getPower()
        print('Output Enabled: {}'.format(self.rf_settings['On']))
        print('Current freq: {} Hz'.format(self.rf_settings['curr freq']))
        print('Current power: {} dBm'.format(self.rf_settings['curr power']))
        
    @logger_decorator
    def getPower(self):
        return self.rf_settings['power']

    @logger_decorator
    def getFrequency(self):
        return self.rf_settings['freq']
        
    @logger_decorator
    def is_output_enabled(self):
        return self.rf_settings['On']
    
    '''fdata is frequency in Hz'''
    @logger_decorator
    def setFrequency(self, fdata):
        dev = self.synth
        dev.setFrequency(fdata)
        print('\n Set Frequency')
        self.readSettings()
        return self.rf_settings['curr freq']

    '''
    SynthNV
    power range from -10.84 dBm to 18.35 dBm
    SynthHD
    power range from -50 dBm to 20 dBm

    '''        
    @logger_decorator
    def setPower(self, pdata):
        dev = self.synth
        curr_power = self.rf_settings['power']
        
        if self.synth.__class__ == 'SynthNV':
            power_idx = self.find_nearest_idx(self.__power_dbm_list, pdata)
            pdata = self.__power_dbm_list[power_idx]
        
        if curr_power > pdata:
            for i in reversed(np.arange(pdata, curr_power, 0.1)):
                dev.setPower(i)
                time.sleep(0.2)
        elif curr_power < pdata:
            for i in np.arange(curr_power, pdata+0.05, 0.1):
                dev.setPower(i)
                time.sleep(0.2)

        print('\n Set Power')
        self.readSettings()
        return self.rf_settings['power']

    @logger_decorator
    def enableOutput(self):
        dev = self.synth
        if not dev.is_output_enabled():
            curr_power = self.rf_settings['power']
            self.setPower(self.synth.min_power)
            dev.enableOutput()
            self.setPower(curr_power)

        print('\n Enabled Output')
        self.readSettings()
        return self.rf_settings['On']
    
    @logger_decorator
    def disableOutput(self):
        dev = self.synth
        if dev.is_output_enabled():
            curr_power = self.rf_settings['power']
            self.setPower(self.synth.min_power)
            dev.disableOutput()
            
        print('\n Disabled Output')
        self.readSettings()
        self.rf_settings['power'] = curr_power
        return self.rf_settings['On']
        
    @logger_decorator
    def setChannel(self, ch):
        self.synth.setChannel(ch)
        print('\n Set Channel')
        self.readSettings()
        return self.rf_settings['curr chan']
        
        
    def find_nearest_idx(array, value):
        return (np.abs(array - value)).argmin()
        
        
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
        
        print("To the client:", msg)
        for clt in client:
            clt.sendMessage(msg)
            
class DummyClient():
    
    def __init__(self):
        pass
    
    def sendMessage(self, msg):
        print(msg)
        
