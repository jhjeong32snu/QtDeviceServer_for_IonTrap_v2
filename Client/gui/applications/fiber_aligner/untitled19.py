# -*- coding: utf-8 -*-
"""
Created on Mon Aug 29 11:57:00 2022

@author: QCP32
"""
#%% GUI
class FiberAlginerGUI(QtWidgets.QMainWindow, Ui_Form, fiber_aligner_theme_base):
    
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
            z_pos = float(self.LBL_Z_pos.text())
            self.scanner.moveMotorPosition(x_pos, y_pos, z_pos)
        except Exception as e:
            self.toStatusBar("Positions should be float numbers. (%s)" % e)
    
    
    def pressedReadPosition(self):
        self.readStagePosition()
        
    def readStagePosition(self):
        self.motors.toWorkList(["Q", "POS", ["px", "py"], self])
    
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