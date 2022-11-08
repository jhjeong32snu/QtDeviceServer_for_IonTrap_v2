# -*- coding: utf-8 -*-
"""
Created on Wed Jul 14 22:52:01 2021

@author: CPO
v1.01: read a config file. compatible with EMCCD
"""
import os
os.system('CLS')

import time
import numpy as np
from datetime import datetime
from PIL import Image
from configparser import ConfigParser

from PyQt5 import uic

filename = os.path.abspath(__file__)
dirname = os.path.dirname(filename)

qt_designer_file = dirname + '/CCD_GUI_v2_01.ui'
Ui_Form, QtBaseClass = uic.loadUiType(qt_designer_file)

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QVBoxLayout, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal

import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from Libs.CCD_oven_v0_03 import Oven_controller

class CCD_UI_base:
    
    _img_cnt = 0
    
    _camera_type = "CCD"
    
    _slider_min = 0
    _slider_max = 0
    
    _im_min = 19
    _im_max = 216
    
    _zoom_in_flag = False
    _auto_save = False
    
    _theme = "white"    
    _theme_color = {
                    "white": {"main":   "",
                              "GBOX":   "",
                              "BTN_ON": "",
                              "BTN_OFF":"",
                              "LBL":    "background-color:rgb(180, 180, 180);",
                              "STATUS": "background-color:rgb(10, 10, 10); color:rgb(255, 255, 255);",
                              "TXT": "background-color:rgb(240, 240, 240); color:rgb(0, 0, 0);",
                              
                              "fig_face_color": "w",
                              "ax_face_color": "w",
                              "tick_color": "k",
                              "color_map": "gist_earth"
                              },
                    
                    "black": {"main":   "background-color:rgb(30,30,30); color:rgb(140, 140, 140);",
                              "GBOX":   "color:rgb(140, 140, 140);",
                              "BTN_ON" :"background-color:rgb(180, 50, 50);",
                              "BTN_OFF":"background-color:rgb(60, 60, 60);",
                              "LBL":    "background-color:rgb(0, 0, 0);",
                              "STATUS": "background-color:rgb(180, 180, 180); color:rgb(10, 10, 10);",
                              "TXT": "background-color:rgb(30,30,30); color:rgb(140, 140, 140);",
                              
                              "fig_face_color": [0.235, 0.235, 0.235],
                              "ax_face_color": [0.118, 0.118, 0.118],
                              "tick_color": [0.7, 0.7, 0.7],
                              "color_map": "afmhot"
                              }
        }
    
    _emccd_cooler_theme = {
                            "white": {"blue": "background-color:rgb(65, 150, 80)",
                                      "red": "background-color:rgb(150, 60, 140)"
                                      },
                            "black": {"blue": "background-color:rgb(0, 100, 20)",
                                      "red": "background-color:rgb(120, 40, 120)"
                                      }
        }
    
    
    _available_ccd = []
        
    
