# -*- coding: utf-8 -*-
"""
Created on Thu Sep 28 22:51:42 2023

@author: Junho Jeong

"""

import os, sys, time
from math import pi, log, sqrt
from ui_resources.RF_client_device_indicator import DeviceIndicator
filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

sub_file_path = dirname + "/ui_resources"
main_ui_file = sub_file_path + "/RF_controller_main_ui.ui"
ref_ui_file = sub_file_path + "/sub_widgets/channel_refbox_ui.ui"
channel_ui_file = sub_file_path + "/sub_widgets/channel_groupbox_ui.ui"

from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QDoubleSpinBox, QSlider
from PyQt5.QtGui import QDoubleValidator
from RF_client_controller_v2 import RF_ClientInterface

main_ui, _ = uic.loadUiType(main_ui_file)
ref_ui,  _ = uic.loadUiType(ref_ui_file)
channel_ui,  _ = uic.loadUiType(channel_ui_file)


class RF_ControllerGUI(QtWidgets.QWidget, main_ui):
    
    __di_dict = {}
        
    def __init__(self, parent=None, device_dict={}):
        QtWidgets.QWidget.__init__(self)
        self.controller = parent
        self.device_dict = device_dict
        self.setupUi(self)
        self.panel_dict = {}
        # self._initUi(device_dict)
        self.tabWidget.currentChanged.connect(self.deviceChanged)
        
        if len(self.device_dict):
            self.setupDevices(self.device_dict)
        
    # def addDevice(self, devcice):
        
        
    def setupDevices(self, device_dict):
        for device_name, device_params in device_dict.items():
            
            layout = QVBoxLayout()
            layout_widget = QtWidgets.QWidget()
            layout_widget.setLayout(layout)
            
            curr_dev = RF_DeviceWidget()
            layout.addWidget(curr_dev)
            
            self.tabWidget.addTab(layout_widget, device_name)
            di = DeviceIndicator(self, device_name)
            di.createLabel(self.IndicatorLayout)
            di.setFlagReferences(curr_dev.BTN_on)
            curr_dev.BTN_on.toggled.connect(di.toggleStatus)
            self.panel_dict[device_name] = curr_dev
            self.__di_dict[device_name] = di
        
        
    def deviceChanged(self, idx):
        print(idx)

    def pressedConButton(self, flag):
        pass
        # self.controller.

        
        
class RF_DeviceWidget(QtWidgets.QWidget, channel_ui):
    
    _power_unit = ""
    _freq_unit  = ""
    _phase_unit = ""
    
    _power = 0 # we have the power always in dBm
    _freq = 0 # we have the frequency always in Hz
    _phase = 0 # we have the phase always in degree
    
    _default_stylesheet = ""
    _not_updated_stylesheet = "background-color:rgb(255, 255, 0)"
    
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)
        self.parent = parent
        self.setupUi(self)
        
    def updatePower(self, value):
        self._power = value
        self.SPB_power.setValue(self._power)
        self.SPB_power.setStyleSheet(self._default_stylesheet)
        
    def updateFreq(self, value):
        self._freq = value
        self.SPB_freq.setValue(self._freq)
        self.SPB_freqr.setStyleSheet(self._default_stylesheet)
        
    def updatePhase(self, value):
        self._phase = value
        self.SPB_phase.setValue(self._phase)
        self.SPB_phase.setStyleSheet(self._default_stylesheet)
        
    def saveSpinBoxStyleSheet(self, stylesheet):
        self._stylesheet = stylesheet
    
    def changedPower(self, value):
        self._power = value
            
    def editedPower(self):
        self.SPB_power.setStyleSheet(self._not_updated_stylesheet)
        
    def changedPowerUnit(self, unit):
        if unit == "Vpp":
            self.SPB_power.setValue(self.dBm_to_vpp(self._power))
        elif unit == "dBm":
            self.SPB_power.setValue(self._power)
        elif unit == "mW":
            self.SPB_power.setValue(self.dBm_to_mW(self._power))
        self.SPB_power.setStyleSheet(self._default_stylesheet)
        
    def changedPowerStep(self, step):
        self.SPB_power.setSingleStep(step)
                
    def editedFreq(self):
        self.SPB_freq.setStyleSheet(self._not_updated_stylesheet)
        
    def changedFreqUnit(self, unit):
        if unit == "kHz":
            divider = 1e3
        elif unit == "MHz":
            divider = 1e6
        elif unit == "GHz":
            divider = 1e9
        self._freq_unit = unit
        self.SPB_freq.setValue(self._freq/divider)
        self.SPB_freq.setStyleSheet(self._default_stylesheet)

            
    def changedFreqStep(self, step):
        self.SPB_freq.setSingleStep(step)

    def editedPhase(self):
        self.SPB_phase.setStyleSheet(self._not_updated_stylesheet)

    def changedPhaseUnit(self, unit):
        if unit == "degree":
            self.SPB_phase.setValue(self._phase)
        else:
            self.SPB_phase.setValue(self._phase/(2*pi))
        self._phase_unit = unit
        self.SPB_phase.setStyleSheet(self._default_stylesheet)

    def changedPhaseStep(self, step):
        self.SPB_phase.setSingleStep(step)
            
    def dBm_to_vpp(self, dBm):
        volt = 2*sqrt((100)/1000)*10**(dBm/20)
        return volt
        
    def vpp_to_dBm(self, vpp):
        dBm = 20*log(vpp/sqrt(8)/(0.001 * 50)**0.5, 10)
        return dBm
    
    def dBm_to_mW(self, dBm):
        mW = 10**(dBm/10)
        return mW
    
    def mW_to_dBm(self, mW):
        dBm = 10*log(mW, 10)
        return dBm
    


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    if app is None:
        app = QtWidgets.QApplication([])
    temp_device_dict = {"EA_RF": {"num_ch": 2},
                        "EC_RF": {"num_ch": 2},
                        "EOM_7G": {"num_ch": 1}}
    RF = RF_ControllerGUI(None, temp_device_dict)
    RF.setWindowTitle("RF GUI v2")
    RF.show()