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
uifile = dirname + '/pmt_aligner_v2.ui'
widgetdir = dirname + '/widgets/'

Ui_Form, QtBaseClass = uic.loadUiType(uifile)
version = "2.12"

#%% Temporary
from motor_opener import MotorOpener
from pmt_aligner_theme import pmt_aligner_theme_base

# class PMTAlignerMain(QtWidgets.QMainWindow, Ui_Form, pmt_aligner_theme_base):
class PMTAlignerMain(QObject):
    
    _opened_module = False
    
    def __init__(self, device_dict=None, parent=None, theme="black"):
        super().__init__()
        self.device_dict = device_dict
        self.parent = parent
        self._theme = theme
        self.pmt_aligner_gui = None
        self.cp = self.parent.cp
        
    def openOpener(self):
        if not self._opened_module:
            opener = MotorOpener(self.device_dict["motors"], self._theme)
            opener.changeTheme(self._theme)
            opener._finished_initialization.connect(self.initiateUi)
            
            opener.show()
            self.device_dict["motors"].openDevice(["px", "py"])
        else:
            self.initiUi()
            
    
    def show(self):
        if not self._opened_module:
            self.openOpener()
        else:
            self.pmt_aligner_gui.show()
            
    def showNormal(self):
        if not self.pmt_aligner_gui == None:
            self.pmt_aligner_gui.showNormal()
    
    def raise_(self):
        if not self.pmt_aligner_gui == None:
            self.pmt_aligner_gui.raise_()
            
    def activateWindow(self):
        if not self.pmt_aligner_gui == None:
            self.pmt_aligner_gui.activateWindow()
    
    def initiateUi(self):
        try:
            self.pmt_aligner_gui = PMTAlginerGUI(self.device_dict, self, self._theme)
            self.pmt_aligner_gui.changeTheme(self._theme)
            self._opened_module = True
            self.show()
        except Exception as err:
            print(err)
        
    def setStyleSheet(self, stylesheet):
        self.styleSheetString = stylesheet
        
        
class PMTAlginerGUI(QtWidgets.QMainWindow, Ui_Form, pmt_aligner_theme_base):
    
    def __init__(self, device_dict=None, parent=None, theme="black"):
        QtWidgets.QMainWindow.__init__(self)
        
        self.setupUi(self)
        
        self.device_dict = device_dict
        self.motor = self.device_dict["motors"]
        self.sequencer = self.device_dict["sequencer"]
        
        self.parent = parent
        self._theme = theme
        self.cp = self.parent.cp
        
        self._initUi()
        self._connectSignals()
        
        self.scanner.readStagePosition()
        self.setWindowTitle("PMT Aligner v%s" % version)
        
        
    def pressedConnectSequencer(self, flag):
        if flag:
            open_result = self.sequencer.openDevice()
            if open_result == -1:
                self.sender().setChecked(False)
                self.toStatusBar("Failed opening the FPGA.")
        else:
            self.sequencer.closeDevice()
                
    def pressedMovePosition(self):
        try:
            x_pos = float(self.LBL_X_pos.text())
            y_pos = float(self.LBL_Y_pos.text())
            self.scanner.moveMotorPosition(x_pos, y_pos)
        except Exception as e:
            self.toStatusBar("Positions should be float numbers. (%s)" % e)
    
    
    def pressedReadPosition(self):
        self.scanner.readStagePosition()
    
    def _initUi(self):
        sys.path.append(widgetdir)
        from scanner import Scanner
        from count_viewer import CountViewer
        self.scanner = Scanner(device_dict=self.device_dict, parent=self, theme=self._theme)
        self.count_viewer = CountViewer(device_dict=self.device_dict, parent=self, theme=self._theme)
        
        self._addTabWidget(self.scanner, "2D Scanner")
        self._addTabWidget(self.count_viewer, "PMT Count Viewer")
        
        if self.sequencer.is_opened:
            self.BTN_connect_sequencer.setChecked(True)
            
            
    def toStatusBar(self, msg):
        self.statusbar.showMessage(msg)
        
    def _connectSignals(self):
        self.scanner.sig_move_done.connect(self._updatePosition)
        self.sequencer.sig_occupied.connect(self._setInterlock)
        self.sequencer.sig_dev_con.connect(self._changeFPGAConn)
        
    def _setInterlock(self, occupation_flag):
        if occupation_flag:
            self.BTN_connect_sequencer.setEnabled(False)
            if self.sequencer.occupant == "scanner":
                self.BTN_SET_pos.setEnabled(False)
                self.BTN_READ_pos.setEnabled(False)
        else:
            self.BTN_connect_sequencer.setEnabled(True)
            self.BTN_SET_pos.setEnabled(True)
            self.BTN_READ_pos.setEnabled(True)
            
    def _changeFPGAConn(self, conn_flag):
        self.BTN_connect_sequencer.setChecked(conn_flag)
            
    def _updatePosition(self):
        self.LBL_X_pos.setText("%.3f" % self.scanner.x_pos)
        self.LBL_Y_pos.setText("%.3f" % self.scanner.y_pos)
        
    def _addTabWidget(self, widget, title):
        self.TabWidgetMain.addTab(widget, title)