class CCD_UI(QtWidgets.QMainWindow, CCD_UI_base, Ui_Form):
    
    _closing = pyqtSignal(int)
        
    def closeEvent(self, e):
        self._closing.emit(1)
        self.oc.close_oven()
        self.cam.close_device()
        print("Released the camera")
        
    def showEvent(self, e):
        if not self.BTN_acquisition.isChecked():
            self.updatePlot()
    
    def __init__(self, controller=None):
        QtWidgets.QMainWindow.__init__(self)
        # cam
        self._readConfig(os.getenv('COMPUTERNAME', 'defaultValue'))
        self.cam = controller
        self.image_handler = self.cam.image_thread
        
        self.setupUi(self)
        self._init_params()

        # zoom
        self.zoom_x1 = 0
        self.zoom_y1 = 0
        self.zoom_x2 = self.cam._param_dict["SIZE"][1]
        self.zoom_y2 = self.cam._param_dict["SIZE"][0]

        # roi
        self.roi_x1 = 0
        self.roi_y1 = 0
        self.roi_x2 = self.cam._param_dict["SIZE"][1]
        self.roi_y2 = self.cam._param_dict["SIZE"][0]
        
        #
        self._initUi()
        self.CBOX_target.currentTextChanged.connect(self._changeChamber)
        
        # self.oc = Oven_controller(self)
        self.cam.image_thread._img_recv_signal.connect(self._countPlot)
        
        self._img_cnt = 0
        self.im_min = 0
        self.im_max = 0
        
        self.plot_handler = PlotHandler(self, self.cam, self.image_handler)
        self.plot_handler._sig_plot_update.connect(self.updatePlot)
        
        
    #%% Initialization
    def _initUi(self):
        pc_name = os.getenv('COMPUTERNAME', 'defaultValue')
        for chamber in self._available_ccd:
            self.CBOX_target.addItem("Chamber_%s" % chamber)
        self.CBOX_target.setCurrentText("Chamber_%s" % pc_name)
        
        self.LBL_ROI_x1.setText("%d" % (self.zoom_x1))
        self.LBL_ROI_x2.setText("%d" % (self.zoom_x2))
        self.LBL_ROI_y1.setText("%d" % (self.zoom_y1))
        self.LBL_ROI_y2.setText("%d" % (self.zoom_y2))
        
        self.BTN_save.setIcon(QtGui.QIcon(dirname + '/Libs/gui_save.ico'))
        self.BTN_oven_settings.setIcon(QtGui.QIcon(dirname + '/Libs/gui_settings.ico'))
        self._makePlot(self.CCD_image_label)
        
        # if self._camera_type == "CCD":
        #     self.NON_temp.setHidden(True)
        #     self.LBL_temp.setHidden(True)
        # else:
        #     self.LBL_temp.returnPressed.connect(self.CoolingOn)
        #     self._cooler_thread = Cooling_Thread(self)
        
    def _init_params(self):
        self.LBL_gain.setText(str(self.cam._param_dict["GAIN"]))
        self.STATUS_exp_time.setText(str(self.cam._param_dict["EXPT"]))
        self.cam.save_directory = self.LBL_directory.text()
        self._height, self._width = self.cam._param_dict["SIZE"]
                
    def _readConfig(self, pc_name):
        conf_file = dirname + '/config/%s.conf' % pc_name
        if not os.path.isfile(conf_file):
            print("No config file has been found.")
            return
        
        cp = ConfigParser()
        cp.read(conf_file)
        self._camera_type = cp.get('device', 'type')
        self._theme = cp.get('ui', 'theme')
        try:
            self._available_ccd = cp.get("server", 'avails').replace(' ', '').split(',')
        except:
            self._available_ccd = [pc_name]
        
    def _changeChamber(self, chamber_id):
        pc_name = chamber_id.split("_")[-1]
        self._readConfig(pc_name)
        self.changeTheme()
        
        
    def changeTheme(self, theme):
        self._theme = theme
        self.setStyleSheet(self._theme_color[self._theme]["main"])
        item_list = dir(self)
        for item in item_list:
            if "GBOX_" in item:
                getattr(self, item).setStyleSheet(self._theme_color[self._theme]["GBOX"])
            elif "BTN_" in item:
                getattr(self, item).setStyleSheet(self._theme_color[self._theme]["BTN_OFF"])
            elif "LBL_" in item:
                getattr(self, item).setStyleSheet(self._theme_color[self._theme]["LBL"])
            elif "STATUS_" in item:
                getattr(self, item).setStyleSheet(self._theme_color[self._theme]["STATUS"])
            elif "TXT_" in item:
                getattr(self, item).setStyleSheet(self._theme_color[self._theme]["TXT"])

        self.fig.set_facecolor(self._theme_color[self._theme]["fig_face_color"])
        self.ax.set_facecolor(self._theme_color[self._theme]["ax_face_color"])
        self.ax.tick_params(axis='x', colors=self._theme_color[self._theme]["tick_color"], length=0)
        self.ax.tick_params(axis='y', colors=self._theme_color[self._theme]["tick_color"], length=0)
        for spine in ['bottom', 'top', 'right', 'left']:
            self.ax.spines[spine].set_color(self._theme_color[self._theme]["tick_color"])
            
        # Colorbar color
        self.colorbar.ax.yaxis.set_tick_params(color=self._theme_color[self._theme]["tick_color"])
        self.colorbar.ax.tick_params(axis='y', colors=self._theme_color[self._theme]["tick_color"], length=3)
        self.colorbar.outline.set_edgecolor(self._theme_color[self._theme]["tick_color"])
            
        self.updatePlot()
        
    def _makePlot(self, frame):
        self.fig = plt.Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        
        layout = QVBoxLayout()
        layout.layoutLeftMargin = 0
        layout.layoutRightMargin = 0
        layout.layoutTopMargin = 0
        layout.layoutBottomMargin = 0
        layout.addWidget(self.canvas)
        frame.setLayout(layout)
        
        self._plot_im = np.zeros((self._height, self._width))
        
        self.ax = self.fig.add_subplot(1,1,1)
        self.im = self.ax.imshow(self._plot_im)
        self.colorbar = self.fig.colorbar(self.im, ax=self.ax)
        
        self.zoom_rs = RectangleSelector(self.ax, self.zoom_rs_callback, drawtype="box", button=[1], rectprops={"fill": False})
        self.zoom_rs.set_active(False)
  
        self.canvas.mpl_connect('button_release_event', self.on_release)

        
    def StartAcquisition(self, acq_flag):
        self._enableObjects(acq_flag)
        if acq_flag:
            self._img_cnt = 0
            
            self.cam.toWorkList(["C", "RUN", []])
            # if not self._image_thread.isRunning():
            #     self._image_thread.start()
            self.plot_handler.start()
            
        else:
            self.cam.toWorkList(["C", "STOP", []])
            
    def _enableObjects(self, flag):
        self.CBOX_target.setEnabled(not flag)
        self.CBOX_single_scan.setEnabled(not flag)
        self.CBOX_Autosave.setEnabled(not flag)
        
        if flag:
            self.BTN_acquisition.setStyleSheet(self._theme_color[self._theme]["BTN_ON"])
        else:
            self.BTN_acquisition.setStyleSheet(self._theme_color[self._theme]["BTN_OFF"])
            
    #%% Image Min & Max
    def ChangeMin(self):
        min_val = int(float(self.LBL_min.text()))

        if min_val < 0:
            min_val = 0
            
        self.LBL_min.setText(str(min_val))
        self.cam.d_min = min_val
        self._im_min = min_val
        
    def ChangeMax(self):
        max_val = int(float(self.LBL_max.text()))
            
        self.LBL_max.setText(str(max_val))
        self.cam.d_max = max_val
        self._im_max = max_val
        
    def MinSliderMoved(self, slider_val):
        min_val = int(float(self.LBL_min.text()))
        min_step = int(float(self.STATUS_min_unit.text()))
        
        new_min_val = int(min_val + (-1)**(slider_val < self._slider_min) * min_step)
        
        self._slider_min = slider_val
        self.LBL_min.setText(str(new_min_val))
        self.ChangeMin()
        
    def MaxSliderMoved(self, slider_val):
        max_val = int(float(self.LBL_max.text()))
        max_step = int(float(self.STATUS_max_unit.text()))
        
        new_max_val = int(max_val + (-1)**(slider_val < self._slider_max) * max_step)
        
        self._slider_max = slider_val
        self.LBL_max.setText(str(new_max_val))
        self.ChangeMax()
        
    def ROISet(self):
        try:
            # value_list = []
            for roi_pos in ["x1", "x2", "y1", "y2"]:
                roi_label = getattr(self, "LBL_ROI_%s" % roi_pos)
    
                value = int(roi_label.text())
                setattr(self, "zoom_" + roi_pos, value)
            #     value_list.append(value)
            
            
            # self.cam.toWorkList(["C", "ROI", [["x", "y"], [(value_list[0], value_list[1]), (value_list[2], value_list[3])]]])
            self.ZoomIn()
        except Exception as err:
            self.toStatusBar("ROI positions must be integers. (%s)" % err)
        
        
    #%% Gain
    def ChangeGain(self):
        gain = int(float(self.LBL_gain.text()))
        self.cam.toWorkList(["C", "GAIN", [gain]])
        
    #%% Save data
    def SelectFilepath(self):
        save_path = QFileDialog.getExistingDirectory(self, "Select Directory", "C:/", QFileDialog.DontUseNativeDialog)
        if save_path == "":
            pass
        else:
            self.LBL_directory.setText(save_path)
            self.cam.save_directory = save_path
            
    def SelectSavepath(self):
        save_file, _ = QFileDialog.getSaveFileName(self, 'Save File', "C:/", options=QFileDialog.DontUseNativeDialog)
        self.SaveImage(save_file)
            
    def SaveImage(self, save_name=""):
        if save_name == "":
            save_name = self.LBL_directory.text() + '/' + datetime.now().strftime("%y%m%d_%H%M_default")
        else:
            save_name = self.LBL_directory.text() + '/' + save_name
        
        if os.path.exists(self.AddExtention(save_name)):
            save_name += "_%03d"
            idx = 0
            while os.path.exists(self.AddExtention(save_name % idx)):
                idx += 1
            save_name = save_name % idx
        
        if self.CBOX_file_format.currentText() == "png":
            self.SavePNG( self.AddExtention(save_name) )
        else:
            self.SaveTIF( self.AddExtention(save_name) , True)
            
    def AddExtention(self, save_name):
        return save_name + ('.png' if self.CBOX_file_format.currentText() == "png" else '.tif')

    def ChangeFileFormat(self, file_format):
        self.cam.save_format = file_format
        
    def SetRecord(self, record_flag):
        self._auto_save = record_flag
        
    def SavePNG(self, save_name):
        png_arr = np.uint16(65535*(self._plot_im - self._im_min)/(self._im_max - self._im_min))
        img = Image.fromarray(png_arr)
        img.save(save_name, format="PNG")
        print("Saved %s" % save_name)
        
    def SaveTIF(self, save_name, stack=False):
        if stack:
            im_arr = []
            for arr in self.cam._buffer_list:
                im_arr.append( Image.fromarray(arr) )
            im_arr[0].save(save_name, format="tiff", save_all=True, append_images=im_arr[1:])
        else:
            im = Image.fromarray(self._plot_im)
            im.save(save_name, format='tiff')
        print("saved %s" % save_name)
        
    def SetScanLength(self):
        try:
            length = int(self.LBL_scan_length.text())
            self.LBL_scan_length.setText("%d" % length)
            self.cam.toWorkList(["C", "NTRG", [length]])
        except Exception as err:
            self.toStatusBar(err)
            
    def SetSinglescan(self, single_scan):
        if single_scan:
            self.cam.toWorkList(["C", "ACQM", ['single_scan']])
            if not int(self.LBL_scan_length.text()):
                self.LBL_scan_length.setText("1")
        else:
            self.cam.toWorkList(["C", "ACQM", ['continuous_scan']])
            
    def setFlip(self, flag):
        if self.sender() == self.CBOX_flip_horizontal:
            self.cam.toWorkList(["C", "FLIP", ["x", flag]])
        else:
            self.cam.toWorkList(["C", "FLIP", ["y", flag]])
            
    def toStatusBar(self, msg):
        self.statusBar.showMessage(msg)
        
    def toLog(self, msg):
        if not msg[1] == "\n":
            msg += "\n"
        self.TXT_log.insertPlainText(msg)
    
            
    #%% Mouse Interaction
    def ZoomIn(self):
        self._zoom_in_flag = True
        self.LBL_ROI_x1.setText(str(self.zoom_x1))
        self.LBL_ROI_x2.setText(str(self.zoom_x2))
        self.LBL_ROI_y1.setText(str(self.zoom_y1))
        self.LBL_ROI_y2.setText(str(self.zoom_y2))
        
        
        x_roi1, x_roi2 = self.zoom_x1, self.zoom_x2
        y_roi1, y_roi2 = self._height - self.zoom_y2, self._height - self.zoom_y1
        
        if self.CBOX_flip_horizontal.isChecked():
            x_roi1 = self._width - self.zoom_x2
            x_roi2 = self._width - self.zoom_x1
        if self.CBOX_flip_vertical.isChecked():
            y_roi1 = self.zoom_y1
            y_roi2 = self.zoom_y2
        
        self.cam.toWorkList(["C", "ROI", [["x", "y"], [(x_roi1, x_roi2), (y_roi1, y_roi2)]]])
        # self._plot_update()
            
    def ZoomOut(self):
        self._zoom_in_flag = False
        self.LBL_ROI_x1.setText(str(0))
        self.LBL_ROI_x2.setText(str(self._width))
        self.LBL_ROI_y1.setText(str(0))
        self.LBL_ROI_y2.setText(str(self._height))
        # self._plot_update()
        self.cam.toWorkList(["C", "ROI", [["x", "y"], [(0, self._width), (0, self._height)]]])
        
    def ClearDrawing(self):
        pass
        
