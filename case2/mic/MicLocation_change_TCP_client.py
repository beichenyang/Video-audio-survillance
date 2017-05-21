import time
import socket

host = '169.234.53.23'  #Mic pi2
# host = '169.234.25.60'
port = 12346           # The same port as used by the TCP_server on pi5

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))
s.sendall(b'Location2')
s.close()
print 'Sent Data'
