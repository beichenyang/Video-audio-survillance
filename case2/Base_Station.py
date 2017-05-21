import socket
import time

def TCP_Server():
  
  # host = '169.234.18.14' 
  host = '169.234.42.229'  # local host edge
  port = 13333     # Arbitrary non-privileged port
  TCPserverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  TCPserverSocket.bind((host, port))
  
  print host , port
  TCPserverSocket.listen(0)
  
  mic_location_pair = {}
  mic_location_index = 0
  
  while True:
    connection, address = TCPserverSocket.accept()
    print('Connected by', address)
    try:
      data = connection.recv(1024)
      print "Client Says: "+data
      connection.sendall('Server Say: Message Received')
      
      # Flag for starting recording 
      if data[0:3] == 'Mic':
        mic_location_pair[mic_location_index] = [data[0:4],data[5:14]]
        mic_location_index = mic_location_index + 1
        print '[socket]  '
      
      # Flag for ending recording
      if data[0:3] == 'End':
        
        print '[socket] REC_start = '  
      
    except socket.error:
      print "Error Occured."
      break
  
    connection.close()    
 
if __name__ == '__main__':
     
  p1 = Process(target=TCP_Server, args=())
  
  p1.start()
  
  p1.join()