#    def DrawRoi(self, idx, x, y, w, h):
#        self.delete_roi(idx)
#        rect = Rectangle((x, y), w, h, fill=False)
#        self.ax.add_patch(rect)
#        self.roi_list[idx] = rect
#        self.BTN_view_clear.setChecked(False)
#        self.canvas.draw()

#    def delete_roi(self, idx):
#        self.BTN_view_clear.setChecked(False)
#        if self.roi_list[idx] is not None:
#            self.roi_list[idx].remove()
#            self.roi_list[idx] = None
#            self.canvas.draw()

    def zoom_rs_callback(self, eclick, erelease):
        self.zoom_x1 = int(min(eclick.xdata, erelease.xdata))
        self.zoom_x2 = int(max(eclick.xdata, erelease.xdata))
        self.zoom_y1 = int(min(eclick.ydata, erelease.ydata))
        self.zoom_y2 = int(max(eclick.ydata, erelease.ydata))

        self.ZoomIn()

#    def _roi_rs_callback_maker(self):
#        def roi_rs_callback(eclick, erelease):
#            x = int(min(eclick.xdata, erelease.xdata))
#            y = int(min(eclick.ydata, erelease.ydata))
#            w = int(max(eclick.xdata, erelease.xdata)) - x
#            h = int(max(eclick.ydata, erelease.ydata)) - y
#
#            self.LBL_position1.setText("(%d,%d)" % (x, y))
#            self.LBL_position2.setText("(%d,%d)" % (w, h))
#        
#        return roi_rs_callback

    def on_release(self, event):
        
        if event.xdata == None or event.ydata == None:
            return
        x = int(round(event.xdata))
        y = int(round(event.ydata))
        
        if not (self.BTN_draw_rectangle.isChecked() and self.BTN_view_zoom.isChecked()):
            if self._zoom_in_flag:
                delta_x = self.zoom_x1
                delta_y = self.zoom_y1
               
            else:
                delta_x = 0
                delta_y = self._height
                
            pnt_y = delta_y - y
            pnt_x = x - delta_x
            
            # if self.CBOX_flip_horizontal.isChecked():
            #     pnt_x = self._width - pnt_x
            # if self.CBOX_flip_vertical.isChecked():
            #     pnt_y = self._height - pnt_y
            
            QtWidgets.QToolTip.showText(QtGui.QCursor().pos(),
                                        "x: {}\ny: {}\ncount: {}".format(x, y, self.im.get_array()[pnt_y][pnt_x]))
        self.BTN_view_zoom.setChecked(False)
        self.BTN_draw_rectangle.setChecked(False)
        return
        
    def ZoomActive(self, zoom_flag):
        self.zoom_rs.setactive(zoom_flag)
        
    def DrawActive(self, draw_flag):
        self.zoom_rs.set_active(draw_flag)
    
    def ChangeExposureTime(self):
        exp_time = float(self.STATUS_exp_time.text())
        self.cam.toWorkList(["C", "EXPT", [exp_time]])
        
    def _countPlot(self, raw_min, raw_max):
        self._img_cnt += 1
        
        if self.CBOX_single_scan.isChecked():
            if self._img_cnt == int(self.LBL_scan_length.text()):
                self._enableObjects(False)
                self.BTN_acquisition.setChecked(False)
                
    def updatePlot(self):
        if not self.isHidden():
            if self.CBOX_auto.isChecked():
                self.LBL_min.setText(str(self.im_min))
                self.LBL_max.setText(str(self.im_max))
                
            self.STATUS_raw_min.setText(str(self.image_handler.raw_min))
            self.STATUS_raw_max.setText(str(self.image_handler.raw_max))
    
            self.canvas.draw()
                            
    #%% for EMCCD
    def CoolingOn(self):
        target_temp = int(self.LBL_temp.text())
        if target_temp < 30:
            self.cam.cooler_on(target_temp)
            if not self._cooler_thread.isRunning():
                self._cooler_thread.running_flag = True
                self._cooler_thread.start()
            print("Cooler on.")
                
        else:
            self.cam.cooler_off()
            self._cooler_thread.running_flag = False
            self._cooler_thread.wait()
            print("Cooler off.")
            self.LBL_temp.setStyleSheet(self._theme_color[self._theme]["LBL"])
            
    # #%% For QTimer
    # def processImage(self):
    #     # self.ax.clear()
    #     self.im.set_data(self.image_handler.image_buffer)
        
    #     if self.CBOX_auto.isChecked():
    #         self.im_min = self.image_handler.raw_min
    #         self.im_max = self.image_handler.raw_max
    #     else:
    #         self.im_min = int(self.LBL_min.text())
    #         self.im_max = int(self.LBL_max.text())
        
    #     self.im.set_clim(self.im_min, self.im_max)
    #     self.im.set_cmap(self._theme_color[self._theme]["color_map"])
        
    #     if self._zoom_in_flag:
    #         extent = np.array([self.zoom_x1, self.zoom_x2,
    #                         self.zoom_y1, self.zoom_y2]).astype(np.float16)
    #     else:
    #         extent = np.array([0, self.cam._param_dict["SIZE"][1],
    #                            0, self.cam._param_dict["SIZE"][0]]).astype(np.float16)
    #     self.im.set_extent(extent)
        
    #     self.updatePlot()
            
        
