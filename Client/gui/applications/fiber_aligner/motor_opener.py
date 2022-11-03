# -*- coding: utf-8 -*-
"""
Created on Wed Nov 24 21:43:32 2021

@author: QCP32
"""
import time
# PyQt libraries
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QThread, QObject, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout

from progress_bar import ProgressBar

class MotorOpener(QtWidgets.QWidget):
    
    _first_shown = True
    _finished_initialization = pyqtSignal()
    
    def __init__(self, device_dict={}, parent=None, theme="black"):
        QtWidgets.QWidget.__init__(self)
        self.device_dict = device_dict
        self.parent = parent
        self.cp = parent.cp
        self._theme = theme
        self.initUi()
        self.connectSignals()
        
    def changeTheme(self, theme):
        self._theme = theme
        styleSheet = {"white": "background-color:rgb(255, 255, 255)",
                      "black": "background-color:rgb(40, 40, 40); color:rgb(180, 180, 180)"}
        
        self.setStyleSheet(styleSheet[self._theme])

        
    def initUi(self):
        frame = QVBoxLayout()
        self.progress_bar = ProgressBar(self, self._theme)
        frame.addWidget(self.progress_bar)
        frame.setContentsMargins(0, 0, 0, 0)
        self.setLayout(frame)
        self.progress_bar.changeTheme(self._theme)
        
        self.resize(500, 60)
        self.setWindowTitle("KDC101 Loader")
        
    def connectSignals(self):
        motor = self.device_dict["motors"]
        motor._sig_motor_initialized.connect(self.changeProgressBar)
        motor._sig_motor_finished_loading.connect(self.finishLoadingMotors)
        
    
    def changeProgressBar(self, curr_idx, max_idx):
        self.progress_bar.changeProgressBar(curr_idx, max_idx)
        self.progress_bar.changeLabelText("Initiating motors (%d/%d)..." % (curr_idx, max_idx))
        
    
    def finishLoadingMotors(self):
        self.progress_bar.completeProgressBar(True)
        self.progress_bar.changeLabelText("Building up GUI...")
        
        self._finished_initialization.emit()
        self.close()
        
    
        
if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    mo = MotorOpener()
    mo.show()