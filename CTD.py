# TODO: update usage
# TODO: detect when a command has finished when instrument returns command prompt

USAGE = """

GP- This has been modified to make it a generic raw socket connection, with <CR><LF>

This program allows direct user interaction with an ADCP instrument via a socket.


USAGE:
    python ADCP.py address port basename # connect to instrument on address:port, with logger basename
    python ADCP.py address port # connect to instrument on address:port, with logger defaulted to generic basename
    python ADCP.py port              # connect to instrument on localhost:port, with logger defaulted to generic basename
    
    

Example:
    python ADCP.py 10.180.80.169 2101 ADCP.180.80.169_2101
    

It establishes a TCP connection with the provided service, starts a thread to
print all incoming data from the associated socket, and goes into a loop to
dispatch commands from the user. In this "logged" version the script stops any sampling,
initializes a new sampling program.

Commands accepted: 
    "initialize,[configuration]" - reconfigures instrument to desired configuration.  Configurations include: B104, I103, E101, D102, K101, E301, D302
    "status" - prints status and configuration information
    "sample" - initializes sampling
    "q" - closes TCP connection and exits program

"""

__author__ = 'Ryan Cox'
__license__ = 'Apache 2.0'

import sys
import socket
import os
import re
import time
import select
from logger import Logger   #logger.py is in Ryan's python $path C:/python27
from threading import Thread

# Thread to receive and print data.
class _Recv(Thread):
    def __init__(self, conn, basename):
        Thread.__init__(self, name="_Recv")
        self._conn = conn
        self.myFileHandler = Logger(basename)
        print "logger initialized with basename %s, will create new file and name at 00:00UTC daily" % (basename)
        self._last_line = ''
        self._new_line = ''
        self.setDaemon(True)

    # The _update_lines method adds each new character received to the current line or saves the current line and creates a new line
    def _update_lines(self, recv):
        if recv == "\n":  #TMPSF data line terminates with a ?, most I/O is with a '\n'
            self._new_line += recv #+ "\n" #this keeps the "#" in the I/O
            self._last_line = self._new_line
            self._new_line = ''
            return True
        else:
            self._new_line += recv
            return  False
            
    # The run method receives incoming chars and sends them to _update_lines, prints them to the console and sends them to the logger.
    def run(self):
        print "### _Recv running."
        while True:
            recv = self._conn.recv(1)
            newline = self._update_lines(recv)
            os.write(sys.stdout.fileno(), recv)   #this writes char by char-- use commented out 'if newline' to write as a line
            self.myFileHandler.write(recv)    #writes to logger file  

            # uncomment code below to print by lines instead of by characters.
            # if newline:
                 # os.write(sys.stdout.fileno(), self._last_line)  #writes to console
                 # myFileHandler.write( self._last_line )    #writes to logger file   + "\n"
                    
            sys.stdout.flush()

# Main program
class _Direct(object):
    # Establishes the connection and starts the receiving thread.
    def __init__(self, host, port, basename):
        print "### connecting to %s:%s" % (host, port)  
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self._sock.connect((host, port))
        self._bt = _Recv(self._sock, basename)
        self._bt.start()
        
        # print status messages
        self.send('GetHD\r\n') # display hardware data
        time.sleep(4)
        self.send('GetCD\r\n') # display configuration data
        time.sleep(2)
        self.send('GetCC\r\n') # display calibration coefficients
        time.sleep(3)
        self.send('GetEC\r\n') # display event counter data
        time.sleep(1)

        # TODO: update info 
        # print possible user commands
        print "### Status checks complete, but not verified"
        print "### To configure instrument enter 'init'"
        print "### To display status and configuration information enter 'status'"
        print "### To start sampling enter 'sample'"
        print "### To stop sampling enter 'stop'"
        print "### To close socket and exit program enter 'q'"
    
    # Dispatches user commands.    
    def run(self):
        while True:
        
            cmd = sys.stdin.readline()
            
            cmd = cmd.strip()
            cmd1 = cmd.split(",")
            
            if cmd1[0] == "q":
                print "### exiting"
                break
            
            # initializes instrument 
            elif cmd1[0] == "init":
                print "### initializing"
                
                self.send('MP\r\n') # set profiler mode
                time.sleep(1)
                self.send('MP\r\n') # must be repeated
                time.sleep(1)
                self.send('Navg=4\r\n') # sample rate
                time.sleep(1)
                self.send('OutputFormat=0\r\n') 
                time.sleep(1)

            elif cmd1[0] == "status":
                # print status messages
                self.send('GetHD\r\n') # display hardware data
                time.sleep(1)
                self.send('GetCD\r\n') # display configuration data
                time.sleep(1)
                self.send('GetCC\r\n') # display calibration coefficients
                time.sleep(1)
                self.send('GetEC\r\n') # display event counter data
                time.sleep(1)
            
            elif cmd1[0] == "sample":
                print "sampling started"
                
                self.send('startnow\r\n') 
                time.sleep(1)
                
            elif cmd1[0] == "stop":
                print "stopping"
                
                self.send('stop\r\n') 
                time.sleep(1)
                
            else:
                print "### sending '%s'" % cmd
                self.send(cmd)
                self.send('\r\n')

        self.stop()
    
    # closes the connection to the socket
    def stop(self):
        self._sock.close()
    
    # Sends a string. Returns the number of bytes written.
    def send(self, s):
        c = os.write(self._sock.fileno(), s)
        return c

# main method.  Accepts command line input parameters and runs the program
# default host: 'localhost'
# default port: no default, must be specified
# default basename: "INSTNAME_IPADDR_PORT"
if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print USAGE
        exit()
    
    elif len(sys.argv) == 2:
        host = 'localhost'
        port = int(sys.argv[1])
        basename = "INSTNAME_IPADDR_PORT"
        
    elif len(sys.argv) == 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
        basename = "INSTNAME_IPADDR_PORT"
        
    else:
        host = sys.argv[1]
        port = int(sys.argv[2])
        basename = sys.argv[3]

    direct = _Direct(host, port, basename)
    direct.run()

