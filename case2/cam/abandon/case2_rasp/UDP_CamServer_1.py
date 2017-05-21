# UDP_CamServer V0.0.1: Get data from clould, decode 
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
import TCP_CamLocation_msg
from multiprocessing import Process, Value


recording_duration = 15

def UDP_Server_Audio(timeFlag,videoRecStartTime):
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
  server_address = ('169.234.24.235 ', 10000)
  #server_address = ('20.0.0.99', 10000)

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
          TCP_CamLocation_msg.TCP_client_on(currentTime)
          if timeFlag.value == 1:
            timeFlag.value = 0
            videoRecStartTime.value = currentTime  
      
        # if mic location change, stop previous camera no matter for the
        # condiion.(1 mic is OK, but more mic is not suitable)
        if Previous_Location != Location:
          TCP_CamLocation_msg.TCP_client_audio_end(currentTime)
          
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

def TCP_Server_CamActivationMsg(timeFlag,videoRecStartTime):
  
  # host is the local machine   
  host = 'localhost'        
  port = 12000     # Arbitrary non-privileged port
  TCPserverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  TCPserverSocket.bind((host, port))
  
  # define output file
  thefile = open('Cam_act.txt', 'w')
  thefile.write(' Server_Time       Cam_time        Cam_duration     ID     previousTime \n')
  thefile.close()
  
  print host , port
  TCPserverSocket.listen(0)
  
  while True:
    connection, address = TCPserverSocket.accept()
    print('Connected by', address)
    try:
      data = connection.recv(1024)      
      print "Client Says: "+data
      print str(videoRecStartTime.value)
      
      timeFlag.value = 1 #set up flag for another received message
      filePrint = str(videoRecStartTime.value) + '    ' + data
      
      thefile = open('Cam_act.txt', 'a')
      thefile.write(filePrint + '\n')
      thefile.close()

    except socket.error:
      print "Error Occured."
      break
  
    connection.close()    
    
    
if __name__ == '__main__':
  
  timeFlag = Value('i',1)
  videoRecStartTime = Value('d',0.0)
  
  p1 = Process(target=UDP_Server_Audio, args=(timeFlag,videoRecStartTime))
  p2 = Process(target=TCP_Server_CamActivationMsg, args=(timeFlag,videoRecStartTime))
  p1.start()
  p2.start()
  p1.join()
  p2.join()