class PlotHandler(QThread):
    
    _sig_plot_update = pyqtSignal()
    
    def __init__(self, parent=None, cam=None, image_handler=None):
        super().__init__()
        self.GUI = parent
        self.im = self.GUI.im
        
        self.cam = cam
        self.image_handler = image_handler        
        self.setMinimumInterval(0.12) # minimum update rate of the CCD image
        
        self.update_enbaled = True
        
    def setMinimumInterval(self, interval=0.1):
        self.minimum_interval = interval
        
    def run(self):
        while self.GUI.BTN_acquisition.isChecked():
            if self.update_enbaled:
                time.sleep(self.minimum_interval)
                # t1 = datetime.now()
                self.processImage()
                # t2 = datetime.now()
                
                # if (t2-t1) < self.timedelta:
                #     time.sleep( ((self.timedelta - (t2-t1)).microseconds/1e6) )
                
                self._sig_plot_update.emit()
                self.update_enabled = False
    
    def processImage(self):
        # self.ax.clear()
        self.im.set_data(self.image_handler.image_buffer)
        
        if self.GUI.CBOX_auto.isChecked():
            self.GUI.im_min = self.image_handler.raw_min
            self.GUI.im_max = self.image_handler.raw_max
        else:
            self.GUI.im_min = int(self.GUI.LBL_min.text())
            self.GUI.im_max = int(self.GUI.LBL_max.text())
        
        self.im.set_clim(self.GUI.im_min, self.GUI.im_max)
        self.im.set_cmap(self.GUI._theme_color[self.GUI._theme]["color_map"])
        
        if self.GUI._zoom_in_flag:
            extent = np.array([self.GUI.zoom_x1, self.GUI.zoom_x2,
                            self.GUI.zoom_y1, self.GUI.zoom_y2]).astype(np.float16)
        else:
            extent = np.array([0, self.cam._param_dict["SIZE"][1],
                               0, self.cam._param_dict["SIZE"][0]]).astype(np.float16)
        self.im.set_extent(extent)


        
