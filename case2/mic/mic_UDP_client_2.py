# UDP_client V0.0.10: Get raw data from file, encode those data 
# by opuslib, and send edcoded data to server, add sequence number,
# microphone name and location are added at frame header
# Add a process to receive location change instruction, and thus change
# location name which is sent to server


import socket
import sys
import pyaudio
import wave
from opuslib import classes
import time
from multiprocessing import Process, Value



#UDPAudioHost = '10.15.20.13' # Edge
#UDPAudioHost = '169.234.42.229' # Edge
TCPMicLocationHost = '169.234.53.23' # Localhost pi2


LocationCam={} 
# Add elements to empty dictionary.
LocationCam['Location1'] = 'Cam1'  # bigcam pi3
LocationCam['Location2'] = 'Cam2'  # raspcam pi5

CamIP={}
# Add elements to empty dictionary.
CamIP['Cam1'] = '10.15.20.13'    # big
CamIP['Cam2'] = '10.15.20.15'    # raspcam



def IP_Location_Dict(Mic_Location):
  
  cam=LocationCam[location]
  IP=CamIP[cam]  
  return IP

def TCP_Server_MicLocationMsg(location):
	
  # host = '169.234.15.36'        
  port = 12346     # Arbitrary non-privileged port
  TCPserverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  TCPserverSocket.bind((TCPMicLocationHost, port))
  
  print TCPMicLocationHost , port
  TCPserverSocket.listen(0)
  
  while True:
    connection, address = TCPserverSocket.accept()
    print('Connected by', address)
    try:
      data = connection.recv(1024)
      print "Client Says: "+data
      
      if data[0:] == 'Location1':
        location.value = 1
        print '[Microphone] Location = %s' %location.value 

      if data[0:] == 'Location2':
        location.value = 2
        print '[Microphone] Location = %s' %location.value 
      
    except socket.error:
      print "Error Occured."
      break
  
    connection.close()    



def UDP_Client_Audio(MicName,Server_locationNum):
  
  # Create a UDP socket
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  # open audio file
  wf = wave.open("output180s.wav", 'rb')
      
  # creat a audio stream
  p = pyaudio.PyAudio()
  
  # Audio parameter
  CHUNK = 960
  FORMAT = p.get_format_from_width(wf.getsampwidth())
  CHANNELS = wf.getnchannels()
  print "Channels: %s" %CHANNELS
  RATE = rate=wf.getframerate()
  print "Rate: %s" %RATE

  # Audio Stream Initial
  stream = p.open(format=FORMAT,
                  channels=CHANNELS,
                  rate=RATE,
                  #frames_per_buffer=CHUNK
                  output = True)  
                
                
  server_address = (UDPAudioHost, 10000)

  print("* recording")

  try:
        
      enc = classes.Encoder(RATE,CHANNELS,'voip')    
      t_ini = time.time()
    
      data = wf.readframes(CHUNK)
    
      i = 0
      # Send data
      while data != '':  
        stream.write(data)
        encdata = enc.encode(data,CHUNK)
        print >>sys.stderr, 'sending data %s size %s' % (i,len(encdata))
        sequence = '{0:04}'.format(i)
        Mic_Location = 'Location' + str(Server_locationNum.value)
        sendData = MicName + Mic_Location + sequence + encdata
        UDPAudioHost = IP_Location_Dict(Mic_Location)
        server_address = (UDPAudioHost, 10000)
        sent = sock.sendto(sendData, server_address)
        t = time.time() - t_ini
        print "current time %s" % t
        data = wf.readframes(CHUNK)
        i = i + 1


  finally:
      print >>sys.stderr, 'closing socket'
      sock.close()
      stream.stop_stream()
      stream.close()
      p.terminate()

if __name__ == '__main__':  
  
  # Micname and location, need manually input location number
  MicName = 'Mic1'
  LocationNum = input('location number: ')
  Location = 'Location' + str(LocationNum)
  
  # TCP_server Process
  Server_locationNum = Value('i', LocationNum)
  p1 = Process(target=TCP_Server_MicLocationMsg, args=(Server_locationNum,))
  p2 = Process(target=UDP_Client_Audio, args=(MicName,Server_locationNum,))
  p1.start()
  p2.start()
  p1.join()
  p2.join()
