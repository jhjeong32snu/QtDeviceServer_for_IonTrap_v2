# -*- coding: utf-8 -*-
"""
Created on Thu Sep 28 22:51:42 2023

@author: QCP75
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
from PyQt5.QtCore import pyqtSignal
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
        self.parent = parent
        self.setupUi(self)
        self._initUi(device_dict)
        self._windowResizing(0)
        
    def _initUi(self, device_dict):
        self.panel_dict = {}
        for device_name, device_params in device_dict.items():
            curr_dev = self.panel_dict[device_name] = {}
            curr_dev["ref"] = RF_RefWidget()
            
            layout = QVBoxLayout()
            layout_widget = QtWidgets.QWidget()
            layout_widget.setLayout(layout)
            
            for idx in range(device_params["num_ch"]):
                curr_dev["ch%d" % idx] = RF_ChannelWidget()
                curr_dev["ch%d" % idx].GBOX_channel_title.setTitle("Channel %d" % (idx+1))
                layout.addWidget(curr_dev["ch%d" % idx])
            layout.addWidget(curr_dev["ref"])
            
            layout.setSpacing(6)
            
            self.tabWidget.addTab(layout_widget, device_name)
            di = DeviceIndicator(self, device_name)
            di.createLabel(self.IndicatorLayout)
            di.setFlagReferences([curr_dev["ch%d" % idx].BTN_on for idx in range(device_params["num_ch"])])
            for idx in range(device_params["num_ch"]):
                curr_dev["ch%d" % idx].BTN_on.toggled.connect(di.toggleStatus)
                self.__di_dict[device_name] = di
        self.tabWidget.currentChanged.connect(self._windowResizing)

    def _windowResizing(self, idx):
        dev = self.panel_dict[list(self.panel_dict.keys())[idx]]
        num_ch = len(dev)-1
        minimum_height = int( 260 + num_ch*136 )
        self.setMinimumHeight(minimum_height)
        self.resize(self.size().width(), minimum_height)
        self.updateGeometry()
        
class RF_RefWidget(QtWidgets.QWidget, ref_ui):
    
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)
        self.parent = parent
        self.setupUi(self)
        
class RF_ChannelWidget(QtWidgets.QWidget, channel_ui):
    
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