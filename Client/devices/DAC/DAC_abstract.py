# -*- coding: utf-8 -*-
"""
Created on Sat Oct  2 11:22:41 2021

@author: Junho Jeong
@Tel: 010-9600-3392
@email1: jhjeong32@snu.ac.kr
@mail2: bugbear128@gmail.com
"""

class DAC_AbstractBase:
    
    channel_num = 16
    voltage_range = [-15, 15]
    
    def openDevice(self):
        """
        """
        
    def closeDevice(self):
        """
        """
        
    def reset(self):
        """
        Set all the channel to 0V.
        """
        
    def setVoltage(self, channel, value):
        """
        Set the output voltage of the given channel.
        """
        
    def readVoltage(self, channel, value):
        """
        Read the output voltage of the given channel.
        """
        
    
        