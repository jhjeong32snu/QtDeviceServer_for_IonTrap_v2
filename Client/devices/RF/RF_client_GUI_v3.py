# -*- coding: utf-8 -*-
"""
@author: KMLee
"""
import os, sys, time
import numpy as np
filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

new_path_list = []
new_path_list.append(dirname + '/ui_resources')
for each_path in new_path_list:
    if not (each_path in sys.path):
        sys.path.append(each_path)

from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import pyqtSignal, QSize, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QDoubleSpinBox, QSlider
from PyQt5.QtGui import QDoubleValidator
from RF_client_controller_v2 import RF_ClientInterface

main_ui_file = dirname + "/ui_resources/RF_Main_widget_v3.ui"
controll_ui_file  = dirname + "/ui_resources/RF_device_widget_v3.ui"
basic_controll_ui_file  = dirname + "/ui_resources/Basic_controll_widget_v3.ui"
basic_power_controll_ui_file  = dirname + "/ui_resources/Basic_power_controll_widget_v3.ui"

main_ui, _ = uic.loadUiType(main_ui_file)
controll_ui,  _ = uic.loadUiType(controll_ui_file)
basic_controll_ui,  _ = uic.loadUiType(basic_controll_ui_file)
basic_power_controll_ui,  _ = uic.loadUiType(basic_power_controll_ui_file)

#%% BasicControllWidget
class BasicControllWidget(QtWidgets.QWidget, basic_controll_ui):
    def __init__(self, ch=1, val_type='freq'):
        super(BasicControllWidget, self).__init__()
        self.setupUi(self)
        self.ch, self.type = ch, val_type
        self.initUi()
    def initUi(self):
        if isinstance(self.ch, str):
            self.CH.setText(self.ch)
        else:
            self.CH.setText('CH ' + str(self.ch))
            
        if self.type == 'freq':
            self.STEP.addItem('KHz')
            self.STEP.addItem('MHz')
            self.STEP.addItem('GHz')
            self.VAL.setDigitCount(14)
            self.SET_VAL.setDecimals(1)
            self.STEP.setCurrentIndex(1)
        if self.type == 'phase':
            self.STEP.addItem('degree')
            self.VAL.setDigitCount(6)
            self.SET_VAL.setDecimals(1)
        
        self.SCAN_STEP.setValue(0.01)
        self.SCAN_STEP.setSingleStep(0.005)
        self.SCAN_STEP.setDecimals(3)
        self.SLD.setMaximum(9)
        self.SLD.setValue(int(self.SLD.maximum()/2+1))
        self.VAL.setStyleSheet('color:rgb(0,0,0);background-color:rgb(255,255,255)')
        self.SLD.setStyleSheet('color:rgb(0,0,0);background-color:rgb(150,150,150);color: rgb(255,255,255);border-style: solid;border-width: 0px;')
        self.STEP.setStyleSheet('color:rgb(0,0,0);background-color:rgb(255,255,255);border-style: solid;border-width: 2px;border-color:rgb(200,200,200);')
        self.CH.setStyleSheet('color:rgb(0,0,0);background-color:rgb(200, 200, 200)')
        self.SCAN_MODE.setStyleSheet('border-width:0px')
        self._curr_val = self.SLD.value()
        self._set_val = self.SET_VAL.value()
            
    def sizeHint(self):
        return QSize(330,130)

class BasicPowerControllWidget(QtWidgets.QWidget, basic_power_controll_ui):
    def __init__(self, ch=1, val_type='power'):
        super(BasicPowerControllWidget, self).__init__()
        self.setupUi(self)
        self.ch, self.type = ch, val_type
        self.initUi()
    def initUi(self):
        if isinstance(self.ch, str):
            self.CH.setText(self.ch)
        else:
            self.CH.setText('CH ' + str(self.ch))
            
        if self.type == 'power':
            self.STEP.addItem('dBm')
            self.VAL.setDigitCount(6)
            self.VAL_VPP.setDigitCount(7)
            self.STEP.addItem('Vpp')
        
        self.SET_VAL.setDecimals(2)
        self.SET_VAL.setSingleStep(0.1)
        self.VAL.setStyleSheet('color:rgb(0,0,0);background-color:rgb(255,255,255)')
        self.VAL_VPP.setStyleSheet('color:rgb(0,0,0);background-color:rgb(255,255,255)')
        # self.SLD.setStyleSheet('background-color:rgb(150,150,150);color: rgb(255,255,255);border-style: solid;border-width: 0px;')
        self.STEP.setStyleSheet('color:rgb(0,0,0);background-color:rgb(255,255,255);border-style: solid;border-width: 2px;border-color:rgb(200,200,200);')
        self.CH.setStyleSheet('color:rgb(0,0,0);background-color:rgb(200, 200, 200)')
        self.OUT_STATUS.setStyleSheet('color:rgb(0,0,0);background-color:rgb(0, 0, 0); color: rgb(255,0,0); border-width:0px')
        self.OUT_BTN.setStyleSheet('color: white;background-color: rgb(100, 100, 100);boder-radius: 0px;boder-width: 0px')
        
    def sizeHint(self):
        return QSize(400,130)
    
