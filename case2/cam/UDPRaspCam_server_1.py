# UDPRaspcam_server V0.0.1: Get data from clould, decode 
# those data by opuslib, then measure time and volume and store them. 
# If abnormal volume detected, turn on camera based on location
# sotre pervious location and current location, if location change, 
# switch camera. Edge will keep a timer for when to active camera, and 
# the camera will give camera actual active time delta back to edge.
# Edge will also keep a list of time for when rec start

import socket
from socket import AF_INET, SOCK_DGRAM
import pyaudio
import wave
import sys
import select
import audioop
import numpy
import time
from opuslib import classes
from multiprocessing import Process, Value, Pipe
import picamera

CamID = 'Cam2'
recording_duration = 15



# -----------------------  UDP server part ---------------------------#

def UDP_Server_Audio(timeFlag,videoRecStartTime,child_CamActMsgConn):
  # Audio parameter
  CHUNK = 960
  SOCK_CHUNK = 960
  FORMAT = pyaudio.paInt16
  CHANNELS = 1
  RATE = 16000
  WAVE_OUTPUT_FILENAME = "output"
  WAVE_OUTPUT_NUMBER = 1

  # creat a audio stream
  p = pyaudio.PyAudio()
                
  # Create a TCP/IP socket
  sock = socket.socket(AF_INET, SOCK_DGRAM)
  dec = classes.Decoder(RATE,CHANNELS)

  # Bind the socket to the port, local host
  #server_address = ('localhost', 10000)
  server_address = ('10.15.20.15', 10000)

  print >>sys.stderr, 'starting up on %s port %s' % server_address
  sock.bind(server_address)

  # time_ini_ = time.time()

  while True:
    frames = []
    volumeFile = open(WAVE_OUTPUT_FILENAME + str(WAVE_OUTPUT_NUMBER) + ".txt", 'w')
    delayFile = open(WAVE_OUTPUT_FILENAME + str(WAVE_OUTPUT_NUMBER) + "_delay.txt", 'w')
    flag = False
    sock.settimeout(None)
    Location = ''
  
    try:
      print >>sys.stderr, '\nwaiting to receive message'
      data, address = sock.recvfrom(SOCK_CHUNK)
      time_ini_ = time.time()
      previousTime = 0
      print >>sys.stderr, 'received %s bytes from %s' % (len(data), address)
      sock.settimeout(5)
      Previous_Location = data[4:13]
    
      while data:
        # pkt size 
        pkt_size = len(data)
                
        # Read prefix
        MicName = data[0:4]
        Location = data[4:13]
        sequenceNumber = data[13:17]
      
        # Read encoded data part
        encodeData = data[17:]
        decodeData = dec.decode(encodeData,CHUNK)
      
        # Compute Volume & delay by frame 
        rms = audioop.rms(decodeData,2)
        volume = 20*numpy.log10(rms)
      
        # store waveform data to a buffer
        frames.append(decodeData)
      
        # Read another socket
        data, address = sock.recvfrom(SOCK_CHUNK)      
        currentTime = time.time() - time_ini_
                  
        # if ab normal Volume detected, turn on camera 
        if volume > 70:
          msg = 'Start,'+str(currentTime)
          print msg
          child_CamActMsgConn.send(msg)
          if timeFlag.value == 1:
            timeFlag.value = 0
            videoRecStartTime.value = currentTime  
      
        # if mic location change, stop previous camera no matter for the
        # condiion.(1 mic is OK, but more mic is not suitable)
        if Previous_Location != Location:
          msg = 'End,'+str(currentTime)
          child_CamActMsgConn.send('End,'+str(currentTime))
                  
      
        volumeFile.write("%s       %s       %s\n" % (currentTime,volume,pkt_size))
        delay = currentTime - previousTime
        delayFile.write("%s   %s\n" % (sequenceNumber,delay))
        previousTime = currentTime

        flag = True
        print >>sys.stderr, 'Previous Location' + Previous_Location + ' ' + 'From '+ MicName+' '+Location+' received %s bytes from %s at time %s' % (pkt_size, address,currentTime)
        Previous_Location = Location
       
       
    except socket.timeout:
      if flag:
        print("* done recording")
      
      
        # wirte raw data into .wav file 
        wf = wave.open(WAVE_OUTPUT_FILENAME + str(WAVE_OUTPUT_NUMBER) + ".wav", 'wb')
        WAVE_OUTPUT_NUMBER = WAVE_OUTPUT_NUMBER + 1
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
      
        # volume and delay
        volumeFile.close()
        delayFile.close()

