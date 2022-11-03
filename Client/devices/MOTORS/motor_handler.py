# -*- coding: utf-8 -*-
"""
Created on Mon Aug 22 10:27:50 2022

@author: QCP32
"""
from PyQt5.QtCore import QThread, pyqtSignal
from queue import Queue
version = "1.1"

def ignoreWhenBusy(func):
    """
    A decorator that checks if the thread is busy.
    If it is busy, it ignores any commands.
    This is gonna prevent a long-scheduled queue.
    """
    def wrapper(self, *args):
        if self.isRunning():
            raise RuntimeWarning("The device is busy. ignore the command.")
        else:
            self._que.put([func, *args])
            self.start()
        
    return wrapper


class MotorHandler(QThread):
    """
    The controller class uses QThread class as a base, handling commands and the device is done by QThread.
    This avoids being delayed by the main thread's task.
    
    The logger decorate automatically record the exceptions when a bug happens.
    """
    _position = 0
    _status = "standby"
    _nickname = "motor"
    _serial = None
    _is_opened = False
    
    _sig_motor_initialized = pyqtSignal(bool)
    _sig_motor_error = pyqtSignal(str)
    _sig_motor_move_done = pyqtSignal()
    _sig_motor_homed = pyqtSignal()
    
    def __init__(self, controller=None, ser=None, dev_type="Dummy", nick="motor"):  # cp is ConfigParser class
        super().__init__()
        self.parent = controller
        self.dev_type = dev_type
        
        self.serial = ser
        self.nickname = nick
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
        
    
    @ignoreWhenBusy
    def openDevice(self):
        """
        If the force flag is true even if the device is already opened, it will be restarted.
        """
        if self.dev_type == "Dummy":
            from Dummy_motor import DummyMotor as KDC101
        elif self.dev_type == "KDC101":
            from KDC101 import KDC101
        
        if self._is_opened:
            self._sig_motor_error.emit("%s is already opened." % self.nickname)
            return True
                 
        try:
            self._motor = KDC101(self.serial)
            self._status = "initiating"
            self._motor.open_and_start_polling()
            self.position = self._motor.get_position()
            self._sig_motor_initialized.emit(True)
            
        except Exception as e:
            self._sig_motor_error.emit("An error while loading a motor %s.(%s)" % (self.nickname, e))

    @ignoreWhenBusy
    def testFunction(self, a, b):
        print(a+b)
        
    @ignoreWhenBusy
    def moveToPosition(self, target_position):
        self._status = "moving"
        self._motor.move_to_position(target_position)
        self.position = self._motor.get_position()
        self._sig_motor_move_done.emit()
        
    @ignoreWhenBusy
    def forceHome(self):
        self._status = "homing"
        self._motor.home(force=True, verbose=False)
        self._sig_motor_homed.emit()
           
    def closeDevice(self):
        if self._is_opened:
            self._motor.close()
            self._is_opened = False
            self._sig_motor_initialized.emit(False)
        else:
            self._sig_motor_error.emit("The motor %s is not opened yet!" % self.nickname)

    def run(self):
        while self._que.qsize():
            data = self._que.get()
            func = data[0]
            args = data[1:]
            self._status  = "running"
            func(self, *args)