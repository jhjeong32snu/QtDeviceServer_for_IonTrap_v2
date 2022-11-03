import os, sys
filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

new_path_list = []
new_path_list.append(dirname + '/ui_resources') # For resources_rc.py
# More paths can be added here...
for each_path in new_path_list:
    if not (each_path in sys.path):
        sys.path.append(each_path)

# PyQt libraries
from PyQt5 import uic, QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QRect, pyqtSignal, QSize, Qt
from PyQt5.QtWidgets import *

main_ui_file = dirname + "/ui_resources/RF_GUI.ui"
controll_ui_file  = dirname + "/ui_resources/Controll_widget.ui"

main_ui, _ = uic.loadUiType(main_ui_file)
controll_ui,  _ = uic.loadUiType(controll_ui_file)

#%% SubWindow
class Controll_Widget(QtWidgets.QWidget, controll_ui):
    def __init__(self, ch:int=1):
        QtWidgets.QWidget.__init__(self)
        self.setupUi(self)
        self.LBL_CH.setText('CH ' + str(ch))
        self.LBL_CH2.setText('CH ' + str(ch+1))
        
    def sizeHint(self):
        return QSize(400,120)

class Controll_List(QtWidgets.QWidget):
    def __init__(self, region='power', num_element=1):
        super().__init__()
        self.region = region
        self.num_box = num_element // 2 + 1 
        self.initUI()

    def initUI(self):
        self.listWidget = QScrollArea(self)
        self.widget = QWidget()
        self.vbox = QVBoxLayout()
        for i in range(self.num_box):
            ch_idx = 2*i + 1
            ctl_widget = Controll_Widget(ch=ch_idx)
            self.vbox.addWidget(ctl_widget)

        self.widget.setLayout(self.vbox)
        self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.listWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.listWidget.setWidgetResizable(True)
        self.listWidget.setWidget(self.widget)

#%% MainWindow
class MainWindow(QtWidgets.QMainWindow, main_ui):
    
    # _gui_callback = pyqtSignal()
    # _update_signal = pyqtSignal()
    # _conn_signal = pyqtSignal(bool)
    
    
    def __init__(self, controller=None, ext_update=False):
        QtWidgets.QWidget.__init__(self)
        # main_ui.__init__(self)
        self.setupUi(self)
        # self.controller = controller
        # self.ext_update = ext_update
        # self.setWindowTitle("RF Controller")
        self._initUi()
        
        # self._gui_callback.connect(self._guiUpdate)
        # self.user_update = True
        
    def _initUi(self):
        self.PWR_BTN = QPushButton('Set \n Power', self)
        self.FREQ_BTN = QPushButton('Set \n Freq', self)
        self.PHASE_BTN = QPushButton('Set \n Phase', self)
        btn_style = 'background-color:rgb(200,200,200); border-color:rgb(150,150,150)'
        self.BTN_LIST = [self.PWR_BTN, self.FREQ_BTN, self.PHASE_BTN]
        self.PWR_CTL = Controll_List(region='power', num_element=1)
        self.FREQ_CTL = Controll_List(region='freq', num_element=1)
        self.PHASE_CTL = Controll_List(region='phase', num_element=1)
        self.CTL_LIST = [self.PWR_CTL, self.FREQ_CTL, self.PHASE_CTL]
        for i in range(self.CTL_TAB.count()):
            widget = self.CTL_TAB.widget(i)
            widget.HBOX = QHBoxLayout(widget)
            btn, ctl = self.BTN_LIST[i], self.CTL_LIST[i]
            ctl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setStyleSheet(btn_style)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            widget.HBOX.addWidget(ctl)
            widget.HBOX.addWidget(btn)
            widget.setLayout(widget.HBOX)
    #     self.PWR_LAYOUT.addWidget(self.PWR_CTL)
    #     self.PWR_LAYOUT.addWidget(self.PWR_BTN)
    #     self.FREQ_LAYOUT.addWidget(self.FREQ_CTL)
    #     self.FREQ_LAYOUT.addWidget(self.FREQ_BTN)
    #     self.PHASE_LAYOUT.addWidget(self.PHASE_CTL)
    #     self.PHASE_LAYOUT.addWidget(self.PHASE_BTN)
    #     self.POWER.setLayout(self.PWR_LAYOUT)
    #     self.FREQ.setLayout(self.FREQ_LAYOUT)
    #     self.PHASE.setLayout(self.PHASE_LAYOUT)
        # for i in range(self.CTL_TAB.count()):
        #     widget = self.CTL_TAB.widget(i)
                
        # for board_idx in range(self.controller._num_boards):
        #     sub_window = SubWindow(parent=self, board_idx=board_idx)
        #     self.dds_list.append(sub_window)
        # ## This must be done in the config
        # for idx, sub_dds in enumerate(self.dds_list):
        #     sub_dds.Board_wrapper.setTitle("%s chamber" % (self.controller._board_nickname[idx]))
        #     self.HFrameLayout.addWidget(sub_dds)


        # num_sub_widget = len(self.dds_list)
        # widget_geometry = QRect(self._widget_x,
        #                         self._widget_y,
        #                         self._widget_width*num_sub_widget + 10*(num_sub_widget-1),
        #                         self._widget_height)


        # self.HFrameLayout.setGeometry(widget_geometry)
        # self.setGeometry(50,
        #                   150,
        #                   self._widget_width*num_sub_widget + 10*(num_sub_widget-1) + 20,
        #                   self._widget_height + 20)
        
        # self.TXT_IP.setText("%s" % self.controller.sck.IP)
        # self.TXT_PORT.setText("%d" % self.controller.sck.PORT)
        # self.TXT_config.setText("%s" % self.controller.config_file)
        
        
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
    gui = MainWindow()
    gui.show()
