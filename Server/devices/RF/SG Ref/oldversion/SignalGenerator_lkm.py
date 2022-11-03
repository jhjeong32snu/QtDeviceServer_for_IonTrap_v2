# -*- coding: utf-8 -*-
"""
Created on Mon Feb 1 2021

@author: Modified by Kyungmin Lee (Original Work by Taehyun Kim)

* Change log
v1_00: Initial working version (Taehyun Kim)
v1_01: Optimized assuming that SG384Control panel will be called by another program (Taehyun Kim)

"""
# from http://wiki.python.org/moin/TcpCommunication
# About SCPI over TCP: page 12 from ftp://ftp.datx.com/Public/DataAcq/MeasurementInstruments/Manuals/SCPI_Measurement.pdf

from __future__ import unicode_literals  # supports python2 codes
import shutil
from configparser import ConfigParser
import time
import socket
import math
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import uic
from SCPI_Commands import *  # SCPI commands for the signal generators
import ImportForSpyderAndQt5
import os
import sys

osc_dir_path = "Q://Experiment_Scripts/Chamber_1S_SNU/RIGOL_DS1052E/"
sys.path.append(osc_dir_path)
from RIGOL_DS1052E_gui_v0_03 import DS1052E_GUI

filename = os.path.abspath(__file__)  # absolute path of the file
dirname = os.path.dirname(filename)  # directory of the file

new_path_list = []
new_path_list.append(dirname + '/..')  # For ImportForSpyderAndQt5
new_path_list.append(dirname + '/../ui_resources')  # For resources_rc.py
# More paths can be added here...
for each_path in new_path_list:
    if not (each_path in sys.path):
        # appends new directories to sys.path to import files/libraries
        sys.path.append(each_path)


qt_designer_file = dirname + '/signal_generator_widget_lkm.ui'
# Ui_QWidget: class constructed according to the ui file
Ui_QWidget, QtBaseClass = uic.loadUiType(qt_designer_file)

ICON_RED_LED = ":/icons/red-led-on.png"
ICON_GREEN_LED = ":/icons/green-led-on.png"
CONFIG_DIR = "/../config"
CONFIG_PATH = CONFIG_DIR

NEG_INF_DBM = -100
POWER_STEP_SIZE = 0.01
STEP_SLEEP_TIME = 0.2

new_path_list = []
new_path_list.append(dirname + '/..')  # For ImportForSpyderAndQt5
new_path_list.append(dirname + '/../ui_resources')  # For resources_rc.py
# More paths can be added here...
for each_path in new_path_list:
    if not (each_path in sys.path):
        # appends new directories to sys.path to import files/libraries
        sys.path.append(each_path)

