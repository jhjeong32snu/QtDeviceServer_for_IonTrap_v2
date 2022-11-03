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

def not_conneted(func):
    """Decorator that checks the connection before calling func.
    Raises:
        RuntimeError - the func is called without connection.
    """
    def check_connection(self, *args):
        rftype = args[0]
        dev = self.rf_dict[rftype]['object']
        if dev.is_connected():
            return func(self, *args)
        else:
            return 'Device is not connected'
    return check_connection

class RFController(QThread):
    
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
    
    
    def __init__(self, logger=None, parent=None):
        super().__init__()
        self.cp = ConfigParser()
        self.cp.read('RFconfig.ini')
        self.read_rf_config()
        self.rf_dict = {}
        self.get_devices()
        self.rf_settings = {key: {'curr freq': None, 'curr power': None} for key in self.cp.sections()}
        
        self.logger = logger
        self.queue = Queue()
    

    def read_rf_config(self):
        '''
        RF Dict form
        'Rf type': {'hw':'real hardware info', 
                    'dev num': 'device number(serial number/IP&PORT)', 
                    'conn type': 'connection type(serial/socket)'}
        EX) '2.7G' : {'hw': 'SynthNV', 'dev num': '12345', 'conn type': 'serial'}
        '''
        self.rf_types = self.cp.sections()
        self.rf_dict = {}
        for rf_type in self.rf_types:
            self.rf_dict[rf_type] = {}
            self.rf_dict[rf_type]['hw'] = self.cp.get(rf_type, 'hw')
            self.rf_dict[rf_type]['dev num'] = self.cp.get(rf_type, "dev_num")
            self.rf_dict[rf_type]['conn type'] = self.cp.get(rf_type, "conn")        
        
    def get_devices(self):
        '''
        Caution: The device API Should have same name of 'hw' in rf_dict
        EX) rf_dict['7.4G']['hw'] = 'SynthHD' => API will be imported as 'from RFdevice import SynthHD'
        '''
        local_ser_list = [dev.serial_number for dev in list_ports.comports()]
        for rf in self.rf_dict:
            if rf['conn type'] == 'serial':
                ser_num = rf['dev num']
                if ser_num in local_ser_list:
                    dev_idx = local_ser_list.index(ser_num)
                    dev_port = list_ports.comports()[dev_idx].device
                exec( "from RFdevice import %s" % rf['hw'])
                exec( "rf['object'] = %s(port=str(%s))" % (rf['hw'], dev_port))
            if rf['conn type'] == 'socket':
                pass
    
    '''
    RF Settings have current device data
    'Rf type': {'curr freq':'real hardware info', 
                'curr power': 'device number(serial number/IP&PORT)', 
                'conn type': 'connection type(serial/socket)'}
    If device is not connected and not read, it might be None value
    '''
    @logger_decorator
    def readSettings(self, rf_type):
        self.rf_settings[rf_type]['curr freq'] = self.readFreq(rf_type)
        self.rf_settings[rf_type]['curr power'] = self.readPower(rf_type)
        print('{} got Current freq: {} MHz'.format(rf_type, self.rf_settings[rf_type]['curr freq']))
        print('{} got Current power: {} dBm'.format(rf_type, self.rf_settings[rf_type]['curr power']))
        

    @logger_decorator
    def openDevice(self, rf_type):
        self.rf_dict[rf_type]['object'].connect()
        self.readSettings(rf_type)
        return 'Opened device'
    
    @logger_decorator
    def closeDevice(self, rf_type, close_all = False):
        if close_all:
            for rf in self.rf_dict:
                rf.disconnect(rf_type)
        else:
            self.rf_dict[rf_type]['object'].disconnect()
            self.rf_settings[rf_type]['curr freq'] = None
            self.rf_settings[rf_type]['curr power'] = None
        return 'Closed device'    
    
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
    - SET Freq / SET Power / Turn On / Turn Off / Change channel
    - SETF    /  SETP     /  TON    /  TOFF    / CH
    Data : value of command - freq / power
    Client : client id for this message
    
    Let the command has the form 'RF_Type:SET_?'
    EX) '7.4G:SETF', '7.4G:SETP'
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
                    result, toall = self.applyFreq(rftype, data), True
                if command == "SETP":
                    result, toall = self.applyPower(rftype, data), True
                if command == "TON":
                    result, toall = self.enable_output(rftype), True
                if command == "TOFF":
                    result, toall = self.disable_output(rftype), True
                # if command == "CH":
                #     msg = self.set_channel(rftype, data)
                #     self.informClients(msg, self.client_list)
                    
                elif command == "ON":
                    """
                    When a client is connected, opens the devcie and send voltage data to the client.
                    """
                    print("opening the device")
                    dev = self.rf_dict[rftype]['object']
                    if not dev.is_connected():
                        result = 'Hello, ' + self.openDevice(rftype)
                    else:
                        result = 'Hello, Device is already opened'
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
                        result = self.safeOff(rftype)
                        # self.closeDevice(rftype)
                        self.toLog("info", "No client is connected. closing the device.")
                    toall = False
                
            elif work_type == "Q":
                if command == "FREQ":
                    data = work[2]
                    result, toall = self.readFreq(rftype), False
    
                if command == "POWER":
                    data = work[2]
                    result, toall = self.readPower(rftype), False
                       
            else:
                self.toLog("critical", "Unknown work type(%s) has been detected." % work_type)
        
            
            msg = ['D', '%s:%s' % (rftype, command), command, result]
            if toall == True:
                self.informClients(msg, self.client_list)
            else:
                self.informClients(msg, client)
            
            self._status = "standby"
                         
    
    @logger_decorator
    @not_conneted
    def readPower(self, rftype):
        power = self.rf_settings[rftype]['curr power']
        return power

    @logger_decorator
    @not_conneted
    def readFreq(self, rftype):
        freq = self.rf_settings[rftype]['curr freq']
        return freq
        
    @logger_decorator
    @not_conneted
    def applyFreq(self, rftype, fdata):
        dev = self.rf_dict[rftype]['object']
        try:
            dev.apply_frequency(fdata)
        except Exception as e:
            return e
    
        self.readSettings(rftype)
        if self.rf_settings[rftype]['curr freq'] == fdata:
            return 'Applied Freq {} MHz to {}'.format(fdata, rftype)
        else:
            return 'Warning: {} frequency is not applied properly'.format(rftype)
        
    @logger_decorator
    @not_conneted
    def applyPower(self, rftype, pdata):
        dev = self.rf_dict[rftype]['object']
        try:
            dev.apply_power(pdata)
        except Exception as e:
            return e
    
        self.readSettings(rftype)
        if self.rf_settings[rftype]['curr power'] == pdata:
            return 'Applied Power {} dBm to {}'.format(pdata, rftype)
        else:
            return 'Warning: {} power is not applied properly'.format(rftype)
    
    @logger_decorator
    @not_conneted
    def outputON(self, rftype):
        dev = self.rf_dict[rftype]['object']
        dev.enable_output()
        if dev.is_output_enabled():
            return '{} Output Enabled'.format(rftype)
        else:
            return 'Warning: {} Output not Enabled properly'.format(rftype)
    
    @logger_decorator
    @not_conneted
    def outputOFF(self, rftype):
        dev = self.rf_dict[rftype]['object']
        dev.disable_output()
        if not dev.is_output_enabled():
            return '{} Output Disabled'.format(rftype)
        else:
            return 'Warning: {} Output not Disabled properly'.format(rftype)
    
    @logger_decorator
    @not_conneted
    def safeOff(self, rftype):
        dev = self.rf_dict[rftype]['object']
        curr_power = self.rf_settings[rftype]['curr power']
        if curr_power > -10:
            while curr_power <= -30:
                dev.apply_power(curr_power)
                curr_power -= 0.1
                time.sleep(0.05)
        self.closeDevice(rftype)
        return 'Last client is left. Device is off Safely'
    
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
        
