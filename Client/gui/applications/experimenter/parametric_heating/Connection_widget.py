# -*- coding: utf-8 -*-
"""
Created on Thu Oct  5 10:50:27 2023

@author: QCP75
"""
import os, sys

serial_devices = ["SynthNV", "SynthHD"]
socket_devices = ["SG384", "APSYN420"]

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

# PyQt libraries
from PyQt5 import uic, QtWidgets

connection_ui_file = dirname + "/ui/device_connection_custom.ui"
connection_ui, _ = uic.loadUiType(connection_ui_file)

internal_dev_ui_file = dirname + "/ui/device_connection_internal.ui"
internal_dev_ui, _ = uic.loadUiType(connection_ui_file)


class CustomDevice(QtWidgets.QWidget, connection_ui):
    
    
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)
        self.parent = parent
        self.con_type = "Serial"
        
        self.serial_devices = serial_devices
        self.socket_devices = socket_devices
        self.device_list = []
        self.device_type = ""
        
        self.setupUi(self)
        self.CBOX_connection_type.addItems(["Serial", "Socket"])
        sys.path.append(dirname)
        

    def changedConnection(self, connection_type):
        self.con_type = connection_type
        
        if connection_type == "Serial":
            self.NON_con1.setText("COM")
            self.NON_con2.setText("Baud\nRate")
        else:
            self.NON_con1.setText("IP")
            self.NON_con2.setText("Port")
            
        self.fillDeviceComboBox()
        
    def fillDeviceComboBox(self):
        self.CBOX_device.clear()
        if self.con_type == "Serial":
            self.CBOX_device.addItems(self.serial_devices)
            self.device_list = self.serial_devices
            
        else:
            self.CBOX_device.addItems(self.socket_devices)
            self.device_list = self.socket_devices
            
            
    def pressedConnect(self, flag):
        if flag:
            try:
                self.device_type = self.CBOX_device.currentText()
                exec("from RFdevice import %s as dev" % self.device_type)
                exec("self.device = dev()")
                if self.con_type == "Serial":
                    self.device.port = self.TXT_con1.text()
                else:
                    self.device.tcp_ip = self.TXT_con1.text()
                    self.device.tcp_port = int(self.TXT_con2.text())
                self.device.connect()
                self.toStatusBar("Connected to the device (%s)." % self.device_type)
                self._setOutputChannel()
            except Exception as err:
                self.toStatusBar("An error while connecting the device (%s)." % err)
                self.BTN_connection.setChecked(False)
                flag = not flag
        else:
            self.device.disconnect()
            self.toStatusBar("Disconnected from the device (%s)" % self.device_type)
        self._enableGUI(flag)

            
    @property
    def isConnected(self):
        if not self.device == None:
            return self.device.is_connected()
        
    @property
    def channel_index(self):
        return self.CBOX_channel.currentIndex()
    
    def setPower(self, power):
        self.device.setPower(power, self.CBOX_channel.currentIndex())
        
    def enableOutput(self):
        self.device.enableOutput(self.CBOX_channel.currentIndex())
        
    def disableOutput(self):
        self.device.disableOutput(self.CBOX_channel.currentIndex())
        
    def setFrequency(self, frequency):
        self.device.setFrequency(frequency, self.CBOX_channel.currentIndex())
        
    def readFrequency(self):
        return self.device.getFrequency(self.CBOX_channel.currentIndex())
        
    def toStatusBar(self, txt):
        if not self.parent == None:
            self.parent.toStatusBar(txt)
        else:
            print(txt)

    def _enableGUI(self, flag):
        self.CBOX_connection_type.setEnabled(not flag)
        self.CBOX_device.setEnabled(not flag)
        
    def _setOutputChannel(self):
        self.CBOX_channel.clear()
        if "SG3" in self.device_type:
            self.CBOX_channel.addItems(["BNC", "N-type"])
        else:
            self.CBOX_channel.addItems( [str(x) for x in range(self.device._num_channels)] )