#%% ControllWidget
class ControllWidget(QtWidgets.QWidget, controll_ui):
    def __init__(self, dev=None, num_power=1, num_freq=1, num_phase=1, synth_type='Synth', ch_names = None, parent=None):
        super(ControllWidget, self).__init__()
        self.setupUi(self)
        self.num_power, self.num_freq, self.num_phase = num_power, num_freq, num_phase
        self.synth_type = synth_type
        self.dev = dev
        self.parent = parent
        if ch_names == None:
            self.ch_names = ['CH {}'.format(i) for i in range(self.num_power)]
        else:
            self.ch_names = ch_names
        if dev == None:
            self.LBL_DEV.setText('None')
        else:
            self.LBL_DEV.setText(dev)
        self.initUI()

    def initUI(self):
        self.LBL_SYN.setText(self.synth_type)
        
        self.power_controll = []

        for i in range(self.num_power):
            self.power_controll.append(BasicPowerControllWidget(ch=self.ch_names[i], val_type='power'))
                
        self.freq_controll = []
        if self.num_freq == len(self.ch_names):
            for i in range(self.num_freq):
                self.freq_controll.append(BasicControllWidget(ch=self.ch_names[i], val_type='freq'))
        else:
            for i in range(self.num_freq):
                self.freq_controll.append(BasicControllWidget(ch='COMMON', val_type='freq'))
        
        self.phase_controll = []
        if self.num_phase == len(self.ch_names):
            for i in range(self.num_phase):
                self.phase_controll.append(BasicControllWidget(ch=self.ch_names[i], val_type='phase'))
        else:
            for i in range(self.num_phase):
                self.phase_controll.append(BasicControllWidget(ch='CONMON', val_type='phase'))
            
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
        border-width:1.5px;
        color:rgb(0,0,0);}
        QPushButton::pressed{background-color:rgb(100,100,100);}
        '''
        self.BTN_STYLE = BTN_STYLE
        self.BTN_CONN.setStyleSheet(BTN_STYLE)
        self.BTN_DISCONN.setStyleSheet(BTN_STYLE)
        self.SET_PWR.setStyleSheet(BTN_STYLE)
        self.SET_FREQ.setStyleSheet(BTN_STYLE)
        self.SET_PHASE.setStyleSheet(BTN_STYLE)
        self.BTN_REL.setStyleSheet(BTN_STYLE)
        
        self.BTN_CONN.clicked.connect(self._btn_conn)
        self.BTN_DISCONN.clicked.connect(self._btn_conn)
        self.SET_PWR.clicked.connect(self._btn_set)
        self.SET_FREQ.clicked.connect(self._btn_set)
        self.SET_PHASE.clicked.connect(self._btn_set)
        self.BTN_REL.clicked.connect(self._btn_release)
        
        for p in self.power_controll:
            p.STEP.currentIndexChanged.connect(self._power_unit_changed)
            p.OUT_BTN.clicked.connect(self._btn_on)
            
        for c in self.freq_controll:
            c.STEP.currentIndexChanged.connect(self._freq_unit_changed)
            
    def _btn_conn(self):
        btn = self.sender()
        dev_widget = self.sender().parent().parent()
        if btn.text() == 'Connect':
            CON = True
        elif btn.text() == 'Disconnect':
            CON = False
        self.parent._btn_conn(btn=btn, controll_widget=dev_widget, dev=self.dev, CON=CON)
        
    def _btn_set(self):
        btn = self.sender() # Either SET_PWR or SET_PHASE or SET_FREQ
        text = btn.objectName()[4:]
        self.parent._btn_set(btn_type=text, dev=self.dev)
        
    def _btn_on(self):
        btn = self.sender()
        basic_power_widget = self.sender().parent().parent()
        index = self.power_controll.index(basic_power_widget)
        self.parent._btn_on(btn=btn, dev=self.dev, idx = index)
        
    def _btn_release(self):
        self.parent.enable_output_button(dev=self.dev)
       
    def _freq_unit_changed(self):
        basic_widget = self.sender().parent().parent()
        combobox = self.sender()
        self.parent._freq_unit_changed(widget=basic_widget, cbox=combobox, dev=self.dev)
    
    def _power_unit_changed(self):
        basic_widget = self.sender().parent().parent()
        combobox = self.sender()
        self.parent._power_unit_changed(widget=basic_widget, cbox=combobox, dev=self.dev)
        
    def sizeHint(self):
        return QSize(1240,350)

#%% MainController

def check_connection(func):
    def wrapper(self, *args, **kwargs):
        if self.controller._is_opened[kwargs['dev']]:
            return func(self, *args, **kwargs)
        else:
            msg = 'Called without Connection'
            self.warningDisplay(msg=msg, dev=kwargs['dev'])
    return wrapper

class MainController(QtWidgets.QWidget, main_ui):
    
    _gui_callback = pyqtSignal()
    _init_signal = pyqtSignal()
    _output_disable_signal = pyqtSignal(str, bool, int)
    _power_disable_signal = pyqtSignal(str, bool)
    _is_released_signal = pyqtSignal(str, bool)
    _is_opened_signal = pyqtSignal(str, bool)
    
    DIS_STYLE = '''QPushButton{background-color:rgb(50,50,50);
                border-color:rgb(150,150,150);
                border-style:solid;
                border-width:1.5px;
                color:rgb(255,255,255);}
                '''
    
    '''
    rf_dev_list: holds rf settings for each devices
    rf_controller_list: holds each rf controller widget for each device
    Both are indexed with device name (935SB, EA_TRAP, ...)
    '''
    
    def showEvent(self, event):
        if not self.controller._init_flag == True:
            self.controller.initRF()
        else:
            self._refresh()
        
    def __init__(self, controller=None, ext_update=False):
        super(MainController, self).__init__()
        main_ui.__init__(self)
        self.setupUi(self)
        self.controller = controller
        self.setWindowTitle("RF Controller")
        self._init_flag = False
        self._gui_callback.connect(self._updateGui)
        self._init_signal.connect(self.safeRFconnection)
        self._output_disable_signal.connect(self.disable_output_button)
        self._power_disable_signal.connect(self.disable_power_button)
        self._is_released_signal.connect(self.display_released_state)
        self._is_opened_signal.connect(self.read_dev_values)
        
    def read_dev_values(self, dev, is_opened):
        controller = self.rf_controller_list[dev]
        if is_opened == True:
            for p in controller.power_controll:
                if p.STEP.currentText() == 'dBm':
                    p.SET_VAL.setValue(p.VAL.value())
                elif p.STEP.currentText() == 'Vpp':
                    p.SET_VAL.setValue(p.VAL_VPP.value())
            for f in controller.freq_controll:
                f.SET_VAL.setValue(f.VAL.value())
            for ph in controller.phase_controll:
                ph.SET_VAL.setValue(ph.VAL.value())
    
    def display_released_state(self, dev, is_released):
        print(dev, is_released)
        if is_released:
            style = 'background-color: rgb(0,0,0); color:rgb(255,0,0); border-width:0px;'
            self.rf_controller_list[dev].LBL_RELEASE.setText('Device Released')
            self.rf_controller_list[dev].LBL_RELEASE.setStyleSheet(style)
        else:
            style = 'background-color: rgb(255,255,255); color:rgb(0,0,0); border-width:0px;'
            self.rf_controller_list[dev].LBL_RELEASE.setText('')
            self.rf_controller_list[dev].LBL_RELEASE.setStyleSheet(style)
            
    def disable_output_button(self, dev, btn_disable, idx):
        if dev in self.rf_controller_list:
            BTN = self.rf_controller_list[dev].power_controll[idx].OUT_BTN
            if btn_disable == True:
                BTN.setDisabled(btn_disable)
                BTN.setStyleSheet(self.DIS_STYLE)
            if btn_disable == False:
                BTN.setDisabled(btn_disable)
                BTN.setStyleSheet(self.rf_controller_list[dev].BTN_STYLE)

    def disable_power_button(self, dev, btn_disable):
        if dev in self.rf_controller_list:
            if btn_disable == True:
                self.rf_controller_list[dev].SET_PWR.setDisabled(btn_disable)
                self.rf_controller_list[dev].SET_PWR.setStyleSheet(self.DIS_STYLE)
            if btn_disable == False:
                self.rf_controller_list[dev].SET_PWR.setDisabled(btn_disable)
                self.rf_controller_list[dev].SET_PWR.setStyleSheet(self.rf_controller_list[dev].BTN_STYLE)
        
    def enable_output_button(self, dev):
        if dev in self.rf_controller_list:
            for p in self.rf_controller_list[dev].power_controll:
                p.OUT_BTN.setDisabled(False)
                p.OUT_BTN.setStyleSheet(self.rf_controller_list[dev].BTN_STYLE)
            self.rf_controller_list[dev].SET_PWR.setDisabled(False)
            self.rf_controller_list[dev].SET_PWR.setStyleSheet(self.rf_controller_list[dev].BTN_STYLE)
        self._updateGui()
        
    def safeRFconnection(self):
        self.rf_dev_list = self.controller.dev_list
        self.initUi()
    
    def initUi(self):
        if not self.controller == None:   
            print('Init UI')
            self.rf_controller_list = {}
            for dev in self.rf_dev_list.keys():
                self.rf_controller_list[dev] = ControllWidget(dev=dev, 
                                                              num_power=self.rf_dev_list[dev]['num_power'],
                                                              num_freq=self.rf_dev_list[dev]['num_freq'],
                                                              num_phase=self.rf_dev_list[dev]['num_phase'],
                                                              synth_type=self.rf_dev_list[dev]['type'],
                                                              ch_names=self.rf_dev_list[dev]['chan'],
                                                              parent=self)
            print(self.rf_controller_list)
            DEV_TAB = self.DEV_AREA
            time.sleep(0.5)
            for dev_name, rf_widget in self.rf_controller_list.items():
                DEV_TAB.addTab(rf_widget, dev_name)
            print('Init UI done')
            self.initUiSettings()
            self._updateGui()
    
    def initUiSettings(self):
        print('Init Ui Settings')
        self.rf_dev_units = {}
        self._gui_output_status = {}
        for key in self.rf_dev_list.keys():
            self.rf_dev_units[key] = {'power': [p.STEP.currentText() for p in self.rf_controller_list[key].power_controll],
                                      'freq': [p.STEP.currentText() for p in self.rf_controller_list[key].freq_controll],
                                      'phase': [p.STEP.currentText() for p in self.rf_controller_list[key].phase_controll]}
            self._gui_output_status[key] = self.controller._rf_settings[key]['on'].copy()
            
        for key in self.rf_dev_list.keys():
            min_power = self.rf_dev_list[key]['min_power']
            max_power = self.rf_dev_list[key]['max_power']
            power_unit = self.rf_dev_units[key]['power']
            min_freq = self.rf_dev_list[key]['min_freq']
            max_freq = self.rf_dev_list[key]['max_freq']
            freq_unit = self.rf_dev_units[key]['freq']
            min_phase = self.rf_dev_list[key]['min_phase']
            max_phase = self.rf_dev_list[key]['max_phase']
            power_controller = self.rf_controller_list[key].power_controll
            freq_controller = self.rf_controller_list[key].freq_controll
            phase_controller = self.rf_controller_list[key].phase_controll
            self.dbm_decimal = 2
            self.vpp_decimal = 4
            self.ph_decimal = 0
            self.khz_decimal = 3
            self.mhz_decimal = 4
            self.ghz_decimal = 8
            for i, p in enumerate(power_controller):
                if power_unit[i] == 'dBm':
                    p.SET_VAL.setDecimals(self.dbm_decimal)
                if power_unit[i] == 'Vpp':
                    p.SET_VAL.setDecimals(self.vpp_decimal)
                p.SET_VAL.setMaximum(max_power[i])
                p.SET_VAL.setMinimum(min_power[i])
                p.SET_VAL.setValue(p.SET_VAL.minimum())
                
            for i, f in enumerate(freq_controller):
                if freq_unit[i] == 'KHz':
                    f.SET_VAL.setDecimals(self.khz_decimal)
                if freq_unit[i] == 'MHz':
                    f.SET_VAL.setDecimals(self.mhz_decimal)
                if freq_unit[i] == 'GHz':
                    f.SET_VAL.setDecimals(self.ghz_decimal)
                min_f = self.check_freq_unit(min_freq[i], freq_unit[i])
                max_f = self.check_freq_unit(max_freq[i], freq_unit[i])
                f.SET_VAL.setMaximum(max_f)
                f.SET_VAL.setMinimum(min_f)
                f.SET_VAL.setValue(f.SET_VAL.minimum())
                f.SCAN_MODE.stateChanged.connect(self._scan_mode)
                
            for i, ph in enumerate(phase_controller):
                ph.SET_VAL.setDecimals(self.ph_decimal)
                ph.SET_VAL.setMaximum(max_phase[i])
                ph.SET_VAL.setMinimum(min_phase[i])
                ph.SET_VAL.setValue(ph.SET_VAL.minimum())
                ph.SCAN_MODE.stateChanged.connect(self._scan_mode)
        
        print('Init Ui Settings done')
    
    
    def _freq_unit_changed(self, widget, cbox, dev):
        if widget in self.rf_controller_list[dev].freq_controll:
            idx = self.rf_controller_list[dev].freq_controll.index(widget)
            curr_unit = self.rf_dev_units[dev]['freq'][idx]
            curr_freq = widget.SET_VAL.value()
            if curr_unit == 'KHz':
                curr_freq *= 1e3
            if curr_unit == 'MHz':
                curr_freq *= 1e6
            elif curr_unit == 'GHz':
                curr_freq *= 1e9

            min_freq = self.rf_dev_list[dev]['min_freq'][idx]
            max_freq = self.rf_dev_list[dev]['max_freq'][idx]   
            fcontroller = self.rf_controller_list[dev].freq_controll[idx]
            changed_unit = cbox.currentText()
            if curr_unit != changed_unit:                
                self.rf_dev_units[dev]['freq'][idx] = changed_unit
                new_min_f = self.check_freq_unit(min_freq, changed_unit)
                new_max_f = self.check_freq_unit(max_freq, changed_unit)
                if changed_unit == 'KHz':
                    decimal = self.khz_decimal
                    fcontroller.SET_VAL.setDecimals(decimal)
                    fcontroller.SET_VAL.setSingleStep(1)
                if changed_unit == 'MHz':
                    decimal = self.mhz_decimal
                    fcontroller.SET_VAL.setDecimals(decimal)
                    fcontroller.SET_VAL.setSingleStep(0.001)
                elif changed_unit == 'GHz':
                    decimal = self.ghz_decimal
                    fcontroller.SET_VAL.setDecimals(decimal)
                    fcontroller.SET_VAL.setSingleStep(0.000001)
                fcontroller.SET_VAL.setMaximum(new_max_f)
                fcontroller.SET_VAL.setMinimum(new_min_f)
                
                fcontroller.SET_VAL.setValue(self.check_freq_unit(curr_freq, changed_unit))
        self._updateGui()

    def _power_unit_changed(self, widget, cbox, dev):
        if widget in self.rf_controller_list[dev].power_controll:
            idx = self.rf_controller_list[dev].power_controll.index(widget)
            curr_power = widget.SET_VAL.value()
            curr_unit = self.rf_dev_units[dev]['power'][idx]
            
            min_power = self.rf_dev_list[dev]['min_power'][idx]
            max_power = self.rf_dev_list[dev]['max_power'][idx]   
            pcontroller = self.rf_controller_list[dev].power_controll[idx]
            changed_unit = cbox.currentText()
            if curr_unit != changed_unit:
                self.rf_dev_units[dev]['power'][idx] = changed_unit
                if changed_unit == 'Vpp':
                    pcontroller.SET_VAL.setDecimals(self.vpp_decimal)
                    pcontroller.SET_VAL.setSingleStep(0.1)
                    new_min_p = self.convert_dbm_to_vpp(min_power)
                    new_max_p = self.convert_dbm_to_vpp(max_power)
                    setval = self.convert_dbm_to_vpp(curr_power)
                
                elif changed_unit == 'dbm':
                    pcontroller.SET_VAL.setDecimals(self.dbm_decimal)
                    pcontroller.SET_VAL.setSingleStep(0.1)
                    new_min_p = self.convert_vpp_to_dbm(min_power)
                    new_max_p = self.convert_vpp_to_dbm(max_power)
                    setval = self.convert_vpp_to_dbm(curr_power)
                    
                pcontroller.SET_VAL.setMaximum(new_max_p)
                pcontroller.SET_VAL.setMinimum(new_min_p)
                pcontroller.SET_VAL.setValue(setval)
        self._updateGui()

    def _scan_mode(self):
        scan_mode = self.sender().isChecked()
        basic_controller_widget = self.sender().parent().parent()
        sld = basic_controller_widget.SLD
        if scan_mode:
            sld.setValue(int(sld.maximum()/2))
            sld.valueChanged.connect(self._scanning)
        else:
            sld.valueChanged.disconnect()
            sld.setValue(int(sld.maximum()/2))
    
    def _scanning(self, changed_val):
        # slider = self.sender()
        basic_controller_widget = self.sender().parent().parent()
        controll_widget = basic_controller_widget.parent().parent().parent().parent().parent()
        
        curr_val = basic_controller_widget._curr_val
        changing = changed_val - curr_val
        step = basic_controller_widget.SCAN_STEP.value()
        curr_set_val = basic_controller_widget.SET_VAL.value()
        basic_controller_widget.SET_VAL.setValue(curr_set_val + step * changing)
        basic_controller_widget._curr_val = changed_val
        TYPE = basic_controller_widget.type
        DEV = controll_widget.dev
        if TYPE == 'freq':
            self.rf_controller_list[DEV].SET_FREQ.click()
        if TYPE == 'phase':
            self.rf_controller_list[DEV].SET_PHASE.click()
            
    '''
    Should use Kwargs for device name(dev_name=~~) for controller function!
    The wapper with decorator in controller use the kwargs as index for finding connection state
    '''        
    def _btn_conn(self, btn, controll_widget, dev, CON):
        if CON == True:
            self.controller.openDevice(dev_name=dev)
        elif CON == False:
            self.controller.closeDevice(dev_name=dev)

    '''
    Should use Kwargs for device name(dev_name=~~) for controller function!
    The wapper with decorator in controller use the kwargs as index for finding connection state
    '''        
    @check_connection
    def _btn_set(self, btn_type, dev):
        if btn_type == 'PWR':
            controller = self.rf_controller_list[dev].power_controll
            power = []
            for c in controller:
                pval = c.SET_VAL.value()
                punit = c.STEP.currentText()
                if punit == 'dBm':
                    power.append(pval)
                elif punit == 'Vpp':
                    power.append(self.convert_vpp_to_dbm(pval))
            self.controller.setPower(power, dev_name=dev)
            
        elif btn_type == 'FREQ':
            controller = self.rf_controller_list[dev].freq_controll
            funit = self.rf_dev_units[dev]['freq']
            unit_conversion = {'KHz':1e3, 'MHz':1e6, 'GHz':1e9}
            freq = []
            for c, unit in zip(controller, funit):
                freq.append(c.SET_VAL.value() * unit_conversion[unit])
            self.controller.setFrequency(freq, dev_name=dev)
        elif btn_type == 'PHASE':
            controller = self.rf_controller_list[dev].phase_controll
            phase = []
            for c in controller:
                phase.append(c.SET_VAL.value())
            self.controller.setPhase(phase, dev_name=dev)

    # '''
    # Should use Kwargs for device name(dev_name=~~) for controller function!
    # The wapper with decorator in controller use the kwargs as index for finding connection state
    # '''        
    # @check_connection
    @check_connection
    def _btn_on(self, btn, dev, idx):
        # curr_out = self.controller._rf_settings[dev]['on'].copy()
        curr_out = self._gui_output_status[dev]
        if curr_out[idx] == True:
            curr_out[idx] = False
        elif curr_out[idx] == False:
            curr_out[idx] = True
        self.controller.enableOutput(curr_out, dev_name=dev)
        
    def warningDisplay(self, msg, dev):
        self.rf_controller_list[dev].LBL_STATUS.setText(msg)
        self.rf_controller_list[dev].LBL_STATUS.setStyleSheet('background-color:rgb(0,0,0);color:rgb(255,0,0)')

    def check_freq_unit(self, freq, unit):
        if unit == 'KHz':
            return freq / 1e3
        if unit == 'MHz':
            return freq / 1e6
        elif unit == 'GHz':
            return freq / 1e9
        
    def convert_dbm_to_vpp(self, dbm):
        mw = 10**(dbm/10)
        resistance = 50
        vrms = np.sqrt(mw*resistance/10**3)
        Vpp = 2 * np.sqrt(2) * vrms
        return round(Vpp, 4)
    
    def convert_vpp_to_dbm(self, vpp):
        resistance = 50
        vrms = vpp / (2 * np.sqrt(2))
        mw = vrms**2 * 10**3 / resistance
        dbm = np.log10(mw) * 10
        return round(dbm, 2)
    
    def _updateGui(self):
        '''
        Update LCD Display & Status based on controller's RF_settings
        Rf_settings of Contoller will update only LCD Display & Conncetion status & Output Status of GUI
        '''
        rf_settings = self.controller._rf_settings
        con_settings = self.controller._is_opened
        # Settings LCD Display
        for key in rf_settings.keys():
            power_controller = self.rf_controller_list[key].power_controll
            freq_controller = self.rf_controller_list[key].freq_controll
            phase_controller = self.rf_controller_list[key].phase_controll
            for i, c in enumerate(power_controller):
                pval = rf_settings[key]['power'][i]
                c.VAL.display('{}'.format(pval))
                c.VAL_VPP.display('{}'.format(self.convert_dbm_to_vpp(pval)))
            for i, c in enumerate(freq_controller):
                funit = self.rf_dev_units[key]['freq'][i]
                fval = self.check_freq_unit(rf_settings[key]['freq'][i], funit)
                c.VAL.display('{}'.format(fval))
            for i, c in enumerate(phase_controller):
                c.VAL.display('{}'.format(rf_settings[key]['phase'][i]))
        
        # Setting Connection Status
        for key in self.rf_controller_list:
            if con_settings[key] == True:
                self.rf_controller_list[key].LBL_STATUS.setText('Connected')
                self.rf_controller_list[key].LBL_STATUS.setStyleSheet('background-color: rgb(0,0,0); color:rgb(0,255,0);')
            elif con_settings[key] == False:
                self.rf_controller_list[key].LBL_STATUS.setText('Disconnected')
                self.rf_controller_list[key].LBL_STATUS.setStyleSheet('background-color: rgb(255,255,255); color:rgb(0,0,0);')
            
        # Setting Output Status
        on_style = 'background-color: rgb(0,0,0); color:rgb(0,255,0); border-width:0px;'
        off_style = 'background-color: rgb(0,0,0); color:rgb(255,0,0); border-width:0px;'
        for key in self.rf_controller_list:
            for idx, on_status in enumerate(rf_settings[key]['on']):
                if on_status == True:
                    self.rf_controller_list[key].power_controll[idx].OUT_STATUS.setText('ON')
                    self.rf_controller_list[key].power_controll[idx].OUT_STATUS.setStyleSheet(on_style)
                elif on_status == False:
                    self.rf_controller_list[key].power_controll[idx].OUT_STATUS.setText('OFF')
                    self.rf_controller_list[key].power_controll[idx].OUT_STATUS.setStyleSheet(off_style)
            # if rf_settings[key]['on'][0] == True:
            #     self.rf_controller_list[key].LBL_OUT.setText('ON')
            #     self.rf_controller_list[key].LBL_OUT.setStyleSheet('background-color: rgb(0,0,0); color:rgb(0,255,0);')
            # elif rf_settings[key]['on'][0] == False:
            #     self.rf_controller_list[key].LBL_OUT.setText('OFF')
            #     self.rf_controller_list[key].LBL_OUT.setStyleSheet('background-color: rgb(255,255,255); color:rgb(0,0,0);')
        
    def _refresh(self):
        if hasattr(self, 'rf_controller_list'):
            for key in self.rf_controller_list:
                if self.controller._is_opened[key]:
                    self.controller.getFrequency(dev_name=key)
                    self.controller.getPower(dev_name=key)
                    self.controller.getOutput(dev_name=key)
                    self.controller.getPhase(dev_name=key)
        print('RF Refreshed')
    
    def _invalid_chan_num(self):
        raise Exception('Number of Channel not matched with data')
        
if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    gui = MainController(controller = RF_ClientInterface())
    # gui = ControllWidget()
    # gui=BasicControllWidget()
    gui.show()
    # app.exec_()