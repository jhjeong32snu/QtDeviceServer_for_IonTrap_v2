# -*- coding: utf-8 -*-
"""
Created on Sun Nov 28 22:37:43 2021

@author: QCP32
"""
import os, time, datetime
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QVBoxLayout
from PyQt5.QtCore    import pyqtSignal, QMutex, QWaitCondition, QThread

import numpy as np
import pickle
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import pathlib

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)
uifile = dirname + '/scanner.ui'
Ui_Form, QtBaseClass = uic.loadUiType(uifile)
version = "2.0"

#%% Temporary
class Scanner(QtWidgets.QWidget, Ui_Form):
    
    scan_request = pyqtSignal(float, float, float)
    sig_move_done = pyqtSignal()

    sig_update_plot = pyqtSignal()
    
    user_run_flag = False
    
    def __init__(self, device_dict=None, parent=None, theme="black"):
        QtWidgets.QMainWindow.__init__(self)
        self.setupUi(self)
        
        self.device_dict = device_dict
        self.parent = parent
        self._theme = theme
        self.motors = self.device_dict["motors"]
        self.sequencer = self.device_dict["sequencer"]
        
        #self.cp = self.parent.cp
        #self.mail = self.parent.parent.parent.library_dict["mail_sender"]
        
        
        self.save_file_name = "%s_default" % datetime.datetime.now().strftime("%y%m%d")
        self.save_file_dir = os.path.abspath(dirname + '/../save_data')
        
        self._initUi()
        self._initParameters()
        
        
    def _initUi(self):
        self.image = np.random.random((3, 3))
        
        # Plot
        self.toolbar, self.ax, self.canvas, self.im = self._create_canvas(self.image_viewer)
        # Connect FPGA signals
        #self.sequencer.sig_occupied.connect(self._setInterlock)
        #self.sequencer.sig_seq_complete.connect(self._completeProgress)

        self.image_handler = ImageHandler(self)
        self.image_handler._sig_img_process_done.connect(self.showImage)
        self.image_handler.start()
        
        # self.readStagePosition()

        # Internal 
        self.disable_list = [self.BTN_scan_vicinity,
                             self.BTN_pause_or_resume_scanning,
                             self.BTN_start_scanning,
                             self.BTN_go_to_max]
        
        
    def _initParameters(self):
        self.x_pos = 0
        self.y_pos = 0
        
        self.x_pos_list = [-0.1, 0, 0.1]
        self.y_pos_list = [-0.1, 0, 0.1]
        self.x_step = 0.1
        self.y_step = 0.1
        
        self.pmt_exposure_time_in_ms = 1
        self.num_points_done = 0
        self.latest_count = -1
        
        self.scanning_flag = False
        self.scan_ongoing_flag = True  # pause/resume scanning
        self.gotomax_rescan_radius = 1  # tile size to rescan in self.go_to_max()
        self.currently_rescanning = False  # true during gotomax operation
        self.save_file = str(pathlib.Path(__file__).parent.resolve()) + "/data/default.csv"
        
        self.LE_save_file_dir.setText(self.save_file_dir)
        self.LE_save_file_name.setText(self.save_file_name)
        # Setup: scanning thread
        
        self.sig_move_done.connect(self._recievedPosition)

        self.PMT_counts_list = []
        self.PMT_number_list = []
        self.PMT_num = 0
        
        self.PMT_vmin = 0
        self.PMT_vmax = 100
        
    #%% Signal-connected functions
    def pressedScanStartButton(self):
        if not self.sequencer.is_opened:
            self.toStatusBar("The FPGA is not opened!")
        else:
            # read and register scan settings
            padding = 0.00001  # some small value to include the stop value in the scan range
            x_list = np.arange(self.GUI_x_start.value(),
                               self.GUI_x_stop.value() + padding,
                               self.GUI_x_step.value())
            y_list = np.arange(self.GUI_y_start.value(),
                               self.GUI_y_stop.value() + padding,
                               self.GUI_y_step.value())
            
            self.startScanning(x_list, y_list)
            
    def pressedScanVicinityButton(self):
        if not self.sequencer.is_opened:
            self.toStatusBar("The FPGA is not opened!")
        else:
            x_list = np.asarray([self.x_pos - self.x_step,
                                self.x_pos,
                                self.x_pos + self.x_step])
            y_list = np.asarray([self.y_pos - self.y_step,
                                self.y_pos,
                                self.y_pos + self.y_step])
            
            self.startScanning(x_list, y_list)
            
    def pressedApplyButton(self):
        self.sig_update_plot.emit()

    def pressedGoToMax(self):
        self.num_points_done = self.x_num * self.y_num
        self.goToMax()
        
    def pressedChangeSaveDir(self):
        save_dir = QFileDialog.getExistingDirectory(parent=self, directory=dirname + '/../save_data')
        if save_dir == "":
            self.toStatusBar("Aborted changing the saving directory.")
        else:
            self._changeSaveDir(save_dir)
            self.save_file_dir = save_dir
            self.toStatusBar("Changed the saving directory.")
        
    def pressedLoadSaveFile(self):
        file_to_load, _ = QFileDialog.getOpenFileName(self, caption="Opening saved files", directory=self.save_file_dir, filter="*.pkl")
            
        self.file_to_load = file_to_load
        if file_to_load == "":
            self.toStatusBar("Aborted loading a saved file.")
            return
        else:
            try:
                self._loadSaveFile(file_to_load)
                self.toStatusBar("Opened the saved file. (%s)" % file_to_load)
            except Exception as err:
                self.toStatusBar("Error while opening the file.(%s)" % err)
            
        