class InternalRF_Device(QtWidgets.QWidget, internal_dev_ui):
    
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)
        self.parent = parent
        self.device_dict = self.parent.device_dict
        self.rf_device = self.device_dict["rf"]
        self.rf_device._gui_update_signal.connect(self.updateSettings)
        
        self.fillDeviceComboBox()
        
    def changedConnection(self, connection_type):
        pass
        
    def fillDeviceComboBox(self):
        self.CBOX_device.clear()
        for rf_device in self.rf_device.RF_dict.keys():
            self.CBOX_device.addItems(rf_device)
            
    def pressedUpdateDevices(self):
        self.fillDeviceComboBox()
            
    def pressedConnect(self, flag):
        if flag:
            try:
                device_nick = self.CBOX_device.currentText()
                self.rf_device.openDevice(device_nick)
                
                self.toStatusBar("Connected to the device (%s)." % self.device_type)
                self._setOutputChannel()
            except Exception as err:
                self.toStatusBar("An error while connecting the device (%s)." % err)
                self.BTN_connection.setChecked(False)
                flag = not flag
        else:
            self.device.disconnect()
            self.toStatusBar("Disconnected from the device (%s)" % self.device_type)
            self.CBOX_device.clear()
        self._enableGUI(flag)

            
    @property
    def isConnected(self):
        if not self.device == None:
            return self.device.is_connected()
        
    @property
    def channel_index(self):
        return self.CBOX_channel.currentIndex()
    
    def setPower(self, power):
        self.device.setPower(power, self.CBOX_channel.currentIndex())
        
    def enableOutput(self):
        self.device.enableOutput(self.CBOX_channel.currentIndex())
        
    def disableOutput(self):
        self.device.disableOutput(self.CBOX_channel.currentIndex())
        
    def setFrequency(self, frequency):
        self.device.setFrequency(frequency, self.CBOX_channel.currentIndex())
        
    def readFrequency(self):
        return self.device.getFrequency(self.CBOX_channel.currentIndex())
        
    def toStatusBar(self, txt):
        if not self.parent == None:
            self.parent.toStatusBar(txt)
        else:
            print(txt)

    def _enableGUI(self, flag):
        self.CBOX_connection_type.setEnabled(not flag)
        self.CBOX_device.setEnabled(not flag)
        
    def _setOutputChannel(self):
        self.CBOX_channel.clear()
        if "SG3" in self.device_type:
            self.CBOX_channel.addItems(["BNC", "N-type"])
        else:
            self.CBOX_channel.addItems( [str(x) for x in range(self.device._num_channels)] )
            
    def updateSettings(self, rf_device:str, command:str, data:list):
        if rf_device == self.CBOX_device.currenctText():
            if command in ["c", "con"]:
                flag = data[0]
                self.BTN_connection.setChecked(flag)
                self.fillDeviceComboBox()
            elif command in ["STAT", "g"]:
                self.updateAmplitude()
                
            
            # if cmd == "STAT":
            #     self.updateAllParameters()
            #     self.readConfig()
            # elif cmd in ["c", "con"]:
            #     flag = data[0]
            #     self.BTN_connect.setChecked(flag)
            #     if flag:
            #         self.toStatusBar("Connected to the device (%s)." % self.device_name)
            #     else:
            #         self.toStatusBar("Disonnected from the device (%s)." % self.device_name)
            #     self.enableInteractionObjects(flag)
            # elif cmd == "g":
            #     flag = data[0]
            #     self.disableWhileUpdating(flag)
            # elif cmd == "e":
            #     if data[0] == "con":
            #         self.toStatusBar("Could not connect to the device! (%s)" % self.device_name)
            #         self.BTN_connect.setChecked(False)
            # elif cmd == "l":
            #     flag = data[0]
            #     self.BTN_lock.setChecked(flag)


if __name__ == "__main__":
    cd = CustomDevice()
    cd.show()