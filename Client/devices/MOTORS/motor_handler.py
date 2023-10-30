# -*- coding: utf-8 -*-
"""
Created on Mon Aug 22 10:27:50 2022

@author: Junho Jeong

"""
from PyQt5.QtCore import QThread, pyqtSignal
from queue import Queue
version = "2.1"


class MotorHandler(QThread):
    """
    This class is an API that can easily handle the motor with Qt classes.    
    This handler class handles the motor with a thread and the controller controls all the motors but in signal based operations.
    """
    _motor = None
    _position = 0
    _status = "closed"
    _nickname = "motor"
    _serial = None
    _is_opened = False
    
    _sig_motor_initialized = pyqtSignal(str)
    _sig_motor_error = pyqtSignal(str)
    _sig_motor_move_done = pyqtSignal(str, float)
    _sig_motor_homed = pyqtSignal(str)
    
    def __init__(self, controller=None, ser=None, dev_type="Dummy", nick="motor"):  # cp is ConfigParser class
        super().__init__()
        self.parent = controller
        self.dev_type = dev_type
        
        self.serial = ser
        self.nickname = nick
        self.target = 0
        self._que = Queue()
        
    @property
    def serial(self):
        return self._serial
    
    @serial.setter
    def serial(self, ser):
        if not ser == None:    
            self._serial = ser
        else:
            print("The serial of the motor cannot be None.")
            
    def info(self):
        return {"serial_number": self.serial,
                "position": self.position,
                "status": self._status,
                "type": self.dev_type}
        
    @property
    def nickname(self):
        return self._nickname
    
    @nickname.setter
    def nickname(self, nick):
        self._nickname = nick
        
    @property
    def position(self):
        return self._position
        
    @position.setter
    def position(self, pos):
        self._position = pos
        
    def getPosition(self):
        self.position = round(self._motor.get_position(), 3)
        return self.position
    
    def setTargetPosition(self, target):
        self._target = target
        
        
    def openDevice(self):
        """
        If the force flag is true even if the device is already opened, it will be restarted.
        """
        if self.dev_type == "Dummy":
            from Dummy_motor import DummyKDC101 as KDC101
        elif self.dev_type == "KDC101":
            from KDC101 import KDC101
        
        if self._is_opened:
            self._sig_motor_error.emit("KDC101 Motor %s is already opened." % self.nickname)
            return True
                 
        try:
            self._motor = KDC101(self.serial)
            self._status = "initiating"
            self._motor.open_and_start_polling()
            self._is_opened = True
            self._sig_motor_initialized.emit(self.nickname)
            
        except Exception as e:
            self._sig_motor_error.emit("An error while loading a motor %s.(%s)" % (self.nickname, e))

    def moveToPosition(self, target_position):
        self._status = "moving"
        self._motor.move_to_position(target_position)
        self.position = self.getPosition()
        self._sig_motor_move_done.emit(self.nickname, self.position)
        
    def forceHome(self):
        self._status = "homing"
        self._motor.home(force=True, verbose=False)
        self._sig_motor_homed.emit(self.nickname)
           
    def closeDevice(self):
        if self._is_opened:
            self._motor.close()
            self._motor = None
            self._is_opened = False
            self._status = "closed"
        else:
            self._sig_motor_error.emit("The motor %s is not opened yet!" % self.nickname)
            
            
    def toWorkList(self, cmd):
        self.queue.put(cmd)
        if not self.isRunning():
            self.start()
            
    def run(self):
        while self.queue.qsize():
            work = self.queue.get()
            
            if work == "O": # Open device
                self.openDevice()
                
            elif work == "M": # Move position
                self.moveToPosition(self.target)
                
            elif work == "D": # Disconnect
                self.closeDevice()
                
            elif work == "H": # Homing
                self.forceHome()

            self._status = "standby"
