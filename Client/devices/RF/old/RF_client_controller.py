# -*- coding: utf-8 -*-
"""
@author: KMLee
"""

from PyQt5.QtCore import QThread
from queue import Queue
from configparser import ConfigParser
import os, sys, traceback
# from RFsettings import Device_list

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

'''
This wrapper uses the kwargs for device name
So, when using the set/get functions, you should explicitly define the device name as
func(val, dev_name=device name)
'''        
def requires_device_open(func):
    """Decorator that checks if the device is open.

    Raises:
        RuntimeError - the func is called before the device is open.
    """
    def wrapper(self, *args, **kwargs):
        if self._is_opened[kwargs['dev_name']]:
            return func(self, *args, **kwargs)
        else:
            raise RuntimeError('{} is called before the device is opened.'
                               .format(func.__name__))
    return wrapper
    

class RF_ClientInterface(QThread):
    
    device_type = "RF"
    _status = "standby"
    _is_opened = {}
    _gui_opened = False
    _rf_settings = {}

    def closeEvent(self, e):
        self._gui_opened = False
        self.closeDevice()
    
    def __init__(self, socket=None):
        super().__init__()
        
        self.sck = socket
        self.gui = None
        self.que = Queue()
        self.initRF()
        
    def openGui(self):
        sys.path.append(dirname + '/../')
        from RF_client_GUI import MainController
        self.gui = MainController(controller=self)
        self._gui_opened = True
    
    # When RF Controller is made, it automaticall send the server a command to read info about rf devices connected to server
    def initRF(self):
        self.toSocket(["C", 'RF', "INIT", []])
        
    # If the rf info from server is read, create the device list
    def createDeviceSettings(self, Device_list):
        self.dev_list = Device_list
        # Handling current rf values
        for key in self.dev_list.keys():
            self._rf_settings[key] = {'on': [False for i in range(self.dev_list[key]['num_power'])],
                                      'power': [self.dev_list[key]['min_power'][i] for i in range(self.dev_list[key]['num_power'])],
                                      'freq':[self.dev_list[key]['min_freq'][i] for i in range(self.dev_list[key]['num_freq'])],
                                      'phase':[self.dev_list[key]['min_phase'][i] for i in range(self.dev_list[key]['num_phase'])]}
        # Handling connection state of rf devices
        for key in self.dev_list.keys():
            self._is_opened[key] = False
            
    def openDevice(self, dev_name=None):
        if not dev_name == None:
            if self._is_opened[dev_name]:
                raise RuntimeError ("The device is already open!")
            else:
                self.toSocket(["C", dev_name, "ON", []])
                # self._is_opened[dev_name] = True
        
    @requires_device_open
    def closeDevice(self, dev_name=None):
        if not dev_name == None:
            self.toSocket(["C", dev_name, "OFF", []])
            # self._is_opened[dev_name] = False
        
    # Set functions
    @requires_device_open
    def enableOutput(self, odata:list, dev_name=None):
        if not dev_name == None:
            assert len(odata) == self.dev_list[dev_name]['num_power']
            msg = ["C", dev_name, "OUT", odata]
            self.toSocket(msg)
    
    @requires_device_open
    def setPower(self, pdata:list, dev_name=None):
        if not dev_name == None:
            assert len(pdata) == self.dev_list[dev_name]['num_power']
            msg = ["C", dev_name, "POWER", pdata]
            self.toSocket(msg)
                
    @requires_device_open
    def setFrequency(self, fdata:list, dev_name=None):
        if not dev_name == None:
            assert len(fdata) == self.dev_list[dev_name]['num_freq']
            msg = ["C", dev_name, "FREQ", fdata]
            self.toSocket(msg)
    
    @requires_device_open
    def setPhase(self, phdata:list, dev_name=None):
        if not dev_name == None:
            assert len(phdata) == self.dev_list[dev_name]['num_phase']
            msg = ["C", dev_name, "PHASE", phdata]
            self.toSocket(msg)    

    # Read functions
    @requires_device_open
    def getPower(self, dev_name=None):
        if not dev_name == None:
             msg = ["Q", dev_name, "POWER", []]
             self.toSocket(msg)
            
    @requires_device_open
    def getFrequency(self, dev_name=None):
        if not dev_name == None:
            msg = ["Q", dev_name, "FREQ", []]
            self.toSocket(msg)
    
    @requires_device_open
    def getPhase(self, dev_name=None):
        if not dev_name == None:
            msg = ["Q", dev_name, "PHASE", []]
            self.toSocket(msg)    

    @requires_device_open
    def getOutput(self, dev_name=None):
        if not dev_name == None:
            msg = ["Q", dev_name, "OUT", []]
            self.toSocket(msg)    
        
    def toWorkList(self, cmd):
        # cmd = ['D', Command, Result Data List with rf device name] 
        # cmd goes to run
        self.que.put(cmd)
        if not self.isRunning():
            self.start()
            print("Thread started")

    def run(self):
        while True:
            # Received Message has a form
            # ['D', Command, Result Data List with rf device name]
            work = self.que.get()
            self._status  = "running"
            # decompose the job
            work_type, command = work[:2]
            result = work[2]
            data, dev = result[:-1], result[-1]
            print("controller got", work)
            print(data, dev)
            if work_type == "D":
                if command == "HELO":
                    """
                    Successfully received a response from the server
                    Got data of Server Device List
                    """
                    for key in self.dev_list.keys():
                        if key not in data:
                            # Device is not on server
                            del self.dev_list[key]
                
                elif command == "ON":
                    assert len(data) == 1
                    if data[0]==True:
                        self._is_opened[dev] = True
                        print('Successfully opened device')
                    elif data[0]==False:
                        self._is_opened[dev] = False
                        print('Device not opened properly')
                    
                elif command == "OFF":
                    assert len(data) == 1
                    if data[0]==True:
                        self._is_opened[dev] = False
                        print('Successfully closed device')
                    elif data[0]==False:
                        self._is_opened[dev] = True
                        print('Device not closed properly')
                    
                elif command == "POWER":
                    # List of channel powers
                    power = data
                    assert len(data) == self.dev_list[dev]['num_power']
                    self._rf_settings[dev]['power'] = power
                    
                elif command == "FREQ":
                    # List of channel frequencies
                    freq = data
                    assert len(data) == self.dev_list[dev]['num_freq']
                    self._rf_settings[dev]['freq'] = freq
                    
                elif command == "PHASE":
                    # List of channel phases
                    phase = data
                    assert len(data) == self.dev_list[dev]['num_phase']
                    self._rf_settings[dev]['phase'] = phase
                    
                elif command == 'TON':
                    # List of channel output enabled
                    is_on = data
                    assert len(data) == self.dev_list[dev]['num_power']
                    self._rf_settings[dev]['on'] = is_on
                    
                elif command == 'INIT':
                    # List of channel output enabled
                    DEV_LIST = data[0]
                    self.createDeviceSettings(DEV_LIST)
                    if hasattr(self, 'gui'):
                        self.gui.safeRFconnection()
                    
            if not self.gui == None:
                self.gui._gui_callback.emit()
                print("Callback emitted")
            
            self._status = "standby"
    
    def toSocket(self, msg):
        if not self.sck == None:
            self.sck.toMessageList(msg)
        else:
            print(msg)
            
    # def toGUI(self, msg):
    #     if not self.gui == None:
    #         self.gui.toStatus(msg)
    #     else:
    #         print(msg)
            
      
if __name__ == "__main__":
    rf = RF_ClientInterface()