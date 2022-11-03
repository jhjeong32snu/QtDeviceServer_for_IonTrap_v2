# -*- coding: utf-8 -*-
"""
Created on Mon Oct 18 01:51:36 2021

@author: KMLee
"""
import time, sys
from PyQt5.QtCore import QThread
from configparser import ConfigParser
from serial.tools import list_ports

api_dir = 'Q://Users/KMLee/Script/RFSource'
sys.path.append(api_dir)
from queue import Queue
from RFdevice import SynthHD

# def not_conneted(func):
#     """Decorator that checks the connection before calling func.
#     Raises:
#         RuntimeError - the func is called without connection.
#     """
#     def check_connection(self, *args):
#         rftype = args[0]
#         dev = self.rf_dict[rftype]['object']
#         if dev.is_connected():
#             return func(self, *args)
#         else:
#             return 'Device is not connected'
#     return check_connection

class SynthHDController(QThread):
    
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
        return wrapper
    
    
    def __init__(self, serial_num=None, logger=None, parent=None):
        super().__init__()
        self.get_device(serial_num)
        self.rf_settings = {'On': False, 'curr freq': None, 'curr power': None, 'curr chan': None}
        # self.readSettings()
        self.logger = logger
        self.queue = Queue()
        
    def get_device(self, serial_num):
        local_ser_list = [dev.serial_number for dev in list_ports.comports()]
        if serial_num in local_ser_list:
            dev_idx = local_ser_list.index(serial_num)
            dev_port = list_ports.comports()[dev_idx].device
        self.synth = SynthHD(port=dev_port)
            
    @logger_decorator
    def openDevice(self):
        if self.synth.is_connected():
            msg = 'Hello, Device is already opened \n'
            msg += 'Current freq: {}, power: {}, Output: {}'.format(self.rf_settings['curr freq'], self.rf_settings['curr power'], self.rf_settings['On'])
        else:
            self.synth.connect()
            self.synth.disable_output()
            self.applyPower(0)
            self.applyFreq(1000e6)
            self.readSettings()
            msg = 'Hello, Device is opened \n'
            msg += 'Current freq: {}, power: {}, Output: {}'.format(self.rf_settings['curr freq'], self.rf_settings['curr power'], self.rf_settings['On'])
        # return msg
        if self.synth.is_connected():
            return True
        else:
            return False
        
    @logger_decorator
    def closeDevice(self):
        self.outputOFF()
        self.synth.disable_output()
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
                    result, toall = self.applyFreq(data), True
                if command == "SETP":
                    result, toall = self.applyPower(data), True
                if command == "TON":
                    result, toall = self.outputON(), True
                if command == "TOFF":
                    result, toall = self.outputOFF(), True
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
                    result, toall = self.readFreq(), False
    
                if command == "POWER":
                    data = work[2]
                    result, toall = self.readPower(), False
                
                if command == "TON":
                    data = work[2]
                    result, toall = self.readState(), False

                if command == "CH":
                    result, toall = self.readChannel(), False
                    
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
    def readSettings(self, rf_type):
        self.rf_settings['On'] = self.synth.is_output_enabled()
        self.rf_settings['curr freq'] = self.synth.read_frequency()
        self.rf_settings['curr power'] = self.synth.read_power()
        self.rf_settings['curr chan'] = self.synth.read_channel()
        print('Output Enabled: {}'.format(self.rf_settings['On']))
        print('Current freq: {} Hz'.format(self.rf_settings['curr freq']))
        print('Current power: {} dBm'.format(self.rf_settings['curr power']))
        print('Current channel: {}'.format(self.rf_settings['curr chan']))
        
    @logger_decorator
    def readPower(self):
        # return 'Current power : {}'.format(self.rf_settings['curr power'])
        return self.rf_settings['curr power']

    @logger_decorator
    def readFreq(self):
        # return 'Current freq : {}'.format(self.rf_settings['curr freq'])
        return self.rf_settings['curr freq']

    @logger_decorator
    def readChannel(self):
        # return 'Output Enabled : {}'.format(self.rf_settings['On'])
        return self.rf_settings['curr chan']
        
    @logger_decorator
    def readState(self):
        # return 'Output Enabled : {}'.format(self.rf_settings['On'])
        return self.rf_settings['On']
    
    '''fdata is frequency in Hz'''
    @logger_decorator
    def applyFreq(self, fdata):
        dev = self.synth
        dev.apply_frequency(fdata)    
        self.readSettings()
        return self.rf_settings['curr freq']

    '''
    pdata is power in index 0~63
    It corresponds to power dbm list from -10.84 dBm to 18.35 dBm
    '''        
    @logger_decorator
    def applyPower(self, pdata):
        dev = self.synth
        curr_power = self.rf_settings['curr power idx']
        if curr_power > pdata:
            for i in reversed(range(pdata, curr_power)):
                dev.apply_power(i)
                time.sleep(0.05)
        elif curr_power < pdata:
            for i in range(curr_power, pdata+1):
                dev.apply_power(i)
                time.sleep(0.05)

        self.readSettings()
        return self.rf_settings['curr power']
    
    @logger_decorator
    def outputON(self):
        dev = self.synth
        if not dev.is_output_enabled():
            power_idx = self.rf_settings['curr power idx']
            
            self.applyPower(0)
            dev.enable_output()
            self.applyPower(power_idx)

        self.readSettings()
        return self.rf_settings['On']

    
    @logger_decorator
    def outputOFF(self):
        dev = self.synth
        if dev.is_output_enabled():
            power_idx = self.rf_settings['curr power idx']
            
            self.applyPower(0)
            dev.disable_output()

        self.readSettings()
        return self.rf_settings['On']

        
    def setChannel(self, ch):
        self.synth.set_channel(ch)
        self.readSettings()
        return self.rf_settings['curr chan']
        
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
        