def CamActivationMsg(timeFlag,videoRecStartTime,parent_CamDurMsgConn):
    
  # define output file
  thefile = open('Cam_act.txt', 'w')
  thefile.write(' Server_Time       Cam_time        Cam_duration     ID     previousTime \n')
  thefile.close()
  
  while True:
    
    data = parent_CamDurMsgConn.recv()      
    print "Cam Says: "+data
    print str(videoRecStartTime.value)
      
    timeFlag.value = 1 #set up flag for another received message
    filePrint = str(videoRecStartTime.value) + '    ' + data
      
    thefile = open('Cam_act.txt', 'a')
    thefile.write(filePrint + '\n')
    thefile.close()

    
  



# --------------------------  Cam part -------------------------------#

def pipe_CamActMsg(REC_start,REC_start_time_in,parent_CamActMsgConn):
  
  
  while True:

    data = parent_CamActMsgConn.recv()
    print "[pipe_CamActMsg] Says: "+data
      
    # Flag for starting recording 
    if data[0:5] == 'Start':
      REC_start.value = 1
      REC_start_time_in.value = float(data[6:])
      print '[socket] REC_start = %s' %REC_start.value 
      
    # Flag for ending recording
    if data[0:3] == 'End':
      REC_start.value = 2
      print '[socket] REC_start = %s' %REC_start.value 
      
      
 
         

def Camera_Operation(REC_start,REC_duration,REC_start_time_in,REC_start_time_out,child_CamDurMsgConn):

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
      camera.start_recording('video'+str(REC_NUM)+'.h264') 
      REC_NUM = REC_NUM + 1  
      ini_time = time.time()
      ini_time_fixed = ini_time
      curr_time = ini_time 
      
      # record for several second
      while curr_time - ini_time <= recording_duration:
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
      # Send time stamp and duration message to edge
      pipe_CamDurationMsg(REC_start_time_out,REC_duration,REC_start_time_in,child_CamDurMsgConn)
      camera.stop_recording()
      

      
      
def pipe_CamDurationMsg(REC_start_time_out,REC_duration,REC_start_time_in,child_CamDurMsgConn):
  
  Previous_duration = REC_duration.value  
  message = str(REC_start_time_out.value) + '    ' + str(REC_duration.value) + '    ' + CamID + '    ' + str(REC_start_time_in.value)
  child_CamDurMsgConn.send(message)
  Previous_duration = REC_duration.value
  print 'Sent Video start time %s and duration %s To Edge' %(REC_start_time_out.value,REC_duration.value)


    
if __name__ == '__main__':
  
  # UDP part
  timeFlag = Value('i',1)
  videoRecStartTime = Value('d',0.0)
  
  # cam part
  REC_start = Value('i', 0)
  REC_start_time_in = Value('d', 0.0)
  REC_start_time_out = Value('d', 0.0)
  REC_duration = Value('d', 0.0)
  
  # pipe
  parent_CamActMsgConn, child_CamActMsgConn = Pipe()
  parent_CamDurMsgConn, child_CamDurMsgConn = Pipe()
  
  p1 = Process(target=UDP_Server_Audio, args=(timeFlag,videoRecStartTime,child_CamActMsgConn))
  p2 = Process(target=CamActivationMsg, args=(timeFlag,videoRecStartTime,parent_CamDurMsgConn))
  
  p3 = Process(target=pipe_CamActMsg, args=(REC_start,REC_start_time_in,parent_CamActMsgConn))
  p4 = Process(target=Camera_Operation, args=(REC_start,REC_duration,REC_start_time_in,REC_start_time_out,child_CamDurMsgConn))
  
  p1.start()
  p2.start()
  p3.start()
  p4.start()
  
  p1.join()
  p2.join()
  p3.join()
  p4.join()


