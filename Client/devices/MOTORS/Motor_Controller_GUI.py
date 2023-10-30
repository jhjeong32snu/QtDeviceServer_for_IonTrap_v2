# -*- coding: utf-8 -*-
"""
Created on Tue Oct 17 18:51:52 2023

@author: QCP75
"""

import os, time, sys
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QVBoxLayout, QPushButton, QTableWidgetItem
from PyQt5.QtCore    import pyqtSignal, QThread, QObject

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import configparser, pathlib

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)
uifile = dirname + '/motor_status_ui.ui'

Ui_Form, _ = uic.loadUiType(uifile)

class Delegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 2:
            return super(Delegate, self).createEditor(parent, option, index)

class MotorController_GUI(QtWidgets.QWidget, Ui_Form):
    
    def __init__(self, controller=None):
        QtWidgets.QWidget.__init__(self)
        
        self.setupUi(self)
        delegate = Delegate(self.tableWidget) # This is probably a monkey patch. However, this is the simplest way to modify the table.
        self.tableWidget.setItemDelegate(delegate)
        
        self.parent = controller
        self.table_dict = {}
        self.setWindowTitle("Motor Controller v1.0")
        
        
    def addMotor(self, nickname="", serial_number=""):
        RowCount = self.tableWidget.rowCount()
        
        self.tableWidget.insertRow(RowCount)
        self.tableWidget.setItem(RowCount, 0, QTableWidgetItem(nickname))
        self.tableWidget.setItem(RowCount, 1, QTableWidgetItem(serial_number))
        
        position_table = QTableWidgetItem()
        self.tableWidget.setItem(RowCount, 2, position_table)
        self.tableWidget.setItem(RowCount, 3, QTableWidgetItem())
        
        self.table_dict[nickname] = {
                                    "index": RowCount-1,
                                     "serial_number": serial_number,
                                     "position": 0,
                                     "status": False,
                                     "position_table": position_table}
        

        self.setFixedHeight( int(110 + 30*RowCount) )
        
    def changeMotorStatus(self, nickname, status):
        
        self.changeItem()
        
        
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