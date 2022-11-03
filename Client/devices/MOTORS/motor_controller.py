"""
Created on Sun Nov 21 2021
@author: Jaeun Kim
based on the Controller class template by Junho Jeong
"""
from PyQt5.QtCore import QThread, pyqtSignal, QWaitCondition, QMutex
from queue import Queue
from motor_handler import MotorHandler
version = "1.1"

class MotorController(QThread):
    """
    The controller class uses QThread class as a base, handling commands and the device is done by QThread.
    This avoids being delayed by the main thread's task.
    
    The logger decorate automatically record the exceptions when a bug happens.
    """
    _positions = {}
    _homing_timestamps = {}
    _client_list = []
    _status = "standby"
    _motors = {}
    _is_opened = False
    _motors_under_request = {}
    
    _sig_motor_initialized = pyqtSignal(int, int, str)
    _sig_motor_finished_loading = pyqtSignal()
    
    def __init__(self, socket=None, logger=None):  # cp is ConfigParser class
        super().__init__()
        self.parent = socket
        self.queue = Queue()
        self.cp = self.parent.cp
        self.logger = logger

        # Setting motor initiator
        self.device = self.cp.get("device", "motors")
        self._motors = self._getMotorDictToLoad()
        
        print("Motor Controller v%s" % version)

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
                motor_dict[nickname] = MotorHandler(self, serno, dev_type=mtype, nick=nickname)
                motor_dict[nickname]._sig_motor_move_done.connect(self._completedMotorMoving)
                
        return motor_dict
    
    def _completedMotorLoading(self):
        self._receiveMotors(self._motors)
        self._is_opened = True
        self._sig_motor_finished_loading.emit()
        
    def _completedMotorMoving(self):
        self._motors_under_request[self.sender().nickname] = True
        t = True
        for val in self._motors_under_request.values():
            t = t & val
        if t:
            self.announcePositions(list(self._motors_under_request.keys()), self._client_list)
        
            
    def logger_decorator(func):
        """
        It writes logs when an exception happens.
        """
        def wrapper(self, *args):
            try:
                func(self, *args)
            except Exception as err:
                if not self.logger == None:
                    self.logger.error("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
                else:
                    print("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
        return wrapper
    
    @logger_decorator
    def openDevice(self, motor_list):
        print("start opening")
        self.motor_initiator = OpenThread(self, self.device)
        self.motor_initiator.finished.connect(self._completedMotorLoading)

        motor_dict = {nickname: self._motors[nickname] for nickname in motor_list}
        
        self.motor_initiator.setMotorDict(motor_dict)
        self.motor_initiator.start()
           
    @logger_decorator
    def closeDevice(self, motor_dict={}):
        if not len(motor_dict):
            motor_dict = self.motor_dict
        for key, val in motor_dict.items():
            val.closeDevice()
            print("Closed motor(%s)" % key)

    @logger_decorator    
    def toWorkList(self, cmd):
        client = cmd[-1]
        if not client in self._client_list:
            self._client_list.append(client)
            
        self.queue.put(cmd)
        if not self.isRunning():
            self.start()
            
    @logger_decorator          
    def run(self):
        while True:
            work = self.queue.get()
            self._status  = "running"
            # decompose the job
            work_type, command = work[:2]
            client = work[-1]    
    
            if work_type == "C":
                if command == "MOVE":
                    data = work[2]  # {motor_nickname: position_in_mm}
                    nickname_list = data[0::2]
                    position_list = data[1::2]
                    position_dict = dict(zip(nickname_list, position_list))
                    
                    self.moveToPosition(position_dict)
                    self._motors_under_request = {key: False for key in nickname_list}
                    
                    # Let all clients know that the positions are updated.
                    #self.announcePositions(nickname_list, self._client_list)
                    
                elif command == "OPEN":
                    nickname_list = work[2]
                    self.openDevice(nickname_list)
                    
                elif command == "CON":
                    """
                    When a client is connected, send position data to the client.
                    """
                    print("connected to %s" % client)
                    self._client_list.append(client)
                    client.toMessageList(["D", "MTR", "HELLO", []])
                    self.announcePositions(list(self._motors.keys()), client)
                    
                elif command == "DCN":
                    """
                    When a client is disconnected, terminate the client and close the device if no client left.
                    """
                    if client in self._client_list:
                        self._client_list.remove(client)
                        
                    if not len(self._client_list):
                        for motor in self._motors.values():
                            motor.closeDevice()

                elif command == "HOME":
                    """
                    Perform forced homing and record the timestamp
                    """
                    data = work[2]  # [motor_nickname1, motor_nickname2, ...]
                    if type(data) != list:
                        data = [data]

                    for motor_nickname in data:
                        self._motors[motor_nickname].home()

            elif work_type == "Q":
                if command == "POS":
                    data = work[2]
                    self.announcePositions(data, client)
                        
            else:
                self.toLog("critical", "Unknown work type (\"%s\") has been detected." % work_type)
            self._status = "standby"
            

    @logger_decorator
    def moveToPosition(self, data):
        for motor_nickname, target_position in data.items():
            self._motors[motor_nickname].moveToPosition(target_position)
            self._positions[motor_nickname] = self._motors[motor_nickname].position
            

    @logger_decorator
    def announcePositions(self, motor_list, client):
        data = []
        for motor_nickname in motor_list:
            data.append(motor_nickname)
            data.append(self._motors[motor_nickname].position)
            
        message = ["D", "MTR", "POS", data]
        self.informClients(message, client)

    @logger_decorator
    def informClients(self, msg, client):
        if type(client) != list:
            client = [client]
        
        self.informing_msg = msg
        for clt in client:
            clt.toMessageList(msg)
         
    def toLog(self, log_type, log_content):
        if not self.logger == None:
            if log_type == "debug":
                self.logger.debug(log_content)
            elif log_type == "info":
                self.logger.info(log_content)
            elif log_type == "warning":
                self.logger.warning(log_content)
            elif log_type == "error":
                self.logger.error(log_content)
            else:
                self.logger.critical(log_content)
        else:
            print(log_type, log_content)
            
            
class OpenThread(QThread):
    
    _motors = {}
    
    def __init__(self, parent=None, device="Dummy"):
        super().__init__()
        self.parent = parent
        self._sig_motor_initialized = parent._sig_motor_initialized
        self.device = device
        
        self.cond = QWaitCondition()
        self.mutex = QMutex()
        
    def setMotorDict(self, motor_dict):
        self._motors = motor_dict
    
    def wakeupThread(self):
        self.cond.wakeAll()
        
    def run(self):
        max_idx = len(self._motors)
        self._sig_motor_initialized.emit(0, max_idx)
            
    
        for motor_idx, nickname in enumerate(self._motors.keys()):
            self.mutex.lock()

            try:
                if not self._motors[nickname]._is_opened:
                    self._motors[nickname]._sig_motor_initialized.connect(self.wakeupThread)
                    self._motors[nickname].openDevice()
                    self.cond.wait(self.mutex)
                else:
                    print("Motor(%s) is alreaday opened." % nickname)
                
            except Exception as e:
                print("An error while the initiator opens a motor %s. (%s)" % (nickname, e))

            self._sig_motor_initialized.emit(motor_idx+1, max_idx, nickname)
            self.mutex.unlock()
