# -*- coding: utf-8 -*-
"""
Created on Sat Oct 30 20:48:23 2021

@author: QCP32
"""
import os, time, datetime
version = "1.4"
filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

from SequencerProgram_v1_07 import SequencerProgram, reg
import SequencerUtility_v1_01 as su
from ArtyS7_v1_02 import ArtyS7

from PyQt5.QtCore import pyqtSignal, QObject, QThread

class SequencerRunner(QObject):
        
    sig_seq_run = pyqtSignal()
    sig_dev_con = pyqtSignal(bool)
    sig_seq_iter_done = pyqtSignal(int, int) # iter, total_run
    sig_seq_complete = pyqtSignal(bool) # True: completed, False: broken while running.
    sig_occupied = pyqtSignal(bool)
    # sig_swch_restore = pyqtSignal() # This signal runs the switch panel, so the switches retunrs to initial settings.
    
    sequencer = None
    is_opened = False
    seq_file = ""
    
    data_run_index = 0
    data_run_loop = 1
    
    data = []
    spontaneous = False

    user_stop = False
    device_sweep_flag = False 
    
    def __init__(self, ser_num=None, hw_def=None, parent=None):
        super().__init__()
        self.parent = parent
        self.ser_num = ser_num
        self.com_port = self.getComPort(ser_num)
        self.hw_def = hw_def
        self.SequencerProgram = SequencerProgram
        self.reg = reg
        self.su = su
        self.openHardwareDefinition(self.hw_def)
        self.runner = Runner(self)
        self.runner.finished.connect(self._finishedRunner)
        self.default_hw_def_dir = dirname
        
        self.start_time = None
        self.end_time = None
        
        self.iter_start_time = None
        self.iter_end_time = None
        
        self.occupant = ""
        
    def openDevice(self, com_port=None):
        if com_port == None:
            com_port = self.com_port
        try:
            if self.sequencer == None:
                self.sequencer = ArtyS7(com_port)
            else:
                self.sequencer.com.open()
            self.toStatusBar("Connected to the FPGA.")
            self.is_opened = True
            self.sig_dev_con.emit(True)
        except Exception as e:
            self.toStatusBar("Failed to open the FPGA. (%s)" % (e))
            return -1 # open fail
            
    def closeDevice(self):
        if self.is_opened:
            self.sequencer.com.close()
            self.toStatusBar("Closed the FPGA.")
            self.is_opened = False
            self.sig_dev_con.emit(False)
        else:
            self.toStatusBar("Failed to close the FPGA. Maybe the FPGA is already closed?")
            
    def openHardwareDefinition(self, hw_def):
        try:
            import sys
            sys.path.append(dirname)
            exec("import %s as hd" % hw_def)
            exec("self.hd = hd")
        except Exception as e:
             self.toStatusBar("Failed to open the hardware definition (%s)." % e)
             
    def loadSequencerFile(self, seq_file="", replace_dict={}):
        """
        Args: seq_file (str), replace_dict (dict)
            - seq_file: It accepts the full path of the sequencer script.
                        It automatically finds where the hardware definition is defined and replaces it to its own hardware definition.
                        the "__main__" function in the seq_file will be ignored.
            - replace_dict: The replace_dict replaces the given parameters in the seq_file.
                            To find parameters, please use getParameters function below.
                            replace dict = {
                                            n-th_line_where_the_parameter1_defined: {"parameter_name1"}: parameter_value,
                                            n-th_line_where_the_parameter2_defined: {"parameter_name2"}: parameter_value
                                            }
                            n-th_line_where_the_parameter1_defined: int
                            "parameter_name1": str
                            parameter_value: int
                        
        """
        if self.is_opened:
            script_filename = os.path.basename(seq_file)
            file_string = self.replaceParameters(seq_file, replace_dict)
            self._executeFileString(file_string)
            self.seq_file = script_filename
            # self.toStatusBar("Loaded file (%s)." % script_filename)
        else:
            self.toStatusBar("You must open the FPGA first.")
            
    def runSequencerFile(self, iteration=1, device_sweep=False):
        if self.is_opened:
            self.sig_seq_run.emit()
            self.device_sweep_flag = device_sweep
            self.data_run_index = 0
            self.data_run_loop = iteration
            self.data = []
            
            # spontaneous flag is needed when the running time is measured inside of this class.
            if not self.spontaneous:
                self.start_time = datetime.datetime.now()
            
            self.startRunner()
        else:
            self.toStatusBar("You must open the FPGA first.")
            
    def startRunner(self):
        self.data_run_index += 1
        self.iter_start_time = datetime.datetime.now()
        self.runner.start()
        
    def stopRunner(self):
        # user_stop lets us know whether it is aborted while running.
        self.user_stop = True
        self.sequencer.stop_sequencer()
        
    def replaceParameters(self, seq_file="", replace_dict={}):
        """
        This function reads a sequencer file and retunrs a file string with gvien parameters changed.
        """
        file_string = ''
        line_idx = 0
        line_idx_list = list(replace_dict.keys())
        with open (seq_file) as f:
            while True:
                line = f.readline()
                if not line:
                    break
                if " as hd\n" in line:
                    print ("replaced from %s" % line)
                    line = "import %s as hd\n" % self.hw_def
                    print("to %s" % line)
                if line_idx in line_idx_list:
                    line = '%s=%.0f\n' % (replace_dict[line_idx]["param"], replace_dict[line_idx]["value"])
                file_string += line
                line_idx += 1
        return file_string
        
    def getComPort(self, ser_num=""):
        from serial.tools.list_ports import comports
        for dev in comports():
            if dev.serial_number == ser_num:
                return dev.device
            
        return None
        
    def getParameters(self, seq_file=""):
        """
        This function reads a sequencer file and returns parameters as a dict.
        Note that the parameter value is stored as a string. (for some reason.)
        The key of the param_dict is a line index. This line index is used to replace the parameter values.
        """
        param_dict = {}
        line_idx = 0
        with open (seq_file) as f:
            while True:
                line = f.readline()
                if not line: break
                if not line[0] == "#" and "=" in line:
                    param = line.split('=')[0]
                    param = param.replace(" ", "")
                    if  param.upper() == param: # if the key consists of capital characters only.
                        value = line.split('=')[1]
                        value = value.replace(" ", "")
                        if value[-1] == "\n":
                            value = value[:-1]
                        param_dict[line_idx] = {"param": param, "value": value}
                line_idx += 1
        return param_dict
        
            
    def toStatusBar(self, message):
        if not self.parent == None:
            self.parent.toStatusBar(message)
        else:
            print(message)
            
    def _finishedRunner(self):
        self.iter_end_time = datetime.datetime.now()

        if self.user_stop:
            self.sig_seq_complete.emit(False)
            self.sequencer.flush_Output_FIFO()
            self.user_stop = False # initialize the flag.
            self.toStatusBar("Stopped running sequencer.")
        else:
            if not self.data_run_index == self.data_run_loop:
                self.sig_seq_iter_done.emit(self.data_run_index, self.data_run_loop)
                self.startRunner()
            else:
                if not self.spontaneous:
                    self.end_time = datetime.datetime.now()
                self.sig_seq_complete.emit(True)
                # self.toStatusBar("Completed running sequencer.")
                
    def _executeFileString(self, file_string):
        """
        This functions runs a file string and saves it in the global dictionary.
        """
        gl = dict(globals())
        exec(file_string, gl)
        self.gl = gl
            
class Runner(QThread):
    
    sig_data_list = pyqtSignal(list)
    status = "standby"
    buffer_data = []
    data = []
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
    
    def run(self):
        self.status = "running"
        if self.controller.device_sweep_flag:
            time.sleep(1)
        
        controller = self.controller
        s = controller.gl['s']
        
        s.program(show=False, target=controller.sequencer)
        controller.sequencer.auto_mode()
        controller.sequencer.start_sequencer()
        
        self.data = []
        while(controller.sequencer.sequencer_running_status() == 'running'):
            data_count = controller.sequencer.fifo_data_length()
            self.data += controller.sequencer.read_fifo_data(data_count)
        
        data_count = controller.sequencer.fifo_data_length()
        while (data_count > 0):
            self.data += controller.sequencer.read_fifo_data(data_count)
            data_count = controller.sequencer.fifo_data_length()

        print(self.data)
            
        controller.data.append(self.data)
        self.status = "standby"