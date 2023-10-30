"""
Created on Sun Nov 21 2021
@author: Junho Jeong
"""
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from motor_handler import MotorHandler
version = "2.1"
qtimer_interval = 500 # ms

class MotorController(QObject):
    """
    The controller class uses QThread class as a base, handling commands and the device is done by QThread.
    This avoids being delayed by the main thread's task.
    
    The logger decorate automatically record the exceptions when a bug happens.
    """
    _client_list = []
    _status = "standby"
    _motors = {}
    _is_opened = False
    _motors_under_request = []
    _motors_under_homing  = []
    _motors_under_loading = []
    
    _sig_motors_initialized = pyqtSignal(int, int, str)
    _sig_motors_positions = pyqtSignal(dict)
    
    def __init__(self, parent=None, gui=None):  # cp is ConfigParser class
        super().__init__()
        self.parent = parent
        self.cp = self.parent.cp
        self.gui = gui
        self.motor_dict = {}

        # Setting motor initiator
        self.device = self.cp.get("device", "motors")
        self._motors = self._getMotorDictToLoad()
        
        self.pos_checker = QTimer() # This emits position signals of currently moving motors in 0.5s interval.
        self.pos_checker.setSingleShot(True)
        self.pos_checker.timeout.connect(self.announcePositionsUnderMoving)
        
        print("Motor Controller v%s" % version)
        
    # def openGui(self):
    #     from Motor_Controller_GUI import MotorController_GUI
    #     self.gui = MainWindow(controller=self)
    #     self._gui_opened = True

    def _receiveMotors(self, motor_dict):
        for nickname, motor in self._motors.items():
            self._positions[nickname] = motor.position
            
    def _getMotorDictToLoad(self):
        motor_dict = {}
        mtype = self.cp.get("motors", "motor_type")
        
        for option in self.cp.options("motors"):
            if "_serno" in option:
                nickname = option[:option.find("_serno")]
                serno = self.cp.get("motors", option)
                
                motor_dict[nickname] = self._addMotor(self, serno, mtype, nickname)
                
        return motor_dict
    
    def _addMotor(self, serno, dev_type, nickname):
        motor = MotorHandler(self, serno, dev_type=dev_type, nick=nickname)
        
        motor._sig_motor_initialized.connect(self._initializedMotor)
        motor._sig_motor_move_done.connect(self._completedMotorMoving)
        motor._sig_motor_error.connect(self._errorReported)
        motor._sig_motor_homed.connect(self._homedMotor)
        
        return motor
        
    def _removeMotor(self, nickname):
        if nickname in self._motors.keys():
            self._motors[nickname].closeDevice()
            self._motors.pop(nickname)
    
    def _initializedMotor(self, nick):
        self._motors_under_loading.remove(nick)
        self._sig_motors_initialized.emit(len(self._motors_under_loading), nick)  # Let applications know how many motors are left.
    
    def getPosition(self, nickname):
        return self._motors[nickname].getPosition()
    
    def moveToPosition(self, data_dict):
        for motor_nick, target_position in data_dict.items():
            self._motors[motor_nick].setTargetPosition(target_position)
            self._motors[motor_nick].toWorkList("M")
            self._motors_under_request.append(motor_nick)
            
        self.pos_checker.start(qtimer_interval) # Let the clients know the positions while moving.

        
    def _completedMotorMoving(self, nick, position):
        self._motors_under_request.remove(nick)
    
    def openDevice(self, motor_list):
        self._sig_motors_initialized.emit(len(motor_list), "")  # Let applications know how many motors to be open.
        for m_idx, m_nick in enumerate(motor_list):
            self._motors[m_nick].toWorkList("O")
            self._motors_under_loading.append(m_nick)


    def closeDevice(self, motor_list):
        for m_idx, m_nick in enumerate(motor_list):
            self._motors[m_nick].toWorkList("D")

    def _homedMotor(self, nick):
        self._motors_under_homing.remove(nick)
            
    def homeDevice(self, motor_list):
        for m_idx, m_nick in enumerate(motor_list):
            self._motors[m_nick].toWorkList("H")
            self._motors_under_homing.append(m_nick)
            
    def announcePositionsUnderMoving(self):
        if len(self._motors_under_request):
            position_dict = {}
            for m_nick in self._motors_under_request:
                position_dict[m_nick] = self._motors[m_nick].getPosition()
                
            self._sig_motors_positions.emit(position_dict)
            self.pos_checker.start(qtimer_interval)
            
            print(position_dict)
        
            
    def toGUI(self, msg):
        if not self.gui == None:
            self.gui.toStatus(msg)
        else:
            print(msg)
            
