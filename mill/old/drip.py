
import sys, time, serial

commands = open(sys.argv[1],'rb').read().rstrip(';').split(';')
print(len(commands), 'commands')

port = serial.Serial(
    port = 'COM3',     #Change this to the appropriate port
    baudrate = 9600,
)

start = time.time()
for i, command in enumerate(commands):
    command = command.strip() + ';'

    while not port.getDSR():
        time.sleep(0.01)
    port.write(command)

    delta = int(time.time()-start)
    sys.stdout.write('\r%3dmin  %3.0f%%' % (
         delta // 60,
         (i+1.0)/len(commands)*100.0
    ))
    sys.stdout.flush()

port.close()
print()