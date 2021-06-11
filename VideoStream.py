import cv2
import socket
from numpy import frombuffer
import threading

class VideoStream():
    def __init__(self,socket_name=None,stream_mode="accepter",peering_name=None,cam_url=None,RECVED_MAX_BYTES=65470,title=None,cam_index=0):
        """
        socket_name      :   
                It's must be tuble. First element of this variable of this property must be IP and Second Port Number . Use empty string                     instead of IP is you want to dynamically attach current IP of system . This required property .User have 
        stream_mode      :
                stream_mode will tell that system will work as accepter ( who will accept the Video Chat Request) or initiator ( who will                   initiate the request for Video Chat) . This property value can be either "accepter" or "initiator" . By Default value of                     this is "accepter".
        peering_name     :
                This is required when stream_mode is "initiator" . This will tell to initiator that on which endpoint it will connect.
        cam_url          :
                This property will used when if Camera is on remote destination then You have to give the URL for that camera .
        RECVED_MAX_BYTES :
                recv() method in TCP socket programming only receive limited data at a time according to their buffer size. This will set                   buffer size for recv() method . By default 65472
        title            :
                When cv2.imshow() open a windows then this method take first argument for title of that window
        cam_index        :
                This property will tell us which camera you want to use (Internal or External) . To use Internal camera this property value                 must be 0 and to use external camera this property value must be 1 .
                Internal --->  0
                External --->  1
                This property has by default value 0
        """
        self.cam_index=cam_index
        self.title=title
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(socket_name)
        self.RECVED_MAX_BYTES=RECVED_MAX_BYTES
        # Take Camera Reference 
        self.cap = cv2.VideoCapture(self.cam_index)
        # Image Dimension
        self.recv_frame_dim =3
        if cam_url != None and isinstance(cam_url,str):
            self.cap.open(cam_url)
        if stream_mode == "accepter":
            self.socket.listen()
            self.socket,addr=self.socket.accept()
            self.socket.send(b'done')
            # Now it will check connection with transfer some data
            # If connection is good then here image shape also be shared
            if self.socket.recv(4).decode() != "done":
                print("Connection Failed")
                exit()
            photo=self.cap.read()[1]
            if len(photo) !=0:
                shape=photo.shape
                self.socket.send(bytes("{0} {1}".format(shape[0],shape[1]).encode()))
                co_ordinates = self.socket.recv(10).decode().split(" ")
                self.recv_frame_column = int(co_ordinates[0])
                self.recv_frame_row = int(co_ordinates[1])
            else:
                print("Camera not connected")
        elif stream_mode == "initiater":
            self.socket.connect(peering_name)
            if self.socket.recv(4).decode() != "done":
                print("Connection Failed")
                exit()
            # Now it will check connection with transfer some data
            # If connection is good then here image shape also be shared
            self.socket.send(b'done')
            co_ordinates = self.socket.recv(10).decode().split(" ")
            self.recv_frame_column = int(co_ordinates[0])
            self.recv_frame_row = int(co_ordinates[1])
            photo=self.cap.read()[1]
            if len(photo) !=0:
                shape=photo.shape
                self.socket.send(bytes("{0} {1}".format(shape[0],shape[1]).encode()))
            else:
                print("Camera not connected")
    
    def recvVideo(self):
        while True:
            frame = b''
            try:
                datapayload=self.socket.recv(self.RECVED_MAX_BYTES).split(b"/")
                seg = int(datapayload[0].decode())
                frame = frame + b"/".join(datapayload[1:])
                seg -= 1
                while (seg) >= 1:
                    if seg == 1:
                        frame_segment_payload=self.socket.recv((self.recv_frame_column*self.recv_frame_row*self.recv_frame_dim)-len(frame))
                    else:
                        frame_segment_payload=self.socket.recv(self.RECVED_MAX_BYTES)
                    frame += frame_segment_payload
                    seg -= 1
            except ConnectionResetError:
                print("Connection Lose")
                exit()
            cv2.imshow(self.title,frombuffer(frame,dtype='uint8').reshape(self.recv_frame_column,self.recv_frame_row,3))
            if cv2.waitKey(10) ==13:
                break
        cv2.destroyAllWindows()
        self.cap.release()
        
    def sendVideo(self):
        while True:
            returnCode , photo = self.cap.read()
            if returnCode and len(photo) != 0:
                frame = photo.tobytes()
                # No of segments ->  int(len(frame)/self.RECVED_MAX_BYTES)+1
                seg = len(frame)/self.RECVED_MAX_BYTES
                if seg != int(seg):
                    seg = int(seg) + 1
                try:
                    self.socket.send(bytes(str(seg).encode())+ b"/" + frame)
                except ConnectionResetError:
                    print("Connection Lose")
                    exit()
            else:
                print("Camera can't read")
                self.cap.release()
                exit()
                
    def startVideo(self):
        try:
            threading.Thread(target=self.sendVideo,args=()).start()
            threading.Thread(target=self.recvVideo,args=()).start()
        except ConnectionResetError:
            print("Connection Lose")
            exit()