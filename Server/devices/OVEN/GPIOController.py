# -*- coding: utf-8 -*-
"""
Created on Tue Oct 25 13:48:03 2022

@author: QCP32
@author: pi
"""
import time, os
from PyQt5.QtCore import QThread, QObject, QTimer, pyqtSignal
import platform
import RPi.GPIO as G
from queue import Queue

conf_dir = os.path.dirname(__file__) + '/Libs/'
conf_file = platform.node() + '.conf'

class GPIO_HandlerQT(QThread):
    
    _pin_assignment = {}
    _connection_flag = False
    _operation = False
    _channel = 1
    _target = 0
    _status = "standby"
    _voltage = 0
    _current = 0
    _force_off = False
    
    sig_oven_control = pyqtSignal()
    
    def __init__(self, parent=None, config=None, device="GPIO"):
        super().__init__()
        self.parent = parent
        self.cp = config
        self._G = G
        self._G.setwarnings(False)
        self.que = Queue()

        self.device = device
        try: 
            self._G.cleanup()
            print("GPOI pins are reseted.")
        except: pass
        self._G.setmode(self._G.BCM)

        self._readConfig()
        
    def __call__(self):
        return self._pin_assignment
    
    def _readConfig(self):
        if self.cp == None:
            print("No config file has been found.")
        else:
            config_dict = dict(self.cp.items("GPIO"))
            
            for key, val in 
        
    def setPinOut(self, pin_num, out_flag):
        try:
            if out_flag:
                self._G.setup(self.pin_num, self._G.OUT)
            else:
                self._G.setup(self.pin_num, self._G.IN)
                
            self.pin_assignment[self.pin_num] = "OUT" if out_flag else "IN"
                
        except Exception as err:
            print("An error has been occured when setting the pin(%d), (%s)" % (pin_num, err))
        
        
    @property
    def pin(self):
        return self._pin_assignment
        
    @property
    def connection(self):
        return self._connection_flag
    
    @connection.setter
    def connection(self, flag):
        self._connection_flag = flag
        
    @property
    def operation(self):
        return self._operation
    
    @operation.seter
    def operation(self, flag):
        self._operation = flag
        
    @property
    def channel(self):
        return self._channel
    
    @channel.setter
    def channel(self, ch):
        self._channel = ch
        
    @property
    def target_value(self):
        return self._target
    
    @target_value.setter
    def target_value(self, target):
        self._target = target
        
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, stat):
        self._status = stat
        
    @property
    def voltage(self):
        return self._voltage
    
    @voltage.setter
    def voltage(self, value):
        self._voltage = value
        
    @property
    def current(self):
        return self._current
    
    @current.setter
    def current(self, value):
        self._current = value
        
    @property
    def time(self):
        return self.oven_timer.time
    
    def setDeviceFile(self, file_name, class_name, model_name):
        self.file_name = file_name
        self.class_name = class_name
        self.model_name = model_name
        
    def run(self):
        while self.operation:
            oven_status = self._oven_run()
            if not oven_status:
                self.operation = False
                
            time.sleep(0.2)
            
        self.sig_oven_control.emit()
            
    def openDevice(self, port=None, stopbits=2, timeout=2):
        """
        It opens the device moudule following the user's file and class name.
        **I believe there's a better design than this. but I was in a hurry.
        """
        if not (self.file_name == "" or self.file_name == ""):
            if port == None:
                port = self._discover_device()
        
        exec("from %s import %s as DC" % (self.file_name, self.class_name))
        
        try:
            exec("self.DC = DC(port, stopbits, timeout)")
            self.DC.WriteDev('*IDN?')
            line = self.DC.ReadDev()
            if self.model_name in line:
                print("Connected to", line)
                self.connection = True
                return 1
            else:
                self.toLog("No/Wrong response from the device.", "error")
                self.DC.close()
                self.DC = None
                return 0
        except Exception as err:
            self.toLog("An error while connecting to the device (%s)." % err, "error")
            return 0
        
    def closeDevice(self):
        if self.connection:
            self.DC.close()
            self.DC = None
        else:
            self.toLog("The device is not yet opened!", "warning")
            
    def _force_off(self):
        print("Forcing off")
        self.status = "off"
        self.operation = True
        if not self.isRunning():
            self.start()
            
    def stopRightNow(self):
        """
        This function is for emergency.
        It downs currents of every cheannels to 0.
        """
        print("Emergency Stopping")
        self.operation = False
        self.status = "off"
        for key in self.DC.Channels.keys():
            self.DC.VoltageOn(key, 0)
            
        print("Done an emergency stop.")
        
    def _oven_run(self):
        time.sleep(0.2)
        self.voltage = self.DC.ReadValue_V(1)
        time.sleep(0.2)
        self.current = self.DC.ReadValue_I(1)
        if self.status == "on":
            if ( (self.target - self.current) > 0.15):
                self.DC.CurrentOn(self.channel, self.current + 0.15)
            else:
                self.DC.CurrentOn(self.channel, self.target)
            return 1
            
        else:
            if not self.current < 0.15:
                self.DC.CurrentOn(self.channel, self.current - 0.15)
                print(self.current)
                return -1
            else:
                self.DC.CurrentOn(self.channel, 0)
                self.current = 0
                return 0
     
    def _discover_device(self, ser_num="A602B73U"):    
        from serial.tools.list_ports import comports
        for dev in comports():
            if dev.serial_number == ser_num:
                return dev.device
        
    
class OvenTimer(QObject):
    
    _sig_Over = pyqtSignal(bool)
    _sig_Time = pyqtSignal(int)
    
    def __init__(self, max_time=480, debug=False):
        super().__init__()
        self.max_time = max_time
        self._time = 0
        
        self.timer = QTimer() 
        self.timer.timeout.connect(self.countdown)
        
        self._debug = debug
        
    @property
    def time(self):
        return self._time
    
    @time.setter
    def time(self, time):
        self._time = time
    
    def start(self):
        self.time = self.max_time
        self.timer.start(1000) # event for every second.
        
    def stop(self):
        self.timer.stop()
        self.time = 0
        self._sig_Over.emit(False)
        
        if self._debug:
            print("Timer stopped!")
        
    def countdown(self):
        self.time -= 1
        
        self._sig_Time.emit(self.time)
            
        if self._debug:
            print("Current time: (%2d:%02d)" % ( (self.time // 60), (self.time % 60)))
            
        if self.time <= 0:
            self.timeOver()
        
    def timeOver(self):
        self.timer.stop()
        self.time = 0
        self._sig_Over.emit(True)
        
        if self._debug:
            print("Time out!")
    
    
if __name__ == '__main__':
    OH = OVEN_HandlerQT()
