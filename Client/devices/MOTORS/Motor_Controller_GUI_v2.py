# -*- coding: utf-8 -*-
"""
Created on Tue Oct 17 18:51:52 2023

@author: QCP75
"""

import os
from PyQt5 import uic
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QLabel, QLineEdit, QCheckBox


filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)
uifile = dirname + '/motor_status_ui_v2.ui'

Ui_Form, _ = uic.loadUiType(uifile)


class MotorController_GUI(QtWidgets.QWidget, Ui_Form):
    
    def __init__(self, controller=None):
        QtWidgets.QWidget.__init__(self)
        
        self.setupUi(self)
        self.checkBox.setVisible(False)
       
        self.motors = controller
        
        self.motor_idx = 0
        self.motor_dict = {}
        self.setWindowTitle("Motor Controller v2.0")
        
        
    def addMotor(self, nickname="", serial_number=""):
        if nickname in self.motor_dict.keys():
            raise ValueError ("The nickname '%s' is already taken." % nickname)
            return
        
        self.motor_dict[nickname] = {"index": self.motor_idx + 1,
                                     "checkbox": QCheckBox(self),
                                     "nick": QLabel(nickname),
                                     "serno": QLabel(serial_number),
                                     "position": QLineEdit("0"),
                                     "status": QLabel("Closed")}
                                     
        
        for item_idx, item_widget in enumerate(self.motor_dict[nickname].values()):
            if not item_idx == 0:
                self.gridLayout.addWidget(item_widget, self.motor_dict[nickname]["index"], item_idx-1)
                
                if item_widget.metaObject().className() == "QLabel":
                    item_widget.setAlignment(QtCore.Qt.AlignCenter)
        
        self.motor_dict[nickname]["position"].returnPressed.connect(self.returnedMotorPosition)
        self.motor_idx += 1
    
        self.setFixedHeight( int(80 + 25*self.motor_idx) )
        
    def changeMotorStatus(self, nickname, status):
        self.changeItem()
        
    def returnedMotorPosition(self):
        for motor_nick, sub_dict in self.motor_dict.items():
            if self.sender() == sub_dict["position"]:
                nickname = motor_nick
                break
            
        print(nickname)
        # self.motors.move_
        
    def requestedMotorPosition(self):
        pass
        
        
    def changeItem(self, row_idx, col_idx, string):
        if row_idx > len(self.table_dict)-1 or col_idx > 3:
            raise ValueError ("Unexpected row id")
        
        self.tableWidget.item(row_idx, col_idx).setText(string)

        
    def getItem(self, row_idx, col_idx):
        text = self.tableWidget.item(row_idx, col_idx).text()
        return text
        

        
if __name__ == "__main__":
    gui = MotorController_GUI()
    gui.show()