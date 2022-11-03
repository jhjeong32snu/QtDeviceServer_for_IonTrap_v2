# -*- coding: utf-8 -*-
"""
Created on Sun Nov 28 09:52:59 2021

@author: QCP32
"""
################ Importing Sequencer Programs ###################
# import sys
# sys.path.append("Q://Experiment_Scripts/GUI_Control_Program/RemoteEntangle/Sequencer/Sequencer Library")
# from SequencerProgram_v1_07 import SequencerProgram, reg
# import SequencerUtility_v1_01 as su
# from ArtyS7_v1_02 import ArtyS7
# import HardwareDefinition_EC as hd

################# Importing Hardware APIs #######################
  # Thorlabs KDC101 Motor Controller
# from DUMMY_PMT import PMT

################ Importing GUI Dependencies #####################
import os, time, sys
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QVBoxLayout, QPushButton
from PyQt5.QtCore    import pyqtSignal, QThread, QObject

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import configparser, pathlib

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)
uifile = dirname + '/fiber_aligner_v1.ui'
widgetdir = dirname + '/widgets/'

Ui_Form, QtBaseClass = uic.loadUiType(uifile)
version = "1.0"

#%% Temporary
from motor_opener import MotorOpener
from fiber_aligner_theme import fiber_aligner_theme_base

class ScanModule(QObject):
    
    _current_position = {"x": 0, "y": 0, "z": 0}
    _scan_range = {"x": [0, 0],
                   "y": [0, 0],
                   "z": [0, 0]}
    
    _scan_array = {"x": [0],
                   "y": [0],
                   "z": [0]}
    
    _scan_step = {"x": 0.001, "y": 0.001, "z": 0.001}
    
    _opened_module = False
    _sig_move_done = pyqtSignal()
    
    scanning_flag = False
    
    def _connectSignals(self):
        self._sig_move_done.connect(self._doneMoving)

    def toStatusBar(self, msg):
        print(msg)
    
    def _set_Range_n_Array(self, key, val):
        self._scan_range[key] = val
        self._scan_array[key] = np.arange(val[0], val[-1] + self._scan_step[key], self._scan_step[key])
        
    def _find_value_in_Array(self, value, axis):
        where = np.where(self._scan_array[axis] == value)[0]
        if not len(where):
            self.toStatusBar("Coudln't find the value (%f) in the axis (%s)" % (value, axis))
        else:
            idx = where[0]
            
            return idx
        
    def _doneMoving(self):
        print("not ey")
        # if self.scanning_flag:
        #     self.runPMT_Exposure()
        
    def _doneExposure(self):
        if self.scanning_flag:
            self.runPMT_Exposure()
        
    def _initialize_parameters(self):
        pass


# class PMTAlignerMain(QtWidgets.QMainWindow, Ui_Form, pmt_aligner_theme_base):
class PMTAlignerMain(ScanModule):
        
    def __init__(self, device_dict=None, parent=None, theme="black"):
        super().__init__()
        self.device_dict = device_dict
        self.parent = parent
        self._theme = theme
        self.gui = None
        self.cp = self.parent.cp
        
    def openOpener(self):
        if not self._opened_module:
            opener = MotorOpener(self.device_dict["motors"], self._theme)
            opener.changeTheme(self._theme)
            opener._finished_initialization.connect(self.initiateUi)
            
            opener.show()
            self.device_dict["motors"].openDevice(["fx", "fy", "fz"])
        else:
            self.initiUi()
            
    
    def show(self):
        if not self._opened_module:
            self.openOpener()
        
        else:
            self.gui.show()
    
    def initiateUi(self):
        try:
            self.gui = FiberAlginerGUI(self.device_dict, self, self._theme)
            self.gui.changeTheme(self._theme)
            self._opened_module = True
            self.show()
            
            self._connectSignals()
        except Exception as err:
            print(err)
                    
    def setStyleSheet(self, stylesheet):
        self.styleSheetString = stylesheet
        
    #%% control modules
    def moveMotorPosition(self, x_pos, y_pos, z_pos):
        self.motors.toWorkList(["C", "MOVE", ["fx", x_pos, 
                                              "fy", y_pos,
                                              "fz", z_pos,
                                              self]])
        
    def readStagePosition(self):
        self.motors.toWorkList(["Q", "POS", ["fx", "fy", "fz"], self])
        
    def runPMT_Exposure(self, num_run = 50):
        self.setExposureTime(self.pmt_exposure_time_in_ms, num_run)
        self.sequencer.runSequencerFile()
        
    def setExposureTime(self, exposure_time, num_run=50):
        # CHECK FOR SYNTAX
        self.exposure_time = exposure_time
        self.sequencer.loadSequencerFile(seq_file= dirname + "/simple_exposure.py",
                                         replace_dict={13:{"param": "EXPOSURE_TIME_IN_100US", "value": int(exposure_time*10)},
                                                       14:{"param": "NUM_REPEAT", "value": num_run}})
        
    def startScan(self, **kwargs):
        for key, val in kwargs.items():
            if not key in ["x", "y", "z"]:
                self.toStatusBar("An unknown key has been detected. (%s)" % key)
                return # quit for safty
            else:
                # ScanModule reference
                self._set_Range_n_Array(key, val)
                
        self.scanning_flag = True
        
        
    def _recievedPosition(self):
        if self.scanning_flag:
            self.runPMT_Exposure()
            return
        else:
            self.user_run_flag = False
        
    def toMessageList(self, msg):
        if msg[2] == "POS":
            data = msg[-1]
            
            nickname_list = data[0::2]
            position_list = data[1::2]
            
            for nickname, position in zip(nickname_list, position_list):
                if nickname == "fx":
                    self.x_pos = round(position, 3)
                elif nickname == "fy":
                    self.y_pos = round(position, 3)
                elif nickname == "fz":
                    self.z_pos = round(position, 3)
            self._sig_move_done.emit()
            
    def _doneMoving(self):
        print("yo!")
        # if self.scanning_flag:
        #     self.runPMT_Exposure()
        
    def _doneExposure(self):
        pass
        
    def toStatusBar(self, msg):
        if self.gui == None:
            print(msg)
        else:
            self.gui.toStautsBar(msg)
    