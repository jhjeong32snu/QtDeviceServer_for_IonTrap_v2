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
from RF_client_controller import RF_ClientInterface

main_ui_file = dirname + "/ui_resources/RF_Main_widget_v2.ui"
controll_ui_file  = dirname + "/ui_resources/RF_device_widget_v2.ui"
basic_controll_ui_file  = dirname + "/ui_resources/Basic_controll_widget_v2.ui"
basic_power_controll_ui_file  = dirname + "/ui_resources/Basic_power_controll_widget_v2.ui"

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
            self.STEP.addItem('MHz')
            self.STEP.addItem('GHz')
            self.VAL.setDigitCount(14)
        if self.type == 'phase':
            self.STEP.addItem('degree')
            self.VAL.setDigitCount(6)
 
        self.SET_VAL.setDecimals(3)
        self.SLD.setMaximum(100)
        self.SLD.setValue(int(self.SLD.maximum()/2))
        self.VAL.setStyleSheet('background-color:rgb(255,255,255)')
        self.SLD.setStyleSheet('background-color:rgb(150,150,150);color: rgb(255,255,255);border-style: solid;border-width: 0px;')
        self.STEP.setStyleSheet('background-color:rgb(255,255,255);border-style: solid;border-width: 2px;border-color:rgb(200,200,200);')
        self.CH.setStyleSheet('background-color:rgb(200, 200, 200)')
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
        
        self.SET_VAL.setDecimals(2)
        self.VAL.setStyleSheet('background-color:rgb(255,255,255)')
        self.VAL_VPP.setStyleSheet('background-color:rgb(255,255,255)')
        # self.SLD.setStyleSheet('background-color:rgb(150,150,150);color: rgb(255,255,255);border-style: solid;border-width: 0px;')
        self.STEP.setStyleSheet('background-color:rgb(255,255,255);border-style: solid;border-width: 2px;border-color:rgb(200,200,200);')
        self.CH.setStyleSheet('background-color:rgb(200, 200, 200)')
        self.OUT_STATUS.setStyleSheet('background-color:rgb(0, 0, 0); color: rgb(255,0,0); border-width:0px')
        self.OUT_CHECK.setStyleSheet('border-width:0px')
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
        self.BTN_OUT.setStyleSheet(BTN_STYLE)
        
        self.BTN_CONN.clicked.connect(self._btn_conn)
        self.BTN_DISCONN.clicked.connect(self._btn_conn)
        self.SET_PWR.clicked.connect(self._btn_set)
        self.SET_FREQ.clicked.connect(self._btn_set)
        self.SET_PHASE.clicked.connect(self._btn_set)
        self.BTN_OUT.clicked.connect(self._btn_on)
        
        # for p in self.power_controll:
        #     p.SET_VAL.valueChanged.connect(self._link_sld_spin)
            # p.SLD.valueChanged.connect(self._link_sld_spin)
        
        # for p in self.freq_controll:
        #     p.SET_VAL.valueChanged.connect(self._link_sld_spin)
        #     p.SLD.valueChanged.connect(self._link_sld_spin)
            
        # for p in self.phase_controll:
        #     p.SET_VAL.valueChanged.connect(self._link_sld_spin)
        #     p.SLD.valueChanged.connect(self._link_sld_spin)
            
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
        self.parent._btn_on(btn=btn, dev=self.dev)
        
    # def _link_sld_spin(self):
    #     basic_widget = self.sender().parent().parent()
    #     if isinstance(self.sender(), QDoubleSpinBox):
    #         sender_type = 'spinbox'
    #         sender = self.sender()
    #         connector = basic_widget.SLD
    #     elif isinstance(self.sender(), QSlider):
    #         sender_type = 'slider'
    #         sender = self.sender()
    #         connector = basic_widget.SET_VAL
    #     self.parent._link_sld_spin(sender=sender, connector=connector, sender_type=sender_type, widget=basic_widget, dev=self.dev)
    
    def _freq_unit_changed(self):
        basic_widget = self.sender().parent().parent()
        combobox = self.sender()
        self.parent._freq_unit_changed(widget=basic_widget, cbox=combobox, dev=self.dev)
    
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
    _output_disable_signal = pyqtSignal(str, bool)
    _power_disable_signal = pyqtSignal(str, bool)
    _is_released_signal = pyqtSignal(str, bool)
    # _update_signal = pyqtSignal()
    # _conn_signal = pyqtSignal(bool)
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
            
    def disable_output_button(self, dev, btn_disable):
        if dev in self.rf_controller_list:
            if btn_disable == True:
                self.rf_controller_list[dev].BTN_OUT.setDisabled(btn_disable)
                self.rf_controller_list[dev].BTN_OUT.setStyleSheet(self.DIS_STYLE)
            if btn_disable == False:
                self.rf_controller_list[dev].BTN_OUT.setDisabled(btn_disable)
                self.rf_controller_list[dev].BTN_OUT.setStyleSheet(self.rf_controller_list[dev].BTN_STYLE)

    def disable_power_button(self, dev, btn_disable):
        if dev in self.rf_controller_list:
            if btn_disable == True:
                self.rf_controller_list[dev].SET_PWR.setDisabled(btn_disable)
                self.rf_controller_list[dev].SET_PWR.setStyleSheet(self.DIS_STYLE)
            if btn_disable == False:
                self.rf_controller_list[dev].SET_PWR.setDisabled(btn_disable)
                self.rf_controller_list[dev].SET_PWR.setStyleSheet(self.rf_controller_list[dev].BTN_STYLE)
        
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
        for key in self.rf_dev_list.keys():
            self.rf_dev_units[key] = {'power': [p.STEP.currentText() for p in self.rf_controller_list[key].power_controll],
                                      'freq': [p.STEP.currentText() for p in self.rf_controller_list[key].freq_controll],
                                      'phase': [p.STEP.currentText() for p in self.rf_controller_list[key].phase_controll]}
        
        for key in self.rf_dev_list.keys():
            min_power = self.rf_dev_list[key]['min_power']
            max_power = self.rf_dev_list[key]['max_power']
            min_freq = self.rf_dev_list[key]['min_freq']
            max_freq = self.rf_dev_list[key]['max_freq']
            freq_unit = self.rf_dev_units[key]['freq']
            min_phase = self.rf_dev_list[key]['min_phase']
            max_phase = self.rf_dev_list[key]['max_phase']
            power_controller = self.rf_controller_list[key].power_controll
            freq_controller = self.rf_controller_list[key].freq_controll
            phase_controller = self.rf_controller_list[key].phase_controll
            self.decimal = 2
            self.mhz_decimal = 3
            self.ghz_decimal = 7
            for i, p in enumerate(power_controller):
                p.SET_VAL.setDecimals(self.decimal)
                p.SET_VAL.setMaximum(max_power[i])
                p.SET_VAL.setMinimum(min_power[i])
                p.SET_VAL.setValue(p.SET_VAL.minimum())
                # p.SLD.setRange(0, int(10**self.decimal*(max_power[i]-min_power[i])))
                
            for i, f in enumerate(freq_controller):
                f.SET_VAL.setDecimals(self.mhz_decimal)
                min_f = self.check_freq_unit(min_freq[i], freq_unit[i])
                max_f = self.check_freq_unit(max_freq[i], freq_unit[i])
                f.SET_VAL.setMaximum(max_f)
                f.SET_VAL.setMinimum(min_f)
                f.SET_VAL.setValue(f.SET_VAL.minimum())
                # f.SLD.setRange(0, int((max_f-min_f)*10**self.mhz_decimal))
                f.SCAN_MODE.stateChanged.connect(self._scan_mode)
                
            for i, ph in enumerate(phase_controller):
                ph.SET_VAL.setDecimals(self.decimal)
                ph.SET_VAL.setMaximum(max_phase[i])
                ph.SET_VAL.setMinimum(min_phase[i])
                ph.SET_VAL.setValue(ph.SET_VAL.minimum())
                ph.SCAN_MODE.stateChanged.connect(self._scan_mode)
                # ph.SLD.setRange(0, int(10**self.decimal*(max_phase[i]-min_phase[i])))
        
        print('Init Ui Settings done')
    
    # def _link_sld_spin(self, sender, connector, sender_type, widget, dev):
    #     if widget in self.rf_controller_list[dev].freq_controll:
    #         idx = self.rf_controller_list[dev].freq_controll.index(widget)
    #         funit = self.rf_dev_units[dev]['freq'][idx]
    #         if funit == 'MHz':
    #             decimal = self.mhz_decimal
    #         elif funit == 'GHz':
    #             decimal = self.ghz_decimal
    #     else:
    #         decimal = self.decimal
        
    #     if sender_type == 'spinbox':
    #         sender_val = sender.value()
    #         if sender.minimum() <= 0:
    #             sender_val -= sender.minimum()
    #         connector.setValue(int(sender_val*10**decimal))
    #     elif sender_type == 'slider':
    #         sender_val = sender.value()
    #         if connector.minimum() <= 0:
    #             sender_val += connector.minimum() * 10**decimal
    #         connector.setValue(sender_val/10**decimal)
    
    def _freq_unit_changed(self, widget, cbox, dev):
        if widget in self.rf_controller_list[dev].freq_controll:
            idx = self.rf_controller_list[dev].freq_controll.index(widget)
            curr_unit = self.rf_dev_units[dev]['freq'][idx]
            curr_freq = widget.SET_VAL.value()
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
                if changed_unit == 'MHz':
                    decimal = 3
                    fcontroller.SET_VAL.setDecimals(decimal)
                    fcontroller.SET_VAL.setSingleStep(1)
                elif changed_unit == 'GHz':
                    decimal = 7
                    fcontroller.SET_VAL.setDecimals(decimal)
                    fcontroller.SET_VAL.setSingleStep(0.1)
                fcontroller.SET_VAL.setMaximum(new_max_f)
                fcontroller.SET_VAL.setMinimum(new_min_f)
                # fcontroller.SLD.setRange(0, int(10**decimal*(new_max_f-new_min_f)))
                
                fcontroller.SET_VAL.setValue(self.check_freq_unit(curr_freq, changed_unit))
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
        step = 0.01
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
                power.append(c.SET_VAL.value())
            self.controller.setPower(power, dev_name=dev)
        elif btn_type == 'FREQ':
            controller = self.rf_controller_list[dev].freq_controll
            funit = self.rf_dev_units[dev]['freq']
            unit_conversion = {'MHz':1e6, 'GHz':1e9}
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

    '''
    Should use Kwargs for device name(dev_name=~~) for controller function!
    The wapper with decorator in controller use the kwargs as index for finding connection state
    '''        
    @check_connection
    def _btn_on(self, btn, dev):
        controller_widget = self.rf_controller_list[dev]
        p_controller = controller_widget.power_controll
        is_out = [p.OUT_CHECK.isChecked() for p in p_controller]
        self.controller.enableOutput(is_out, dev_name=dev)
        
    def warningDisplay(self, msg, dev):
        self.rf_controller_list[dev].LBL_STATUS.setText(msg)
        self.rf_controller_list[dev].LBL_STATUS.setStyleSheet('background-color:rgb(0,0,0);color:rgb(255,0,0)')

    def check_freq_unit(self, freq, unit):
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