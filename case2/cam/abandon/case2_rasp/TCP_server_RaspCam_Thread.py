# TCP camera server always on. If receive a 'start' message from client, 
# turn on the camrea for 15s. If received a 'end' message to stop the cam, 
# stop it immediately. After recording send the cam active duration, 
# camID and timestamp for receiving the last 'start' message to edge.

import socket
import picamera
import time
from multiprocessing import Process, Value

recordingTime = 15
CamName = 'Cam2'

def TCP_Server(REC_start,REC_start_time_in):
  
  # host = '169.234.18.14' 
  # host = '169.234.39.209'
  host = 'localhost'        
  port = 22345     # Arbitrary non-privileged port
  TCPserverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  TCPserverSocket.bind((host, port))
  
  print host , port
  TCPserverSocket.listen(0)
  
  while True:
    connection, address = TCPserverSocket.accept()
    print('Connected by', address)
    try:
      data = connection.recv(1024)
      print "Client Says: "+data
      connection.sendall('Server Say: Message Received')
      
      # Flag for starting recording 
      if data[0:5] == 'Start':
        REC_start.value = 1
        REC_start_time_in.value = float(data[22:])
        print '[socket] REC_start = %s' %REC_start.value
        print '[socket] REC_start at = %s' %REC_start_time_in.value

      # Flag for ending recording
      if data[0:3] == 'End':
        REC_start.value = 2
        print '[socket] REC_start = %s' %REC_start.value 
      
      time.sleep(0.1)

    except socket.error:
      print "Error Occured."
      break
  
    connection.close()   

def Camera_Operation(REC_start,REC_duration,REC_start_time_in,REC_start_time_out):

  print '[Cam] REC_start = %s' %REC_start.value
  initialTime = time.time()
  
  REC_NUM = 1
  camera = picamera.PiCamera()
  
  while True:
    
    Cam_activation = 0       
    
    if REC_start.value == 1: #Start Recording
      REC_start.value = 0
      REC_start_time_out.value = REC_start_time_in.value
      
            
      print 'Camera recording start'
      # camera.start_preview()
      camera.start_recording('video'+str(REC_NUM)+'.h264') 
      REC_NUM = REC_NUM + 1  
      ini_time = time.time()
      ini_time_fixed = ini_time
      curr_time = ini_time 
      
      # record for several second
      while curr_time - ini_time <= recordingTime:
        Cam_activation = 1 
        curr_time = time.time()
        print 'REC: %s' %(curr_time - ini_time_fixed)
        
        if REC_start.value == 1:
          REC_start.value = 0
          ini_time = curr_time
          print 'Continue Recording'        
        
        if REC_start.value == 2:
          REC_start.value = 0
          print 'Move to Another Camera'
          break        
        
        time.sleep(0.05)
                
      print 'Stop Recording'
      REC_duration.value = curr_time - ini_time_fixed 
      TCP_Client(REC_start_time_out,REC_duration,REC_start_time_in)
      camera.stop_recording()
      # camera.stop_preview()  
      

def TCP_Client(REC_start_time_out,REC_duration,REC_start_time_in):
  # host = '169.234.0.236'  # pi02
  EdgeHost = 'localhost' # Edge host
  # host = '169.234.25.60' # pi 03

  port = 12000  # The same port as used by the server
  
  Previous_duration = REC_duration.value
  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((EdgeHost, port))
  message = str(REC_start_time_out.value) + '    ' + str(REC_duration.value) + '    ' + CamName + '    ' + str(REC_start_time_in.value)
  s.sendall(message)
  s.close()
  Previous_duration = REC_duration.value
  print 'Sent Video start time %s and duration %s To Edge' %(REC_start_time_out.value,REC_duration.value) 
               
               
               
               
if __name__ == '__main__':
    REC_start = Value('i', 0)
    REC_start_time_in = Value('d', 0.0)
    REC_start_time_out = Value('d', 0.0)
    REC_duration = Value('d', 0.0)
    
    p1 = Process(target=TCP_Server, args=(REC_start,REC_start_time_in))
    p2 = Process(target=Camera_Operation, args=(REC_start,REC_duration,REC_start_time_in,REC_start_time_out))
    
    p1.start()
    p2.start()
    p1.join()
    p2.join()