class Cooling_Thread(QThread):
    
    def __init__(self, parent):
        super().__init__()
        self.GUI = parent
        self.cam = self.GUI.cam
        self.running_flag = False
        
    def run(self):
        while self.running_flag:
            if self.cam._cool_status == "cooling":
                self.GUI.LBL_temp.setStyleSheet(self.GUI._emccd_cooler_theme[self.GUI._theme]["red"])
            elif self.cam._cool_status == "stabilized":
                self.GUI.LBL_temp.setStyleSheet(self.GUI._emccd_cooler_theme[self.GUI._theme]["blue"])
                
            self.GUI.LBL_temp.setText(str(self.cam.temperature))
            time.sleep(3)
            if not self.GUI.BTN_acquisition.isChecked():
                self.GUI.update()
                
# class ImageTimer(QTimer):
    
#     def __init__(self, parent=None, ):
        
#     def run(self):
        
        
#     def processImage(self):
#         # self.ax.clear()
#         self.im.set_data(self.GUI._plot_im)
#         self.im.set_clim(self.GUI._im_min, self.GUI._im_max)
#         self.im.set_cmap(self.GUI._theme_color[self.GUI._theme]["color_map"])
        
#         if self.GUI._zoom_in_flag:
#             extent = np.array([self.GUI.zoom_x1, self.GUI.zoom_x2,
#                             self.GUI.zoom_y1, self.GUI.zoom_y2]).astype(np.float16)
#         else:
#             extent = np.array([0, self.controller._param_dict["SIZE"][1],
#                                0, self.controller._param_dict["SIZE"][0]]).astype(np.float16)
#         self.im.set_extent(extent)
    
    
if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    CCD = CCD_UI(instance_name='QuIQCL_CCD_v1.02')
    CCD.setWindowTitle('QuIQCL_CCD_v1.02')
    CCD.show()

#CCD.cam._thor_cam.set_trigger_count(10)
#CCD.cam._buffer_size = 10