#%%
    def changedStepValue(self, value):
        if "_x_" in self.sender().objectName():
            self.x_step = value
        elif "_y_" in self.sender().objectName():
            self.y_step = value
        
    def startScanning(self, x_list, y_list):
        self._setupScanRange(x_list=x_list, y_list=y_list)
        # initiate scanning
        self.scanning_flag = True
        self.user_run_flag = True
        
        self.BTN_pause_or_resume_scanning.setText("Pause Scanning")
        
        self.sequencer.occupant = "scanner"
        self.sequencer.sig_occupied.emit(True)
        
        self.toStatusBar("Started scanning.")
        self.keepScanning()
        
    def sendRequest(self, x_pos, y_pos):
        """
        initiates a scan request to the scanning thread
        calculates the scan position based on self.num_points_done
        """
        # zigzag scanning to minimize backlash
        if np.where(abs(self.y_pos_list - y_pos) < 0.001)[0][0] % 2 == 1:  # for even-numbered rows
            original_index = self.num_points_done % self.x_num
            new_index = -1 * (original_index + 1)  # counting from the end of the list
            x_pos = self.x_pos_list[new_index]  # overwriting x_pos
            
        self.moveMotorPosition(x_pos, y_pos)
        
    def pauseScanning(self):
        if self.sequencer.is_opened:
            if self.scanning_flag:  # scanning -> pause
                self.scanning_flag = False
                self.user_run_flag = False
                self.BTN_pause_or_resume_scanning.setText("Resume Scanning")
                
                self.sequencer.occupant = ""
                self.sequencer.sig_occupied.emit(False)
                
                self.toStatusBar("Paused scanning.")
            else:  # pause -> resume
                self.scanning_flag = True
                self.user_run_flag = True
                self.BTN_pause_or_resume_scanning.setText("Pause Scanning")
                
                self.sequencer.occupant = "scanner"
                self.sequencer.sig_occupied.emit(True)
                
                self.keepScanning()
                self.toStatusBar("Resumed scanning.")
        else:
            self.toStatusBar("The FPGA is not opened.")

    
    def _changeSaveDir(self, save_dir):
        self.LE_save_file_dir.setText(save_dir)
    
    def keepScanning(self):
        x_pos = self.x_pos_list[self.num_points_done % self.x_num]
        y_pos = self.y_pos_list[self.num_points_done // self.x_num]
        
        self.sendRequest(x_pos, y_pos)
    
    def goToMax(self):
        true_y_argmax, true_x_argmax = np.unravel_index(np.argmax(self.image.T, axis=None), self.image.T.shape)
        # sending motors to max position by making a measurement at that position
        print("max", true_x_argmax, true_y_argmax)
        x_pos = self.x_pos_list[true_x_argmax]
        y_pos = self.y_pos_list[true_y_argmax]
                
        self.moveMotorPosition(x_pos, y_pos)
    
    def showImage(self):
        # Note that the thread does all the work, the main thread updates the plot only.
        self.canvas.draw_idle()
        
    def toStatusBar(self, msg):
        self.parent.toStatusBar(msg)
        
    def moveMotorPosition(self, x_pos, y_pos, move_only=False):
        self.motors.toWorkList(["C", "MOVE", ["px", x_pos, "py", y_pos], self])
        
    def readStagePosition(self):
        self.motors.toWorkList(["Q", "POS", ["px", "py"], self])
        
    def toMessageList(self, msg):
        if msg[2] == "POS":
            data = msg[-1]
            print("yoisho")
            
            nickname_list = data[0::2]
            position_list = data[1::2]
            
            for nickname, position in zip(nickname_list, position_list):
                if nickname == "px":
                    self.x_pos = round(position*1000)/1000
                elif nickname == "py":
                    self.y_pos = round(position*1000)/1000
            self.sig_move_done.emit()
            
    def runPMT_Exposure(self, num_run = 50):
        self.setExposureTime(self.pmt_exposure_time_in_ms, num_run)
        self.sequencer.runSequencerFile()
        
        
    def setExposureTime(self, exposure_time, num_run=50):
        # CHECK FOR SYNTAX
        self.exposure_time = exposure_time
        self.sequencer.loadSequencerFile(seq_file= dirname + "/simple_exposure.py",
                                         replace_dict={13:{"param": "EXPOSURE_TIME_IN_100US", "value": int(exposure_time*10)},
                                                       14:{"param": "NUM_REPEAT", "value": num_run}})
        
    ## recieved something
    #####################
    def _recievedPosition(self):
        if self.scanning_flag:
            self.runPMT_Exposure()
            return
        else:
            self.user_run_flag = False
            
    def _recievedResult(self, x_pos, y_pos, pmt_count):
        # update GUI (image & progress)
        print("pos_list", self.x_pos_list)
        print("pos", x_pos)
        x_index = np.where(abs(self.x_pos_list - x_pos) < 0.001)[0][0]
        y_index = np.where(abs(self.y_pos_list - y_pos) < 0.001)[0][0]
        # print('x, y', x_index, y_index)
        self.image[x_index, y_index] = pmt_count
        if self.motors.device == "Dummy":
            self.image[x_index, y_index] = np.random.random()
        
        self.latest_count = pmt_count
        self.num_points_done += 1
        self._updatePorgressLabel()
        self.sig_update_plot.emit()
        
        # send new request
        if self.num_points_done < self.x_num * self.y_num:  # if scanning not finished
            # check if scanning is not paused
            if self.scanning_flag:
                self.keepScanning()
                return
        
        elif self.num_points_done == self.x_num * self.y_num:
            if self.CB_auto_go_to_max.isChecked():
                self.goToMax()
                return
                
        else:  # if scanning is done
            time.sleep(0.1)
            
        
        self.scanning_flag = False
        self.user_run_flag = False
        
        self.sequencer.occupant = ""
        self.sequencer.sig_occupied.emit(False)
        
        # saving image        
        self.image_handler.save_flag = True
        self.sig_update_plot.emit()
        self.toStatusBar("Completed scanning.")
        
        self._sendMail()
        
    def _setupScanRange(self, x_list=[0], y_list=[0]):
        # 
        # # update the variables related to the scan range
        self.x_pos_list = x_list
        self.y_pos_list = y_list
        
        self.x_num = len(self.x_pos_list)
        self.y_num = len(self.y_pos_list)
        self.image = np.zeros((self.x_num, self.y_num))
        
        # update PMT settings
        self.pmt_exposure_time_in_ms = self._getExposureTime()        
        # update scan_progress labels
        self.num_points_done = 0
        self.latest_count = 0
        # self._updatePorgressLabel()
        
        print("updated scan range: ", self.x_pos_list, self.y_pos_list, self.pmt_exposure_time_in_ms)
        
    def _updatePorgressLabel(self):
        self.LBL_latest_count.setText(str(self.latest_count))
        self.LBL_points_done.setText(str(self.num_points_done))
        self.LBL_total_points.setText(str(self.x_num * self.y_num))
        
    def _getExposureTime(self):
        try:
            pmt_exposure_time = int(self.LE_pmt_exposure_time_in_ms.text())
        except:
            pmt_exposure_time = self.pmt_exposure_time_in_ms
            self.toStatusBar("The exposure time must be an int.")
        
        return pmt_exposure_time
    
    def _setEnableObjects(self, flag):
        for obj in self.disable_list:
            obj.setEnabled(flag)
    
    def _create_canvas(self, frame):
        fig = plt.Figure(tight_layout=True)
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        
        layout = QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        frame.setLayout(layout)
        
        ax = fig.add_subplot(1,1,1)
        ax.tick_params(axis = 'x', labelrotation = 90)

        spine_list = ['bottom', 'top', 'right', 'left']
        
        if self._theme == "black":
            plt.style.use('dark_background')
            plt.rcParams.update({"savefig.facecolor": [0.157, 0.157, 0.157],
                                "savefig.edgecolor": [0.157, 0.157, 0.157]})
            
            fig.set_facecolor([0.157, 0.157, 0.157])
            ax.set_facecolor([0.157, 0.157, 0.157])
            ax.tick_params(axis='x', colors=[0.7, 0.7, 0.7], length=0)
            ax.tick_params(axis='y', colors=[0.7, 0.7, 0.7], length=0)
            
            im = ax.imshow(np.zeros((3,3)), cmap="inferno")
            colorbar = fig.colorbar(im, orientation="horizontal")
            colorbar.outline.set_edgecolor([0.7, 0.7, 0.7])
            colorbar.ax.xaxis.set_tick_params(color=[0.7, 0.7, 0.7])
            plt.setp(plt.getp(colorbar.ax.axes, 'xticklabels'), color=[0.7, 0.7, 0.7])

            for spine in spine_list:
                ax.spines[spine].set_color([0.7, 0.7, 0.7])

                
            for action in toolbar.actions():
                action_text = action.text()
                action.setIcon(QtGui.QIcon(os.path.dirname(dirname) + '/icons/%s.png' % action_text))
            
            
        elif self._theme == "white":
            plt.style.use('default')
            plt.rcParams.update({"savefig.facecolor": [1, 1, 1],
                                "savefig.edgecolor": [1, 1, 1]})
            fig.set_facecolor([1, 1, 1])
            ax.set_facecolor([1, 1, 1])
            ax.tick_params(axis='x', colors='k', length=0)
            ax.tick_params(axis='y', colors='k', length=0)
            
            im = ax.imshow(np.zeros((3,3)), cmap="viridis")
            colorbar = fig.colorbar(im, orientation="horizontal")
            
            for spine in spine_list:
                ax.spines[spine].set_color('k')
            toolbar.setStyleSheet("background-color:rgb(255, 255, 255);")
            
        return toolbar, ax, canvas, im
                
        
    ## Sequencer signals
    ####################
    def _setInterlock(self, occupied_flag):
        if occupied_flag:
            if not self.sequencer.occupant == "scanner":
                self._setEnableObjects(False)
        else:
            self._setEnableObjects(True)
            
                
    def _completeProgress(self):
        if self.user_run_flag:
            if self.scanning_flag:
                raw_pmt_count = np.asarray(self.sequencer.data[0]) # kind of deep copying...
                if len(raw_pmt_count) > 1:
                    pmt_count = np.mean(raw_pmt_count[:, 2])
                else:
                    pmt_count = raw_pmt_count[0][2]
                self._recievedResult(self.x_pos, self.y_pos, pmt_count)
                
                
    def _sendMail(self):
        if self.CHBOX_mail.isChecked():
            receiver = self.TXT_mail.text()
            self.mail.setExperimentName("PMT_scanner")
            self.mail.setReceiver(receiver)
            self.mail.connect()
            self.mail.sendMail()
            self.mail.disconnect()
            
            
    def _loadSaveFile(self, file_to_load):
        extension = file_to_load.split(".")[-1]
        if not extension in ["png", "PNG", "pkl"]:
            raise ValueError ("The file should be either png or pkl file.")
            
        else:
            if extension in ["png", "PNG"]:
                file_to_load = file_to_load[:-4] + '.pkl'
            with open (file_to_load, "rb") as fr:
                loaded_dict = pickle.load(fr)
                
            self.image = loaded_dict["img"]
            self.x_pos_list = loaded_dict["x_pos"]
            self.y_pos_list = loaded_dict["y_pos"]
            self.sig_update_plot.emit()
                
    
class ImageHandler(QThread):
    
    _sig_img_process_done = pyqtSignal()    
    
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.parent.sig_update_plot.connect(self.wakeupThread)
        
        # figures
        self.toolbar = self.parent.toolbar
        self.ax = self.parent.ax
        self.canvas = self.parent.canvas
        self.im = self.parent.im
        
        # running
        self.cond = QWaitCondition()
        self.mutex = QMutex()        
        self.status = "standby"
        
        self.save_flag = False
        
    def processImage(self):
        img = self.parent.image.T # This is "almost" equivalent to "deepcopy". no need to copy the image of parent.

        # flips
        if self.parent.CB_flip_horizontally.isChecked():
            img = np.flip(img, 1)
        if self.parent.CB_flip_vertically.isChecked():
            img = np.flip(img, 0)

        # show the image and the indices
        extent = np.array([self.parent.x_pos_list[0]  - self.parent.x_step/2,
                            self.parent.x_pos_list[-1] + self.parent.x_step/2,
                            self.parent.y_pos_list[-1] + self.parent.y_step/2,
                            self.parent.y_pos_list[0]  - self.parent.y_step/2]).astype(np.float16)
        if not self.parent.CB_auto_minmax.isChecked():
            my_vmin, my_vmax = float(self.parent.plot_min.text()), float(self.parent.plot_max.text())
        else:
            my_vmin, my_vmax = np.amin(img), np.amax(img)

        self.im.set_data(img)
        self.im.set_extent(extent)
        self.im.set_clim(my_vmin, my_vmax)
        
        self.ax.set_xticks(self.parent.x_pos_list)
        self.ax.set_yticks(self.parent.y_pos_list)
        
        self._sig_img_process_done.emit()
        
    def saveImage(self, filename='default'):
        """
        Since the error while saving the image should not block the scanning work, I used try and except.
        """
        try:
            save_dict = {"img": self.parent.image,
                         "x_pos": self.parent.x_pos_list,
                         "y_pos": self.parent.y_pos_list}
            if os.path.isfile(filename + ".pkl"):
                idx = 0
                while True:
                    if os.path.isfile(filename + "_%02d" % idx + ".pkl"):
                        idx += 1
                    else:
                        break
                filename = filename + "_%02d" % idx
                
            
            with open (filename + ".pkl", "wb") as fw:
                pickle.dump(save_dict, fw)
            
            time.sleep(0.5)
            self.parent.parent.grab().save(filename + ".png")
            # self.parent.toStatusBar("Completed scanning.")

        except Exception as e:
            self.parent.toStatusBar("An error while saving the image. (%s)" % e)
            
        self.save_flag = False
            
    def getHeader(self):
        header = """================================
                    Date: %s
                    Exposure Time in ms : %d
                    ================================
                 """ % (datetime.datetime.now().strftime("%y%m%d_%H:%M:%S"), self.parent.pmt_exposure_time_in_ms)
                 
        return header
    
    def wakeupThread(self):
        self.cond.wakeAll()
        
    def run(self):
        while True:
            self.mutex.lock()
            
            if not self.save_flag:
                self.status = "plotting"
                try:
                    self.processImage()
                except Exception as e:
                    print(e)
            else:
                self.status = "saving"
                directeory = self.parent.LE_save_file_dir.text()
                file_name = self.parent.LE_save_file_name.text()
                self.saveImage(directeory + "/" + file_name)
            
            self.status = "standby"
            self.cond.wait(self.mutex)
            self.mutex.unlock()

if __name__ == "__main__":
    pa = Scanner()
    pa.show()