class PowerThread(QtCore.QThread):
    def __init__(self, sg, curr_dBm, target_Vpp, output_type, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.sg = sg
        curr_mW = 10**(curr_dBm/10)
        self.curr_Vpp = math.sqrt(curr_mW/10)*2
        self.target_Vpp = target_Vpp
        self.output_type = output_type

    def run(self):
        command = POWER_DBM_Q[self.output_type][self.sg.device_type]
        Vpp = self.curr_Vpp
        step_num = int((self.target_Vpp - Vpp)*100)
        if step_num < 0:
            global POWER_STEP_SIZE
            POWER_STEP_SIZE = -1*POWER_STEP_SIZE
            step_num = -1*step_num

        for i in range(step_num):
            Vpp += (self.target_Vpp - self.curr_Vpp)/step_num
            if Vpp > 0.19:
                Vpp = 0.19
            Vamp = Vpp/2
            mW = 10*Vamp**2
            dBm = math.trunc(100*(10*math.log10(mW)))/100
            message = "%s %.2f" % (command, dBm)
            self.sg.socket.send((message + '\n').encode('latin-1'))
            #self.socket.send((command + '?' + '\n').encode('latin-1'))
            #data = self.socket.recv(1024)
            time.sleep(STEP_SLEEP_TIME)

        Vamp = self.target_Vpp/2
        mW = 10*Vamp**2
        if mW > 0:
            dBm = math.trunc(100*(10*math.log10(mW)))/100
        else:
            dBm = NEG_INF_DBM
        message = "%s %.2f" % (command, dBm)
        self.sg.socket.send((message + '\n').encode('latin-1'))

        for widget in self.sg.disabled_widgets:
            widget.setEnabled(True)


class SignalGenerator(QtWidgets.QWidget, Ui_QWidget):

    # device_type (int): 0 = SG384, 1 = APSYN420
    # device_index (int): index of each signal generator on MainWindow
    def __init__(self, device_index, parent=None, connection_callback=None):
        QtWidgets.QWidget.__init__(self, parent)  # or super().__init__(parent)

        self.setupUi(self)  # display ui

        self.device_index = device_index  # to access the appropriate config section

        self.dBm_spinboxes = [self.dBm_spinbox, self.dBm_BNC_spinbox]
        self.Vpp_spinboxes = [self.Vpp_spinbox, self.Vpp_BNC_spinbox]
        self.mW_spinboxes = [self.mW_spinbox, self.mW_BNC_spinbox]
        self.output_statuses = [self.output_TypeN_status, self.output_BNC_status]
        self.output_buttons = [self.output_TypeN_button, self.output_BNC_button]
        self.output_on = [False, False]

        # overrides stepBy() of the spinbox with new_Vpp_stepBy()
        # stepBy(): called whenever the user triggers a step
        self.old_Vpp_stepBy = self.Vpp_spinbox.stepBy
        self.old_Vpp_BNC_stepBy = self.Vpp_BNC_spinbox.stepBy
        self.Vpp_spinbox.stepBy = self.new_Vpp_stepBy
        self.Vpp_BNC_spinbox.stepBy = self.new_Vpp_BNC_stepBy

        self.old_dBm_stepBy = self.dBm_spinbox.stepBy
        self.old_dBm_BNC_stepBy = self.dBm_BNC_spinbox.stepBy
        self.dBm_spinbox.stepBy = self.new_dBm_stepBy
        self.dBm_BNC_spinbox.stepBy = self.new_dBm_BNC_stepBy

        self.old_mW_stepBy = self.mW_spinbox.stepBy
        self.old_mW_BNC_stepBy = self.mW_BNC_spinbox.stepBy
        self.mW_spinbox.stepBy = self.new_mW_stepBy
        self.mW_BNC_spinbox.stepBy = self.new_mW_BNC_stepBy

        self.old_freq_stepBy = self.freq_spinbox.stepBy
        self.freq_spinbox.stepBy = self.new_freq_stepBy

        # Freq_unit (QComboBox) : index 0 - Hz, 1 - KHz, 2 - MHz, 3 - GHz
        self.prev_freq_unit_index = self.freq_unit.currentIndex()

        self.old_phase_stepBy = self.phase_spinbox.stepBy
        self.phase_spinbox.stepBy = self.new_phase_stepBy

        # Config
        self.load_config()

        # Visibility settings
        # SG384: freq, power (Type-N, BNC) control
        # APSYN420: freq, phase, external reference frequency control
        self.phase_group.setVisible(self.device_type)
        self.ref_freq_group.setVisible(self.device_type)
        self.power_sweep_group.setVisible(not self.device_type)
        self.power_BNC_group.setVisible(not self.device_type)
        self.BNC_output_frame.setVisible(not self.device_type)

        self.apply_gradually_checkbox_N_type.setText(
            'Apply gradually (0.01V/%.1fs)' % STEP_SLEEP_TIME)
        self.apply_gradually_checkbox_BNC.setText(
            'Apply gradually (0.01V/%.1fs)' % STEP_SLEEP_TIME)

        self.connected = False
        self.connection_callback = connection_callback

        self.red_icon = QtGui.QPixmap(ICON_RED_LED)
        self.green_icon = QtGui.QPixmap(ICON_GREEN_LED)
        self.control_widget.setEnabled(False)
        
        self.power_thread = None
        
        self.slider_value = 0
    # Sends and receives messages
    def query(self, message):
        # '\n' indicates the end of the message
        self.socket.send((message + '\n').encode('latin-1'))
        data = self.socket.recv(1024)  # receives 1024 bytes of data
        return data.decode('latin-1')[:-1]  # Removing the trailing '\n'

    # Sends messages
    def write(self, message):
        self.socket.send((message + '\n').encode('latin-1'))

    # Overrides closeEvent() of the widget
    def closeEvent(self):
        if hasattr(self, 'socket') and self.socket.fileno() != -1:
            self.socket.close()
            if self.connection_callback != None:
                self.connection_callback(False)

    def connect(self):
        if self.connected:
            # Disconnect
            self.socket.close()
            self.IDN_label.setText('')

            self.connection_status.setText('Disconnected')
            self.connect_button.setText('Connect')
            self.control_widget.setEnabled(False)
            self.connected = False
            if self.connection_callback != None:
                self.connection_callback(False)

        else:
            # Connect
            self.TCP_IP = self.IP_address.text()
            self.TCP_PORT = int(self.port.text())

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(1)  # unit in second
            self.socket.connect((self.TCP_IP, self.TCP_PORT))

            # query the instrument identification string
            self.IDN_label.setText(self.query('*IDN?'))

            # Type-N, BNC output check
            for i in range(2):
                if i == 0 or self.device_type == 0:
                    if self.query('%s?' % ENABLE_OUTPUT_Q[i][self.device_type])[0] == '0':
                        self.output_statuses[i].setPixmap(self.red_icon)
                        self.output_buttons[i].setText('Turn on')
                        self.output_on[i] = False
                    else:
                        self.output_statuses[i].setPixmap(self.green_icon)
                        self.output_buttons[i].setText('Turn off')
                        self.output_on[i] = True

            # Reads power/freq/phase and locks to external reference frequency
            if (self.device_type == 0):
                self.read_power(0)
                self.read_power(1)
            else:
                self.read_phase()
                self.lock()
                time.sleep(1)
                self.lock_status_check()
            self.read_freq()

            self.connection_status.setText('Connected')
            self.connect_button.setText('Disconnect')
            self.control_widget.setEnabled(True)
            self.connected = True
            if self.connection_callback != None:
                self.connection_callback(True)

    def read_TypeN_power(self):
        self.read_power(0)

    def read_BNC_power(self):
        self.read_power(1)

    # Reads power in dBm and converts to mW and Vp-p
    # output_type: 0 - Type-N, 1 - BNC
    def read_power(self, output_type):
        # Query the Type-N RF output amplitude in dBm.
        dBm = math.trunc(100*float(self.query('%s?' %
                                              POWER_DBM_Q[output_type][self.device_type])))/100

        self.dBm_spinboxes[output_type].setValue(dBm)
        mW = 10**(dBm/10)
        Vamp = math.sqrt(mW/10)
        self.mW_spinboxes[output_type].setValue(mW)
        self.Vpp_spinboxes[output_type].setValue(2*Vamp)

        color = 'black'
        # After read, change the spinbox background color to white
        background_color = 'white'
        # If the value is out of range, it displays the text in red
        if dBm > self.max_dBm or dBm < self.min_dBm:
            color = 'red'
        style = "QDoubleSpinBox:enabled {{ color: {0}; selection-color: {0}; background-color: {1} }}"\
            .format(color, background_color)
        self.dBm_spinboxes[output_type].setStyleSheet(style)
        self.mW_spinboxes[output_type].setStyleSheet(style)
        self.Vpp_spinboxes[output_type].setStyleSheet(style)

    def apply_TypeN_power(self):
        self.apply_power(0)

    def apply_BNC_power(self):
        self.apply_power(1)

    # Applies power in dBm
    # output_type: 0 - Type-N, 1 - BNC
    def apply_power(self, output_type):
        dBm = self.dBm_spinboxes[output_type].value()
        # Applies the value only if the value is in the range
        if dBm <= self.max_dBm and dBm >= self.min_dBm:
            self.dBm_spinboxes[output_type].setStyleSheet(
                "QDoubleSpinBox:enabled { background-color: white }")
            self.mW_spinboxes[output_type].setStyleSheet(
                "QDoubleSpinBox:enabled { background-color: white }")
            self.Vpp_spinboxes[output_type].setStyleSheet(
                "QDoubleSpinBox:enabled { background-color: white }")

            if self.apply_gradually_checkbox_N_type.checkState() and output_type == 0:
                self.disabled_widgets = [self.apply_all_button, self.power_sweep_group]
                for widget in self.disabled_widgets:
                    widget.setEnabled(False)

                curr_dBm = float(self.query(
                    '%s?' % POWER_DBM_Q[output_type]
                    [self.device_type]))
                if not output_type:
                    target_Vpp = self.Vpp_spinboxes[output_type].value()

                self.power_thread = PowerThread(self, curr_dBm, target_Vpp, output_type)
                self.power_thread.start()
                
            elif self.apply_gradually_checkbox_BNC.checkState() and output_type == 1:
                self.disabled_widgets = [self.apply_all_button, self.power_BNC_group]
                for widget in self.disabled_widgets:
                    widget.setEnabled(False)

                curr_dBm = float(self.query(
                    '%s?' % POWER_DBM_Q[output_type]
                    [self.device_type]))
                if output_type:
                    target_Vpp = self.Vpp_spinboxes[output_type].value()

                self.power_thread = PowerThread(self, curr_dBm, target_Vpp, output_type)
                self.power_thread.start()
                
            else:
                self.write('%s %.2f' % (POWER_DBM_Q[output_type][self.device_type], dBm))
                # After applied, change the background color to white
                
                

    # Reads frequency in Hz
    def read_freq(self):
        scale = 10**(3*self.freq_unit.currentIndex())
        query = '%s?' % FREQUENCY_Q[self.device_type]
        freq = float(self.query(query))/scale
        self.freq_spinbox.setValue(freq)

        color = 'black'
        # After read, change the spinbox background color to white
        background_color = 'white'
        # If the value is out of range, it displays the text in red
        if freq > self.max_freq or freq < self.min_freq:
            color = 'red'
        style = "QDoubleSpinBox:enabled {{ color: {0}; selection-color: {0}; background-color: {1} }}"\
            .format(color, background_color)
        self.freq_spinbox.setStyleSheet(style)

    # Applies frequency in Hz
    def apply_freq(self):
        scale = 10**(3*self.freq_unit.currentIndex())
        freq = self.freq_spinbox.value()
        query = '%s %f' % (FREQUENCY_Q[self.device_type], freq*scale)
        # Applies the value only if the value is in the range
        if freq <= self.max_freq and freq >= self.min_freq:
            self.write(query)
            self.freq_spinbox.setStyleSheet(
                "QDoubleSpinBox:enabled {{ background-color: white }}")

    # Reads phase in degree
    def read_phase(self):
        # Unit: SG384 - degree (only), APSYN420 - radian (default)
        phase = self.query('%s?' % PHASE_Q[self.device_type])
        if self.device_type == 1:
            phase = float(phase)*180/math.pi
        self.phase_spinbox.setValue(phase)

        color = 'black'
        # After read, change the spinbox background color to white
        background_color = 'white'
        # If the value is out of range, it displays the text in red
        if phase > self.max_phase or phase < self.min_phase:
            color = 'red'
        style = "QDoubleSpinBox:enabled {{ color: {0}; selection-color: {0}; background-color: {1} }}"\
            .format(color, background_color)
        self.phase_spinbox.setStyleSheet(style)

    # Applies phase in degree
    def apply_phase(self):
        # Unit: SG384 - degree (only), APSYN420 - radian (default)
        unit_str = ''
        if (self.device_type == 1):
            unit_str = 'deg'
        phase = self.phase_spinbox.value()
        query = '%s %.2f%s' % (PHASE_Q[self.device_type], phase, unit_str)
        # Applies only if the value is in the range
        if phase <= self.max_phase and phase >= self.min_phase:
            self.write(query)
            # After applied, change the spinbox background color to white
            self.phase_spinbox.setStyleSheet(
                "QDoubleSpinBox:enabled {{ background-color: white }}")
            

    def read_all(self):
        if self.device_type == 0:
            self.read_power(0)
            self.read_power(1)
        else:
            self.read_phase()
        self.read_freq()

    def apply_all(self):
        if self.device_type == 0:
            self.apply_power(0)
            self.apply_power(1)
        else:
            self.apply_phase()
        self.apply_freq()

    def output_TypeN_on_off(self):
        self.output_on_off(0)

    def output_BNC_on_off(self):
        self.output_on_off(1)

    # Output on-off toggle
    def output_on_off(self, output_type):
        if self.output_on[output_type]:
            self.Vpp_spinboxes[output_type].setValue(0.001)
            self.apply_power(output_type)
            time.sleep(0.2)
            if self.power_thread:
                while self.power_thread.isRunning():
                    self.power_thread.wait()
            self.write('%s 0' % ENABLE_OUTPUT_Q[output_type][self.device_type])
            self.output_statuses[output_type].setPixmap(self.red_icon)
            self.output_buttons[output_type].setText('Turn on')
            self.output_on[output_type] = False
        else:
            self.write('%s 1' % ENABLE_OUTPUT_Q[output_type][self.device_type])
            self.output_statuses[output_type].setPixmap(self.green_icon)
            self.output_buttons[output_type].setText('Turn off')
            self.output_on[output_type] = True

    # Customized stepBy function
    # Called after the user changes the value by pushing the up/down button of the spinbox
    def new_freq_stepBy(self, steps):
        self.old_freq_stepBy(steps)  # default stepBy function
        self.freq_updated()

    # Slot connected to 'editingFinished()' signal from the spinbox
    # Called after the user directly edited the value of the spinbox
    def freq_editing_finished(self):
        self.freq_updated()

    # Change colors according to the updated value in the spinbox
    def freq_updated(self):
        color = 'black'
        # Yellow background indicates that the value has not been applied yet.
        background_color = 'yellow'
        if self.freq_spinbox.value() > self.max_freq or self.freq_spinbox.value() < self.min_freq:
            color = 'red'
        style = "QDoubleSpinBox:enabled {{ color: {0}; selection-color: {0}; background-color: {1} }}"\
            .format(color, background_color)

        self.freq_spinbox.setStyleSheet(style)

        # if self.auto_freq_apply_checkbox.isChecked():
        #    self.apply_freq()

    # Slot connected to 'currentIndexChanged()' signal from 'freq_unit' spinbox
    def freq_unit_changed(self, index):
        new_freq_unit_index = self.freq_unit.currentIndex()
        # indices of 'freq_unit' (QComboBox) : 0 - Hz, 1 - KHz, 2 - MHz, 3 - GHz
        scale = 10**(3*(new_freq_unit_index - self.prev_freq_unit_index))

        self.freq_spinbox.setValue(self.freq_spinbox.value()/scale)
        self.freq_spinbox.setDecimals(3*new_freq_unit_index)
        self.freq_step_size.setText(str(float(self.freq_step_size.text())/scale))
        self.freq_step_size_changed()

        self.max_freq = self.max_freq/scale
        self.min_freq = self.min_freq/scale

        self.prev_freq_unit_index = new_freq_unit_index

    # Slot connected to 'editingFinished()' signal from 'freq_step_size'
    def freq_step_size_changed(self):
        # Changes the stepsize of the spinbox according to the value of 'freq_step_size'
        self.freq_spinbox.setSingleStep(float(self.freq_step_size.text()))

    def new_Vpp_stepBy(self, steps):
        self.old_Vpp_stepBy(steps)
        self.Vpp_updated(0)

    def new_Vpp_BNC_stepBy(self, steps):
        self.old_Vpp_BNC_stepBy(steps)
        self.Vpp_updated(1)

    def Vpp_editing_finished(self):
        self.Vpp_updated(0)

    def Vpp_BNC_editing_finished(self):
        self.Vpp_updated(1)

    def Vpp_updated(self, output_type):
        # Updates mW, dBm spinboxes according to the value of Vpp spinbox
        Vamp = self.Vpp_spinboxes[output_type].value()/2
        mW = 10*Vamp**2
        if mW > 0:
            dBm = math.trunc(100*(10*math.log10(mW)))/100
        else:
            dBm = NEG_INF_DBM
        self.mW_spinboxes[output_type].setValue(mW)
        self.dBm_spinboxes[output_type].setValue(dBm)

        color = 'black'
        background_color = 'yellow'
        if dBm > self.max_dBm or dBm < self.min_dBm:
            color = 'red'
        style = "QDoubleSpinBox:enabled {{ color: {0}; selection-color: {0}; background-color: {1} }}"\
            .format(color, background_color)
        self.dBm_spinboxes[output_type].setStyleSheet(style)
        self.mW_spinboxes[output_type].setStyleSheet(style)
        self.Vpp_spinboxes[output_type].setStyleSheet(style)

        # if self.auto_power_apply_checkbox.isChecked():
        #    self.apply_power()

    def Vpp_step_size_changed(self):
        self.Vpp_spinbox[0].setSingleStep(float(self.Vpp_step_size.text()))

    def Vpp_BNC_step_size_changed(self):
        self.Vpp_spinbox[1].setSingleStep(float(self.Vpp_BNC_step_size.text()))

    def new_mW_stepBy(self, steps):
        self.old_mW_stepBy(steps)
        self.mW_updated(0)

    def new_mW_BNC_stepBy(self, steps):
        self.old_mW_BNC_stepBy(steps)
        self.mW_updated(1)

    def mW_editing_finished(self):
        self.mW_updated(0)

    def mW_BNC_editing_finished(self):
        self.mW_updated(1)

    def mW_updated(self, output_type):
        mW = self.mW_spinboxes[output_type].value()
        Vamp = math.sqrt(mW/10)
        if mW > 0:
            dBm = math.trunc(100*(10*math.log10(mW)))/100
        else:
            dBm = NEG_INF_DBM
        self.Vpp_spinboxes[output_type].setValue(2*Vamp)
        self.dBm_spinboxes[output_type].setValue(dBm)

        color = 'black'
        background_color = 'yellow'
        if dBm > self.max_dBm or dBm < self.min_dBm:
            color = 'red'
        style = "QDoubleSpinBox:enabled {{ color: {0}; selection-color: {0}; background-color: {1} }}"\
            .format(color, background_color)
        self.dBm_spinboxes[output_type].setStyleSheet(style)
        self.mW_spinboxes[output_type].setStyleSheet(style)
        self.Vpp_spinboxes[output_type].setStyleSheet(style)

        # if self.auto_power_apply_checkbox.isChecked():
        #    self.apply_power()

    def mW_step_size_changed(self):
        self.mW_spinboxes[0].setSingleStep(float(self.mW_step_size.text()))

    def mW_BNC_step_size_changed(self):
        self.mW_spinboxes[1].setSingleStep(float(self.mW_BNC_step_size.text()))

    def new_dBm_stepBy(self, steps):
        self.old_dBm_stepBy(steps)
        self.dBm_updated(0)

    def new_dBm_BNC_stepBy(self, steps):
        self.old_dBm_BNC_stepBy(steps)
        self.dBm_updated(1)

    def dBm_editing_finished(self):
        self.dBm_updated(0)

    def dBm_BNC_editing_finished(self):
        self.dBm_updated(1)

    def dBm_updated(self, output_type):
        dBm = self.dBm_spinboxes[output_type].value()
        mW = 10**(dBm/10)
        Vamp = math.sqrt(mW/10)
        self.mW_spinboxes[output_type].setValue(mW)
        self.Vpp_spinboxes[output_type].setValue(2*Vamp)

        color = 'black'
        background_color = 'yellow'
        if dBm > self.max_dBm or dBm < self.min_dBm:
            color = 'red'
        style = "QDoubleSpinBox:enabled {{ color: {0}; selection-color: {0}; background-color: {1} }}"\
            .format(color, background_color)
        self.dBm_spinboxes[output_type].setStyleSheet(style)
        self.mW_spinboxes[output_type].setStyleSheet(style)
        self.Vpp_spinboxes[output_type].setStyleSheet(style)

        # if self.auto_power_apply_checkbox.isChecked():
        #    self.apply_power()

    def dBm_step_size_changed(self):
        self.dBm_spinboxes[0].setSingleStep(float(self.dBm_step_size.text()))

    def dBm_BNC_step_size_changed(self):
        self.dBm_spinboxes[1].setSingleStep(float(self.dBm_BNC_step_size.text()))

    def new_phase_stepBy(self, steps):
        self.old_phase_stepBy(steps)
        self.phase_updated()

    def phase_editing_finished(self):
        self.phase_updated()

    def phase_updated(self):
        phase = self.phase_spinbox.value()
        color = 'black'
        background_color = 'yellow'
        if phase > self.max_phase or phase < self.min_phase:
            color = 'red'
        style = "QDoubleSpinBox:enabled {{ color: {0}; selection-color: {0}; background-color: {1} }}"\
            .format(color, background_color)
        self.phase_spinbox.setStyleSheet(style)

        # if self.auto_phase_apply_checkbox.isChecked():
        #    self.apply_phase()

    def phase_step_size_changed(self):
        self.phase_spinbox.setSingleStep(float(self.phase_step_size.text()))

    # external reference frequency settings

    def ext_ref_freq_editing_finished(self):
        if self.ext_ref_freq_lineedit.text() == self.ext_ref_freq_str:
            self.ext_ref_freq_lineedit.setStyleSheet(
                "QLineEdit:enabled { color: black; selection-color: black }")
        else:
            # If the value is different from the config value, display the text in blue.
            self.ext_ref_freq_lineedit.setStyleSheet(
                "QLineEdit:enabled { color: blue; selection-color: blue }")

    def lock(self):
        self.write('%s EXTernal' % REF_SOURCE_Q[self.device_type])
        self.write('%s %.3f' % (EXT_FREQ_Q[self.device_type], float(
            self.ext_ref_freq_lineedit.text())*(10**6)))  # unit: MHz
        print(self.ext_ref_freq_str)

    def lock_status_check(self):
        locked = int(self.query('%s?' % LOCK_Q[self.device_type]))
        if locked:
            self.lock_status.setPixmap(self.green_icon)
        else:
            self.lock_status.setPixmap(self.red_icon)

    def load_config(self):
        self.config = ConfigParser()
        self.config.read(dirname + CONFIG_PATH)
        nickname = self.config.get('SG' + str(self.device_index), 'nickname')
        self.device_nickname.setText(nickname)
        if nickname.find('Trap_') >= 0:
            self.apply_gradually_checkbox_N_type.setCheckState(True)
            self.apply_gradually_checkbox_BNC.setCheckState(True)
        else:
            self.apply_gradually_checkbox_N_type.setCheckState(False)
            self.apply_gradually_checkbox_BNC.setCheckState(False)
        self.device_type = int(self.config.get(
            'SG' + str(self.device_index), 'device_type'))
        self.TCP_IP = self.config.get('SG' + str(self.device_index), 'ip_address')

        scale = 10**(3*self.freq_unit.currentIndex())
        self.max_freq = float(self.config.get(
            'SG' + str(self.device_index),
            'max_freq_Hz')) / scale
        self.min_freq = float(self.config.get(
            'SG' + str(self.device_index),
            'min_freq_Hz')) / scale

        if self.device_type == 0:
            self.max_dBm = float(self.config.get(
                'SG' + str(self.device_index), 'max_power_dBm'))
            self.min_dBm = float(self.config.get(
                'SG' + str(self.device_index), 'min_power_dBm'))
        else:
            self.max_phase = float(self.config.get(
                'SG' + str(self.device_index), 'max_phase_deg'))
            self.min_phase = float(self.config.get(
                'SG' + str(self.device_index), 'min_phase_deg'))
            self.ext_ref_freq_str = self.config.get(
                'SG' + str(self.device_index), 'ext_ref_freq_MHz')
            self.ext_ref_freq_lineedit.setText(self.ext_ref_freq_str)

        self.IP_address.setText(self.TCP_IP)
        self.port.setText(PORT_NUM[self.device_type])

    def load_config_curr(self):
        scale = 10**(3*self.freq_unit.currentIndex())
        curr_freq = float(self.config.get(
            'SG' + str(self.device_index),
            'curr_freq_Hz')) / scale
        self.freq_spinbox.setValue(curr_freq)
        self.freq_updated()

        if self.device_type == 0:
            curr_dBm = float(self.config.get(
                'SG' + str(self.device_index),
                'curr_power_dBm'))
            self.dBm_spinbox.setValue(curr_dBm)
            self.dBm_updated(0)
        else:
            curr_phase = float(self.config.get(
                'SG' + str(self.device_index),
                'curr_phase_deg'))
            self.phase_spinbox.setValue(curr_phase)
            self.phase_updated()

    def save_config(self):
        self.config = ConfigParser()
        self.config.read(dirname + CONFIG_PATH)
        curr_dBm = self.dBm_spinbox.value()
        scale = 10**(3*self.freq_unit.currentIndex())
        curr_freq = self.freq_spinbox.value()*scale
        curr_phase = self.phase_spinbox.value()
        curr_ext_ref_freq_str = self.ext_ref_freq_lineedit.text()

        self.config.set('SG'+str(self.device_index), 'curr_freq_Hz', str(curr_freq))
        if self.device_type == 0:
            self.config.set('SG'+str(self.device_index), 'curr_power_dBm', str(curr_dBm))
        else:
            self.config.set(
                'SG' + str(self.device_index),
                'curr_phase_deg', str(curr_phase))
            self.config.set(
                'SG' + str(self.device_index),
                'ext_ref_freq_MHz', curr_ext_ref_freq_str)

        with open(dirname + CONFIG_PATH, 'w') as configfile:
            self.config.write(configfile)
            
        
    def freq_slider_moved(self, value):
        val = value - self.slider_value
        curr_freq = self.freq_spinbox.value()
        step_size = float(self.freq_step_size.text())
        new_freq = curr_freq + step_size * val
        self.freq_spinbox.setValue(new_freq)
        self.apply_freq()
        self.slider_value = value
        
        
class MainWindow(QtWidgets.QDialog):

    clsSignal = pyqtSignal(int)

    def closeEvent(self, e):
        self.clsSignal.emit(0)

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Main Window')

        global CONFIG_PATH
        CONFIG_PATH = CONFIG_PATH + '/' + socket.gethostname() + '.ini'
        if not os.path.isfile(dirname + CONFIG_PATH):
            shutil.copyfile(dirname + CONFIG_DIR + '/default.ini', dirname + CONFIG_PATH)
            
        # Get configure data
        self.config = ConfigParser()
        self.config.read(dirname + CONFIG_PATH)
        self.device_num = int(self.config.get('SETTINGS', 'device_num'))
        
        # self.'SG'+'i' = SignalGenerator(i)
        for i in range(self.device_num):
            setattr(self, 'SG'+str(i), SignalGenerator(i, self))


        # Main Window Vbox
        vbox = QtWidgets.QVBoxLayout()

        # 1st Frame : Save/Load/Edit Configure
        self.config_frame = QtWidgets.QFrame(self)
        self.config_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.config_frame.setMinimumSize(400, 150)
        self.config_frame.setMaximumSize(400, 150)
        
        # 2 hbox Layouts for path & button contained in single config vbox Layout
        # path_hbox will be holding config file paths
        # buttons_hbox will be holding qpushbuttons for load/save/edit
        config_vbox = QtWidgets.QVBoxLayout()
        config_path_hbox = QtWidgets.QHBoxLayout()
        config_buttons_hbox = QtWidgets.QHBoxLayout()
        config_vbox.addLayout(config_path_hbox)
        config_vbox.addLayout(config_buttons_hbox)
        # add config vbox Layout with 2 hbox into Config Frame
        self.config_frame.setLayout(config_vbox)

        # Add components into path hbox in config vbox
        self.config_path_label = QtWidgets.QLabel(self)
        self.config_path_label.setText('Config file: ' + CONFIG_PATH)
        self.config_dir_open_button = QtWidgets.QPushButton('Open \n Config dir')
        self.config_dir_open_button.setMinimumSize(110, 50)
        self.config_dir_open_button.setMaximumSize(110, 50)
        self.config_dir_open_button.clicked.connect(self.open_config_dir)
        config_path_hbox.addWidget(self.config_path_label)
        config_path_hbox.addWidget(self.config_dir_open_button)

        # Add components into button hbox in config vbox
        self.load_config_button = QtWidgets.QPushButton('\n Load \n Config file \n')
        self.edit_config_button = QtWidgets.QPushButton('\n Edit \n Config file \n')
        self.save_config_button = QtWidgets.QPushButton('\n Save \n Current setting \n')
        h_size, v_size = 120, 50
        self.load_config_button.setMinimumSize(h_size, v_size)
        self.load_config_button.setMaximumSize(h_size, v_size)
        self.edit_config_button.setMinimumSize(h_size, v_size)
        self.edit_config_button.setMaximumSize(h_size, v_size)
        self.save_config_button.setMinimumSize(h_size, v_size)
        self.save_config_button.setMaximumSize(h_size, v_size)
        self.load_config_button.clicked.connect(self.load_config)
        self.edit_config_button.clicked.connect(self.edit_config)
        self.save_config_button.clicked.connect(self.save_config)
        config_buttons_hbox.addWidget(self.load_config_button)
        config_buttons_hbox.addWidget(self.edit_config_button)
        config_buttons_hbox.addWidget(self.save_config_button)
        
        
        # 2nd Frame : Signal Generator
        self.SG_frame = QtWidgets.QFrame(self)
        self.SG_frame.setMinimumSize(i*425, 0)
        # SG_hbox_Layout will be holding displaying widgets for signal generator
        SG_hbox = QtWidgets.QHBoxLayout()
        SG_hbox.setContentsMargins(0, 0, 0, 0)

        # add SG_hbox_Layout to SG_Frame
        self.SG_frame.setLayout(SG_hbox)

        # Add components to SG_hbox_Layout
        # self.'SG' inherits QWidgets class
        for i in range(self.device_num):
            SG_hbox.addWidget(getattr(self, 'SG'+str(i)))
        SG_hbox.addStretch(1)
        # SG_hbox_Layout now contains # of SG Widgets same to device #
        
        
        # 3rd Frame : Oscilloscope                
        self.OSC_frame = QtWidgets.QFrame(self)
        self.OSC_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.OSC_frame.setMinimumSize(210, 150)
        self.OSC_frame.setMaximumSize(210, 150)
        # OSC_button_hbox_Layout will be holding open button
        OSC_button_hbox = QtWidgets.QHBoxLayout()
        # Add OSC_button_hbox_ayout to OSC_Frame
        self.OSC_frame.setLayout(OSC_button_hbox)

        # Create and Connect open_osc button and add to OSC_button_hbox Layout
        self.open_OSC_button = QtWidgets.QPushButton('\n Open \n\n Oscilloscope \n')
        self.open_OSC_button.setFont(QtGui.QFont('Segoe UI Black', 12))
        self.open_OSC_button.setStyleSheet("font-weight: bold;")
        self.open_OSC_button.setMinimumSize(170, 100)
        self.open_OSC_button.setMaximumSize(170, 100)
        self.open_OSC_button.clicked.connect(self.open_OSC)
        OSC_button_hbox.addWidget(self.open_OSC_button)


        # Make Top frame containing Configure & Oscilloscope widget        
        self.Top_frame = QtWidgets.QFrame(self)
        # self.Top_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        Top_hbox = QtWidgets.QHBoxLayout()
        Top_hbox.addWidget(self.config_frame)
        Top_hbox.addWidget(self.OSC_frame)
        self.Top_frame.setLayout(Top_hbox)


        # Finally sum up all Frames to Overall Vbox and align
        # vbox.addWidget(self.config_frame)
        vbox.addWidget(self.Top_frame)
        vbox.addWidget(self.SG_frame)
        # vbox.addWidget(self.OSC_frame)
        # vbox.setAlignment(self.config_frame, QtCore.Qt.AlignLeft)
        vbox.setAlignment(self.Top_frame, QtCore.Qt.AlignLeft)
        vbox.setAlignment(self.SG_frame, QtCore.Qt.AlignLeft)
        # vbox.setAlignment(self.OSC_frame, QtCore.Qt.AlignLeft)
        self.setLayout(vbox)

    def closeEvent(self, event):
        for i in range(self.device_num):
            if hasattr(self, 'SG'+str(i)):
                SG = getattr(self, 'SG'+str(i))
                SG.closeEvent()
        
        if hasattr(self, 'OSC'):
#            self.OSC.closeEvent(event)
            self.OSC.close()

    def load_config(self):
        for i in range(0, self.device_num):
            if hasattr(self, 'SG'+str(i)):
                SG = getattr(self, 'SG'+str(i))
                SG.load_config()
                SG.load_config_curr()

    def save_config(self):
        for i in range(0, self.device_num):
            if hasattr(self, 'SG'+str(i)):
                SG = getattr(self, 'SG'+str(i))
                SG.save_config()

    def edit_config(self):  # support Windows only
        os.startfile(dirname + CONFIG_PATH)

    def open_config_dir(self):  # support Windows only
        os.startfile(dirname + CONFIG_DIR)
        
    def open_OSC(self):
        sg_list = []
        for i in range(0, self.device_num):
            if hasattr(self, 'SG'+str(i)):
                SG = getattr(self, 'SG'+str(i))
                sg_list.append(SG)
        self.OSC = DS1052E_GUI(instance_name='DS1052E_v0.02')
        self.OSC.SG = sg_list
        self.OSC.show()


if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    signalGenerator = MainWindow()
    # signalGenerator.showMaximized()
    signalGenerator.show()
   # app.exec_()
#   sys.exit(app.exec_())
