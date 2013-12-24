#!/usr/bin/env python
"""

Z command units are 0.025mm (1./40 mm)

V command units are mm/sec

"""

import sys, os, math, time, random

import serial

import nesoni
from nesoni import config

MAX_X = 200 * 40 #...
MAX_Y = 150 * 40 #... slightly more?
MAX_Z = 2420

def shift(commands, x,y):
    result = [ ]
    for item in commands:
        if not item.startswith('Z'):
           result.append(item)
           continue
           
        pos = map(int,item[1:].split(','))
        pos[0] += x
        pos[1] += y
        assert 0 <= pos[0] < MAX_X, 'outside work area on x axis'
        assert 0 <= pos[1] < MAX_Y, 'outside work area on y axis'
        result.append('Z%d,%d,%d' % tuple(pos))
    return result

def execute(commands, port_name,  start=0):
    port = serial.Serial(
        port = port_name,
        baudrate = 9600,
        timeout = 0, #Read timeout
    )
    
    start = time.time()
    #for i, command in enumerate(commands):
    for i in xrange(start,len(commands)):
        command = commands[i]
    
        char = port.read(1)
        if char:
           sys.stdout.write('\nRead: ')
           while char:
               sys.stdout.write(char)
               sys.stdout.flush()
               char = port.read(1)
           sys.stdout.write('\n')
           sys.stdout.flush()
        
        command = command.strip() + ';\n'

        #Paranoia
        for j in xrange(3):
            while not port.getDSR():
                time.sleep(0.01)
            port.write(';\n')
    
        for char in command:
            while not port.getDSR():
                time.sleep(0.01)
            port.write(char)
    
        delta = int(time.time()-start)
        sys.stdout.write('\r%3dmin  %3.0f%%' % (
             delta // 60,
             (i+1.0)/len(commands)*100.0
        ))
        sys.stdout.flush()
    
    port.close()
    print



@config.Positional('filename', '.prn file to send to mill.')
@config.String_flag('port')
@config.Float_flag('x', 'X offset')
@config.Float_flag('y', 'Y offset')
@config.Float_flag('percent', 'Start from percent-done')
class Send(config.Action):
    filename = None
    port = '/dev/ttyUSB0'
    x = 0.0
    y = 0.0
    percent = 0.0

    def run(self):
        commands = open(self.filename,'rb').read().strip().rstrip(';').split(';')
        commands = [ item.strip() for item in commands ]
        
        print len(commands), 'commands'
    
        body_start = commands.index('!MC1') + 1
    
        body_end = body_start
        while body_end < len(commands) and commands[body_end][:1] != '!':
            body_end += 1
    
        #commands = (
        #    commands[:body_start_1] + 
        #    shift(commands[body_start_1:], int(self.x*40),int(self.y*40)) 
        #    )
        
        start = body_start + int(self.percent/100.0*(body_end-body_start))
        
        while True:
            if start == body_start: break
            if commands[start].startswith('Z'):
                pos = map(int,item[1:].split(','))
                if pos[2] >= 2420:
                    break
            start -= 1
        
        print 'commands  ', len(commands)
        print 'body_start', body_start
        print 'start     ', start
        print 'body_end  ', body_end
        
        execute(commands[:body_start], self.port)
        
        execute(shift(commands[body_start:],int(self.x*40),int(self.y*40)), 
                self.port, start-body_start)



if __name__ == '__main__': 
    nesoni.run_tool(Send)


