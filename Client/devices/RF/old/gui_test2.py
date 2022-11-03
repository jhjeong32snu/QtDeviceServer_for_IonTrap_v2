# -*- coding: utf-8 -*-
"""
@author: KMLee
"""
import os, sys, time
filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

new_path_list = []
new_path_list.append(dirname + '/ui_resources')
for each_path in new_path_list:
    if not (each_path in sys.path):
        sys.path.append(each_path)

from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import pyqtSignal, QSize, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFileDialog
from RF_client_controller import RF_ClientInterface

main_ui_file = dirname + "/ui_resources/RF_Main2.ui"
controll_ui_file  = dirname + "/ui_resources/RF_Widget.ui"
basic_controll_ui_file  = dirname + "/ui_resources/Basic_controll_widget.ui"

main_ui, _ = uic.loadUiType(main_ui_file)
controll_ui,  _ = uic.loadUiType(controll_ui_file)
basic_controll_ui,  _ = uic.loadUiType(basic_controll_ui_file)

#%% BasicControllWidget
class BasicControllWidget(QtWidgets.QWidget, basic_controll_ui):
    def __init__(self, ch=1, val_type='power'):
        super(BasicControllWidget, self).__init__()
        self.setupUi(self)
        self.ch, self.type = ch, val_type
        self.initUi()
    def initUi(self):
        self.CH.setText('CH ' + str(self.ch))
        if self.type == 'power':
            self.STEP.addItem('dBm')
        if self.type == 'freq':
            self.STEP.addItem('MHz')
            self.STEP.addItem('GHz')
        if self.type == 'phase':
            self.STEP.addItem('degree')
        
        self.VAL.setStyleSheet('background-color:rgb(255,255,255)')
        self.SLD.setStyleSheet('background-color:rgb(150,150,150);color: rgb(255,255,255);border-style: solid;border-width: 0px;')
        self.STEP.setStyleSheet('background-color:rgb(255,255,255);border-style: solid;border-width: 2px;border-color:rgb(200,200,200);')
        self.CH.setStyleSheet('background-color:rgb(200, 200, 200)')
    def sizeHint(self):
        return QSize(320,130)
        
#%% ControllWidget
class ControllWidget(QtWidgets.QWidget, controll_ui):
    def __init__(self, dev=None, num_power=1, num_freq=1, num_phase=1):
        super(ControllWidget, self).__init__()
        self.setupUi(self)
        self.num_power, self.num_freq, self.num_phase = num_power, num_freq, num_phase
        self.dev = dev
        if dev == None:
            self.LBL_DEV.setText('None')
        else:
            self.LBL_DEV.setText(dev)
        self.initUI()

    def initUI(self):
        self.power_controll = []
        for i in range(self.num_power):
            self.power_controll.append(BasicControllWidget(ch=i+1, val_type='power'))

        self.freq_controll = []
        for i in range(self.num_freq):
            self.freq_controll.append(BasicControllWidget(ch=i+1, val_type='freq'))
            
        self.phase_controll = []
        for i in range(self.num_phase):
            self.phase_controll.append(BasicControllWidget(ch=i+1, val_type='phase'))
            
        power_widget = QWidget()
        power_vbox = QVBoxLayout()
        power_widget.setLayout(power_vbox)
            
        freq_widget = QWidget()
        freq_vbox = QVBoxLayout()
        freq_widget.setLayout(freq_vbox)
        
        phase_widget = QWidget()
        phase_vbox = QVBoxLayout()
        phase_widget.setLayout(phase_vbox)
        
        scroll_area = [self.PWR_LIST, self.FREQ_LIST, self.PHASE_LIST]
        widget_list = [power_widget, freq_widget, phase_widget]
        for widget, scroll in zip(widget_list, scroll_area):
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidgetResizable(True)
            scroll.setWidget(widget)
        
        basic_size = BasicControllWidget().sizeHint()
        for p in self.power_controll:    
            power_vbox.addWidget(p)
        power_vbox.setContentsMargins(10,10,10,10)
        power_widget.setMinimumSize(basic_size.width()+20, 
                                    basic_size.height()*power_vbox.count()+50)
        
        for f in self.freq_controll:
            freq_vbox.addWidget(f)
        freq_widget.setMinimumSize(basic_size.width()+20, 
                                   basic_size.height()*freq_vbox.count()+50)

        for ph in self.phase_controll:
            phase_vbox.addWidget(ph)
        phase_widget.setMinimumSize(basic_size.width()+20, 
                                    basic_size.height()*phase_vbox.count()+50)
        
        BTN_STYLE = '''QPushButton{background-color:rgb(200,200,200);
        border-color:rgb(150,150,150);
        border-style:solid;
        border-width:1.5px;}
        QPushButton::pressed{background-color:rgb(100,100,100);}
        '''
        self.BTN_CONN.setStyleSheet(BTN_STYLE)
        self.BTN_DISCONN.setStyleSheet(BTN_STYLE)
        self.SET_PWR.setStyleSheet(BTN_STYLE)
        self.SET_FREQ.setStyleSheet(BTN_STYLE)
        self.SET_PHASE.setStyleSheet(BTN_STYLE)
        
    #     self.BTN_CONN.clicked.connect(self._btn_interaction)
    #     self.BTN_DISCONN.clicked.connect(self._btn_interaction)
    #     self.SET_PWR.clicked.connect(self._btn_interaction)
    #     self.SET_FREQ.clicked.connect(self._btn_interaction)
    #     self.SET_PHASE.clicked.connect(self._btn_interaction)
        
    # def _btn_interaction(self):
    #     btn = self.sender()
    #     print(btn.text())
        
    def sizeHint(self):
        return QSize(1240,350)
