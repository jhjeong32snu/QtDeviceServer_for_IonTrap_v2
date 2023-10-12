# -*- coding: utf-8 -*-
"""
Created on Thu Sep 28 20:50:28 2023

@author: QCP75
"""

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import QLabel


class DeviceIndicator(QObject):
    
    __stylesheet = {1 : """
                            background:rgb(40,140,40);
                            border-radius: 8px;
                            margin-left: 2px;
                            margin-right:2px;
                            color:rgb(210, 210, 210);
                            font: 87 9pt "Arial Black";
                            """,
                    0: """
                            background:rgb(140,40,40);
                            border-radius: 8px;
                            margin-left: 2px;
                            margin-right:2px;
                            color:rgb(210, 210, 210);
                            font: 87 9pt "Arial Black";
                            """}
    
    def __init__(self, parent=None, device_name=""):
        super().__init__()
        self.parent = parent
        self.device_name = device_name
        
    def connectSignal(self, signal):
        signal.connect(self.toggleStatus)
        
    def createLabel(self, container=None):
        if not container == None:
            self.label = QLabel()
            self.label.setText(self.device_name)
            self.label.setMaximumWidth(len(self.device_name)*12)
            self.label.setMinimumWidth(len(self.device_name)*12)
            self.label.setMaximumHeight(20)
            self.label.setAlignment(Qt.AlignCenter)
            
            container.addWidget(self.label)
            
    def setFlagReferences(self, button):
        if not type(button) == list:
            button = [button]
        self.flag_reference = button
        self.toggleStatus()
            
    def toggleStatus(self):
        flag = 0
        for button in self.flag_reference:
            flag += button.isChecked()
        stylesheet = self.__stylesheet[flag]
        self.label.setStyleSheet(stylesheet)
        