import cv2
import socket
from numpy import frombuffer
import threading
class VideoStream():
    def __init__(self,socket_name=None,stream_node="server",peering_name=None,cam_url=None,RECVED_MAX_BYTES=65472,title=None):
        self.title=title
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(socket_name)
        self.RECVED_MAX_BYTES=RECVED_MAX_BYTES
        self.cap = cv2.VideoCapture(0)
        self.recv_frame_dim =3
        if cam_url != None and isinstance(cam_url,str):
            self.cap.open(cam_url)
        if stream_node == "server":
            self.socket.listen()
            self.socket,addr=self.socket.accept()
            self.socket.send(b'done')
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
        elif stream_node == "client":
            self.socket.connect(peering_name)
            if self.socket.recv(4).decode() != "done":
                print("Connection Failed")
                exit()
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
                while (seg - 1) > 0:
                    if seg == 2:
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
                try:
                    self.socket.send(bytes(str(int(len(frame)/self.RECVED_MAX_BYTES)+1).encode())+ b"/" + frame)
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