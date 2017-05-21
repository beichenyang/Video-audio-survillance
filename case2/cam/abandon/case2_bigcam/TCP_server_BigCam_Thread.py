# TCP camera server always on. If receive a 'start' message from client, 
# turn on the camrea for 15s. If received a 'end' message to stop the cam, 
# stop it immediately. After recording send the cam active duration, 
# camID and timestamp for receiving the last 'start' message to edge.

import socket
import time
import thread
from multiprocessing import Process, Pipe, Lock, Value
import numpy as np
import cv2

recording_time = 15
CamID = 'Cam1'

def TCP_Server(REC_start,REC_start_time_in):
  
  # host = '169.234.18.14' 
  host = 'localhost'  # local host pi 05      
  port = 12445     # Arbitrary non-privileged port
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
      
      # Flag for ending recording
      if data[0:3] == 'End':
        REC_start.value = 2
        print '[socket] REC_start = %s' %REC_start.value 
      
    except socket.error:
      print "Error Occured."
      break
  
    connection.close()    
 
         

def Camera(REC_start,REC_duration,REC_start_time_in,REC_start_time_out):
  print '[Cam] REC_start = %s' %REC_start.value
  thefile = open('Cam_act.txt', 'w')
  initialTime = time.time()
  
  while True:    
    # print '[Cam] REC_start = %s' %REC_start.value
    Cam_activation = 0
    currentTime = time.time()
    timeStamp = currentTime - initialTime
    thefile.write("%s  %s\n" % (Cam_activation, timeStamp))
    
    if REC_start.value == 1:
      REC_start.value = 0
      REC_start_time_out.value = REC_start_time_in.value
      	
      print 'Camera recording start'
      cap = cv2.VideoCapture(0)
      # Define the codec and create VideoWriter object
      fourcc = cv2.VideoWriter_fourcc(*'XVID')
      out = cv2.VideoWriter('output.avi',fourcc, 20.0, (640,480))
      ini_time = time.time()
      ini_time_fixed = ini_time
      curr_time = ini_time
    
      while(cap.isOpened()):

        Cam_activation = 1
        currentTime = time.time()
        timeStamp = currentTime - initialTime
        thefile.write("%s  %s\n" % (Cam_activation, timeStamp))

        ret, frame = cap.read()
        if ret==True:
          frame = cv2.flip(frame,0)

          # write the flipped frame
          out.write(frame)

          cv2.imshow('frame',frame)
          curr_time = time.time()
          
          if REC_start.value == 1:
            REC_start.value = 0
            ini_time = curr_time
            print 'Continue Recording'    
          
          if curr_time - ini_time > recording_time: 
            print 'Finish Recording'
            REC_duration.value = curr_time - ini_time_fixed 
            break 

          if REC_start.value == 2:
            REC_start.value = 0
            print 'Stop Recording & Move to Another Camera'
            REC_duration.value = curr_time - ini_time_fixed
            break

          else:
            print curr_time - ini_time_fixed                
        else:
          break

      # Send time stamp and duration message to edge
      TCP_Client_CamDurationMsg(REC_start_time_out,REC_duration,REC_start_time_in)
      # Release everything if job is finished
      cap.release()
      out.release()
      cv2.destroyAllWindows()
      
    if cv2.waitKey(1) & 0xFF == ord('q'):
      thefile.close()
      break      

def TCP_Client_CamDurationMsg(REC_start_time_out,REC_duration,REC_start_time_in):
  # host = '169.234.0.236'  # pi02
  edgeHost = 'localhost' # Edge host
  # host = '169.234.25.60' # pi 03

  port = 12000                   # The same port as used by the server
  
  Previous_duration = REC_duration.value
  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((edgeHost, port))
  message = str(REC_start_time_out.value) + '    ' + str(REC_duration.value) + '    ' + CamID + '    ' + str(REC_start_time_in.value)
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
    p2 = Process(target=Camera, args=(REC_start,REC_duration,REC_start_time_in,REC_start_time_out))
    
    p1.start()
    p2.start()
    p1.join()
    p2.join()
