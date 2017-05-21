# sotrage the list of 

import socket

IP='localhost'  
port = 12445                   # The same port as used by the server

def TCP_client_on(current_time):
      
  host = IP
  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((host, port))
  s.sendall(b'Start Video Recording %s' % current_time)
  data = s.recv(1024)
  s.close()
  print('Received', repr(data))

def TCP_client_off(current_time):

  host = IP
  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((host, port))
  s.sendall(b'Stop Video Recording %s' % current_time)
  data = s.recv(1024)
  s.close()
  print('Received', repr(data))

def TCP_client_audio_end(current_time):

  host = IP
  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((host, port))
  s.sendall(b'End Audio Recording %s' % current_time)
  data = s.recv(1024)
  s.close()
  print('Received', repr(data))


#TCP_client_on(12)