#%% MainController
class MainController(QtWidgets.QWidget, main_ui):
    
    # _gui_callback = pyqtSignal()
    # _update_signal = pyqtSignal()
    # _conn_signal = pyqtSignal(bool)
    
    def __init__(self, controller=None, ext_update=False):
        super(MainController, self).__init__()
        # main_ui.__init__(self)
        self.setupUi(self)
        self.controller = controller
        self.rf_dev_list = self.controller.dev_list
        # self.ext_update = ext_update
        # self.setWindowTitle("RF Controller")
        self.initUi()
        
        # self._gui_callback.connect(self._guiUpdate)
        # self.user_update = True
        
    def initUi(self):
        if not self.controller == None:   
            print('')
            self.global_widget = QWidget()
            self.global_vbox = QVBoxLayout()
            self.global_widget.setLayout(self.global_vbox)
            self.rf_controller_list = []
            for dev in self.rf_dev_list.keys():
                self.rf_controller_list.append(ControllWidget(dev=dev, 
                                                         num_power=self.rf_dev_list[dev]['num_power'],
                                                         num_freq=self.rf_dev_list[dev]['num_freq'],
                                                         num_phase=self.rf_dev_list[dev]['num_phase'])
                                               )

            scroll = self.DEV_AREA
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidgetResizable(True)
            scroll.setWidget(self.global_widget)
            
            for rf in self.rf_controller_list:
                self.global_vbox.addWidget(rf)
            basic_size = ControllWidget().sizeHint()
            self.global_vbox.setContentsMargins(10,10,10,10)
            self.global_widget.setMinimumSize(basic_size.width()+20, 
                                              basic_size.height()*self.global_vbox.count()+50)

        
    def toStatus(self, msg):
        self.LBL_status.setText(msg)

    def connectToServer(self, on_flag):
        if self.user_update:
            self._conn_signal.emit(on_flag)
        if on_flag:
            self.controller.openDevice()            
        else:
            self.controller.closeDevice()
            self.toStatus("Disconnected from the server.")
    
    def readConfig(self):
        config_file = self.TXT_config.text()
        self.controller.readConfig(config_file)
        
        self._initUi()
        
    def openConfig(self):
        config_file = QFileDialog.getOpenFileName(self, caption="Load a config file", directory=dirname, filter="*.conf")
        self.TXT_config.setText(config_file[0])
        self.readConfig()
                
    def powerOn(self, channel, value):
        board = self._getBoardIndex(self.sender())
        ch1, ch2 = self._getChannelFlags(channel)

        if value: # power up
            self.controller.powerUp(board, ch1, ch2) 
        else:
            self.controller.powerDown(board, ch1, ch2)
        
        
    def changeCurr(self, channel, current):
        board = self._getBoardIndex(self.sender())
        ch1, ch2 = self._getChannelFlags(channel)

        self.controller.setCurrent(board, ch1, ch2, current)
        
    def changeFreq(self, channel, freq_in_MHz):
        board = self._getBoardIndex(self.sender())
        ch1, ch2 = self._getChannelFlags(channel)
            
        self.controller.setFrequency(board, ch1, ch2, freq_in_MHz)
        
    def changePhase(self, channel, value):
        print("This function is not implemented yet.")
        
    def _guiUpdate(self):
        """
        When update GUI from external script....
        Not sure if it is a right approach.
        """
        if self.ext_update:
            self._update_signal.emit()
        else:
            self.updateUi()
            
    def updateUi(self):
        """
        current_settings =
        {1: {'current': [0, 0], 'freq_in_MHz': [0, 0], 'power': [0, 0]},
          2: {'current': [0, 0], 'freq_in_MHz': [0, 0], 'power': [0, 0]}}
        """
        current_settings = self.controller._current_settings
        
        for board_idx, board_settings in current_settings.items():
            self.dds_list[board_idx-1].user_update = False
            for setting, value_list in board_settings.items():
                if setting == "current":
                    for channel, value in enumerate(value_list):
                        spin_box = getattr(self.dds_list[board_idx-1], "Board1_DDS%d_power_spinbox" % (channel+1))
                        if not value == spin_box.value():
                            spin_box.setValue(value)
                            
                elif setting == "freq_in_MHz":
                    for channel, value in enumerate(value_list):
                        spin_box = getattr(self.dds_list[board_idx-1], "Board1_DDS%d_freq_spinbox" % (channel+1))
                        if not value == spin_box.value():
                            spin_box.setValue(value)
                            
                elif setting == "power":
                    for channel, value in enumerate(value_list):
                        push_button = getattr(self.dds_list[board_idx-1], "BTN_power_on_%d" % (channel+1))
                        if not value == push_button.isChecked():
                            push_button.setChecked(value)
                            
            self.dds_list[board_idx-1].user_update = True
                
        
if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    gui = MainController(controller = RF_ClientInterface())
    # gui = ControllWidget()
    # gui=BasicControllWidget()
    gui.show()
