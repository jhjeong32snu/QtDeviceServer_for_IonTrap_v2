# -*- coding: utf-8 -*-
"""
Created on Tue Oct 26 10:13:54 2021

@author: QCP32
"""

def requires_connection(func):
    """Decorator that checks the connection before calling func.
    Raises:
        RuntimeError - the func is called without connection.
    """
    def wrapper(self, *args):
        if self._connected:
            return func(self, *args)
        else:
            raise RuntimeError('{} is called with no connection.'
                               .format(func.__name__))
    return wrapper


class DummyDDS():
    
    def __init__(self, ser_num="", com_port=""):
        super().__init__()
        self._connected = False
                
    def openDevice(self):
        if self._connected:
            raise RuntimeError ("The device is alrady open!")
        else:
            self._connected = True

    @requires_connection
    def closeDevice(self):
        self._connected = False
     
    @requires_connection
    def setCurrent(self, board, ch1, ch2, current):
        print("Set the current %d." % current)
  
    @requires_connection
    def setFrequency(self, board, ch1, ch2, freq_in_MHz):
        print("Set the frequency %.4f." % freq_in_MHz)
        
    @requires_connection
    def powerDown(self, board, ch1, ch2):
        print("Power downed.")
        
    @requires_connection
    def powerUp(self, board, ch1, ch2):
        print("Power up.")
        
if __name__ == "__main__":
    my_dds = DummyDDS(ser_num="")