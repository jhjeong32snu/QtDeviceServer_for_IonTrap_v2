"""
Created on Wed Sep 1 22:52:01 2021

@author: jhjeong
e-mail: jhjeong32@snu.ac.kr
Tel. 010-9600-3392
"""
from PyQt5.QtCore import QByteArray, QDataStream, QIODevice, pyqtSignal, QObject
from PyQt5.QtNetwork import QTcpServer, QHostAddress


class RequestHandler(QTcpServer):
    
    """
    RequestHandler handles multiple client connections.
    When a client tries to connect to this server, adds in the client_list and wraps it with MessageHandler.
    
    Note:
    - This class inherits QTcpServer as a base.
    - Most methods are overridden on our purpose, especially for handling client requets.
    """
    client_list = []
    
    def closeSession(self):
        for client in self.client_list:
            client.sendMessage(['C', 'DCN', []])
        self.close()

    def __init__(self, device_dict, logger=None):
        super().__init__()
        self.device_dict = device_dict
        self.logger = logger

    def openSession(self, address='local', port=55555):
        """
        Opens a session with user-defined port.
        If not assigned, the session will be opened through a port number 55555.
        
        It returns:
            -1: When failed to open the session.
            0: when the session is already being opened.
            1: When the session is successfully opened.
        """
        if self.isListening():
            print("Session already opened")
            return 0

        # If address is not 'local', the host address will be a user-defined IP address.
        if address == 'local':
            host = QHostAddress(QHostAddress.LocalHost)
        else:
            host = QHostAddress(address)

        # QTcpServer.listen(host, port) opens a session and starts listening requests.
        if self.listen(host, port) != True:
            print("Failed to open the session")
            return -1
        
        # When no error meets until this line. The session is successfully opened.
        self.newConnection.connect(self.createNewConnection)
        print("Server opened at (%s, %d)." % (host.toString(), port))
        return 1

    def createNewConnection(self):
        """
        Called whenever a new connection request arrives
        """
        client_connection = self.nextPendingConnection()
        new_client = MessageHandler(self, client_connection)
        new_client._sig_kill_me.connect(self.killSocket)
        self.client_list.append(new_client)
        print("Number of clients: %d." % len(self.client_list))
        self.toLog("info", "A new connection from (%s, %d)" % (new_client.socket.peerAddress().toString(), new_client.socket.peerPort()))

    def killSocket(self, user_name):
        for client in self.client_list:
            if client.user_name == user_name:
                for device in self.device_dict.values():
                    if client in device._client_list:
                        device._client_list.remove(client)
                self.client_list.remove(client)
                self.toLog("info", "A client (%s, %d) has been disconnected." % (client.socket.peerAddress().toString(), client.socket.peerPort()))
                break
            
    def poolDevice(self, msg):
        """
        It distrubutes the command following the request.
        """
        device = msg.pop(1)
        self.device_dict[device].toWorkList(msg)
        
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

class MessageHandler(QObject):
    """
    This class handles messages between server and client.
    The server creates this class for each client.
    
    To combat the unwanted crushes when more than one thread tries to send messages, I made a message queue
    When a new message has been added to the message queue, a fire signal is emitted and the MessageHandler sends the message one by one in the list.
    
    Note that the class is callable and returns the ip address of the client.
    
    - userName: User-defined nickname to be distinguished from other clients. this name is usually pre-defined in a user-config file.    
    - status: represents if it is sending messages or not.
              the emission of the fire signal will be ignored when the status is "sending" even if a new message has been added to the message queue.
              
    """    
    _sig_kill_me  = pyqtSignal(str)
    _msg_list = []
    _fire_signal = pyqtSignal()

    def __init__(self, parent, clientsocket):
        super().__init__()
        self.socket = clientsocket
        self.server = parent
        self.user_name = ""
        self.status = "standby"
        self.socket.readyRead.connect(self.receiveMessage)
        
        # privates
        self._name_duplicate = 0
        self._valid = True
        self._block_size = 0
        self._num_failure = 0
        self._address = self.socket.peerAddress().toString()
        self._port = self.socket.peerPort()
        self._fire_signal.connect(self.dealMessageList)
        
    def __call__(self):
        return self._address
        
    @property
    def address(self):
        return self._address
    
    @property
    def port(self):
        return self._port

    def sendMessage(self, msg):
        block = QByteArray()
        self.debugging_msg = msg
        output = QDataStream(block, QIODevice.WriteOnly)
        output.setVersion(QDataStream.Qt_5_0)
        # output.writeUInt16(0)
        output.writeUInt16(0)
        output.writeQString(msg[0])      ### flag C/D
        output.writeQString(msg[1])      ### device; 3 ~ 4 charaters
        output.writeQString(msg[2])      ### command of 3 or 4 characters
        output.writeQVariantList(msg[3]) ### data
        output.device().seek(0)
        output.writeUInt16(block.size()-2)
        res = self.socket.write(block)
        print(res)
        if res < 0:
            self._num_failure += 1
            if self._num_failure >= 10:
                self._sig_kill_me.emit(self.user_name)
        else:
            self._numFailure = 0
        # print("To the client(%s, %d):" % (self.socket.peerAddress().toString(), self.socket.peerPort()), msg)
        
    def toMessageList(self, msg):
        self._msg_list.append(msg)
        if self.status == "standby":
            self.status = "sending"
            self._fire_signal.emit()
        
    def dealMessageList(self):
        while len(self._msg_list):
            msg = self._msg_list.pop(0)
            self.sendMessage(msg)
        self.status = "standby"
        
    def receiveMessage(self):
        print("Received a message")
        stream = QDataStream(self.socket)
        stream.setVersion(QDataStream.Qt_5_0)

        while(self.socket.bytesAvailable() >= 2):
            print(self.socket.bytesAvailable())
            if self._block_size == 0:
                if self.socket.bytesAvailable() < 2:
                    return
                self._block_size = stream.readUInt16()
            if self.socket.bytesAvailable() < self._block_size:
                return
            control = str(stream.readQString())      ### flag C/D
            device  = str(stream.readQString())      ### device; 3 ~ 4 charaters
            command = str(stream.readQString())      ### command of 2 ~ 4 characters
            data = list(stream.readQVariantList())   ### data
            self._block_size = 0

            print("Received,", [control, device, command, data])
            if device == "SRV":
                if control =="C" and command == "CON":
                    self.user_name, self._name_duplicate = self.fixUserName(data[0])
                    self.toMessageList(["D", "SRV", "HELO", list(self.server.device_dict.keys())])
                    
                elif control =="C" and command == "DCN":
                    if self._name_duplicate == 0:
                        assert(self.user_name == data[0])
                    else:
                        assert(self.user_name[:-3] == data[0])
                    self._sig_kill_me.emit(self.user_name)
                    
            else:
                self.server.poolDevice([control, device, command, data, self])
            
    
    def fixUserName(self, user_name):
        flagDuplicate = True
        index = 0

        while flagDuplicate:
            flagDuplicate = False
            for client in self.server.client_list:
                if client != self and client.user_name == user_name:
                    flagDuplicate = True
                    index += 1
                    user_name = user_name + "(" + str(index) + ")"
        return user_name, index
    


if __name__ == "__main__":
    server = RequestHandler()
    # server.openSession()
    
# srv.rh.client_list[1].sendMessage("a")
# srv.rh.client_list[0].sendMessage(["D", "DAC", "SETV", ["E0:-2;E1:1;E15:-3"]]