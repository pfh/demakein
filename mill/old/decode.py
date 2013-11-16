#!/usr/bin/env python
"""

Z command units are 0.025mm (1./40 mm)

V command units are mm/sec

"""

import sys, os, math, time, random

import serial

MAX_X = 200 * 40 #...
MAX_Y = 150 * 40 #... slightly more?

MAX_Z = 2420


class Mover:
    def __init__(self, horizontal_v, vertical_v, start, end, start_pos, smart=False):
        self.commands = start[:]
        self.horizontal_v = horizontal_v
        self.vertical_v = vertical_v
        self.ratio = horizontal_v / vertical_v
        self.end = end
        self.pos = start_pos
        self.commands.append( 'Z%d,%d,%d' % tuple(start_pos) )
        self.v = None
        self.smart = smart
        
    def close(self):
        self.commands.extend(self.end)

    def goto(self, pos, v):
        if pos == self.pos:
            #print 'dup', pos
            return
        
        if self.smart:
            dx = pos[0] - self.pos[0]
            dy = pos[1] - self.pos[1]
            dz = pos[2] - self.pos[2]
            length = math.sqrt(dx**2+dy**2+dz**2)
            effective_length = math.sqrt(dx**2+dy**2+(dz*self.ratio)**2)
            if effective_length:
                ideal_v = self.horizontal_v * length / effective_length
            else:
                ideal_v = self.vertical_v
            if ideal_v > v + 1e-3:
                #print self.pos, pos, dx, dy, dz, v, '->', ideal_v
                v = ideal_v

        if self.v != v:
            self.commands.append( 'V%.1f' % v)
            self.v = v
        self.commands.append( 'Z%d,%d,%d' % tuple(pos) )
        self.pos = pos


class Action:
    def __init__(self, motions):
        self.motions = motions
        dims = [[],[],[]]
        for pos, v in motions:
            for i in xrange(3):
                dims[i].append(pos[i])
       
        self.bounds = [ (min(item),max(item)) for item in dims ]
        self.small = (self.bounds[0][1]-self.bounds[0][0] <= 6*40 and
                      self.bounds[1][1]-self.bounds[1][0] <= 6*40)

    def cost_to_move_to(self, action, tool_diam):
        me = self.motions[-1][0]
        it = action.motions[0][0]
        dx = it[0]-(me[0]) # + tool_diam*2)
        dy = it[1]-(me[1]) # - tool_diam*2) #Tend to lower right
        return dx*dx+dy*dy
        
    def blocked_by(self, action, tool_diam):
        me = self.bounds
        it = action.bounds
        return (
            it[0][0] <= me[0][1]+tool_diam and me[0][0] <= it[0][1]+tool_diam and
            it[1][0] <= me[1][1]+tool_diam and me[1][0] <= it[1][1]+tool_diam            
        )
    
    def add_twitches(self, horizontal_v, vertical_v):
        i = 1
        run_length = 0.0
        
        max_run = 30*40 * (0.75+0.5*random.random())
        twitch_size = 3*40
        while i < len(self.motions):
            p1 = self.motions[i-1][0]
            p2 = self.motions[i][0]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = p2[2] - p1[2]
            this_length = math.sqrt(dx*dx+dy*dy)
            old_length = run_length
            run_length += this_length
            if dz or \
               (run_length <= max_run) or \
               p1[2] > 0 or \
               this_length < twitch_size:
                if dz: run_length = 0.0
                i += 1
                continue
        
            d1 = min(this_length, max_run-old_length+twitch_size)
            d2 = max(0, d1-twitch_size)
        
            def get_point(d):
                w2 = max(0.0,min(1.0,float(d)/this_length))
                assert 0 <= w2 <= 1
                w1 = 1.0 - w2
                
                return [
                    int(math.floor(p1[0]*w1+p2[0]*w2+0.5)),
                    int(math.floor(p1[1]*w1+p2[1]*w2+0.5)),
                    int(math.floor(p1[2]*w1+p2[2]*w2+0.5)),
                ]
            
            self.motions = self.motions[:i] + [
                (get_point(d1), horizontal_v),
                (get_point(d2), horizontal_v),
            ] + self.motions[i:]
            i += 2
            run_length = 0.0

def execute(commands, port='COM3'):
    port = serial.Serial(
        port = port,
        baudrate = 9600,
        timeout = 0, #Read timeout
    )
    
    start = time.time()
    for i, command in enumerate(commands):
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
    
        #while not port.getDSR():
        #    time.sleep(0.01)
        #port.write(command)
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
        

def do_it(tool_diam, filename, x=0, y=0, percent=0, plot=False, port='COM3', smart=False, twitch=False):
    # Load commands ==========================================================
    tool_diam = tool_diam * 40.0
    commands = open(filename,'rb').read().strip().rstrip(';').split(';')
    commands = [ item.strip() for item in commands ]
    
    print len(commands), 'commands'
    
    body_start_1 = commands.index('!MC1')
    body_start = body_start_1+2
    
    body_end = body_start
    while body_end < len(commands) and commands[body_end][:1] != '!':
        body_end += 1
    
    commands = commands[:body_start_1] + shift(commands[body_start_1:], int(x*40),int(y*40)) 
    
    xs = [ ]
    ys = [ ]
    zs = [ ]
    
    pos = None
    v = None
    motions = [ ]
    
    up_vs = [ ]
    down_vs = [ ]
    horiz_vs = [ ]
    
    for command in commands[body_start:body_end]:
        if command[:1] == 'V':
            v = float(command[1:])
        elif command[:1] == 'Z':
            new_pos = map(int,command[1:].split(','))
            
            motions.append((new_pos, v))
            
            xs.append(new_pos[0])
            ys.append(new_pos[1])
            zs.append(new_pos[2])
            
            if pos is not None:
                if pos[2] == new_pos[2]:
                    if abs(pos[0]-new_pos[0]) > 10 or abs(pos[1]-new_pos[1]) > 10:
                        horiz_vs.append(v)
                elif pos[2] < new_pos[2]:
                    up_vs.append(v)
                else:
                    down_vs.append(v)
            pos = new_pos
        else:
            assert False, command
    
    print 'x', min(xs),max(xs)
    print 'y', min(ys),max(ys)
    print 'z', min(zs),max(zs)
    #print set(horiz_vs)
    #print set(up_vs)
    #print set(down_vs)
    
    horizontal_v = min(horiz_vs) if horiz_vs else 10.0
    vertical_v = min(down_vs)    if down_vs else 0.5
    tool_up_z = max(zs)          if zs else 40
    
    print 'Horizontal v', horizontal_v
    print '  Vertical v', vertical_v
    print '     Tool up', tool_up_z
    
    if smart:
        last_pos = motions[-1][0]
        motions.append( ((last_pos[0],last_pos[1],tool_up_z), horizontal_v) )
        
        assert motions[0][0][2] == tool_up_z
        assert motions[-1][0][2] == tool_up_z
        
        # Reorder actions ==================================================================
        
        bounds = [ 0 ]
        for i in xrange(1, len(motions)):
            if motions[i-1][0][2] >= tool_up_z and motions[i][0][2] >= tool_up_z:
                bounds.append(i)
        bounds.append(len(motions))
        
        actions = [ Action(motions[bounds[i]:bounds[i+1]]) for i in xrange(len(bounds)-1) ]

        # Remove surfacing        
        #i = 0
        #while i < len(actions):
        #    if actions[i].bounds[2][0] < 0:
        #        i += 1
        #    else:
        #        print 'Discard', i, len(actions[i].motions)
        #        del actions[i]
        
        index = range(len(actions))
        new_actions = [ actions.pop(0) ]
        del index[0]
        while actions:            
            best = 0
            best_score = new_actions[-1].cost_to_move_to(actions[0], tool_diam)
            i = 0
            #n = index[0] + 1000
            #while i < len(actions) and index[i] <= n:
            n = 50
            while i < len(actions) and i <= n:
                score = new_actions[-1].cost_to_move_to(actions[i], tool_diam)
                if score < best_score:
                    for j in xrange(i-1,-1,-1):
                        if actions[i].blocked_by(actions[j], tool_diam):
                            break
                    else:
                        best_score = score
                        best = i
                i += 1
            
            print best,
            new_actions.append(actions.pop(best))
            del index[best]
        actions = new_actions
        print

        if twitch:
           for item in actions:
                item.add_twitches(horizontal_v,vertical_v)
                
        motions = [ ]
        for i, action in enumerate(actions):
            if motions:
                #Z slippage reset
                last = motions[-1][0]
                next = action.motions[0][0]
                motions.extend([((last[0],last[1],MAX_Z),15.0),((next[0],next[1],MAX_Z),15.0)])

            motions.extend(action.motions)
            
        
        # Toolup begone ===============================================================
        #
        #i = 0
        #while i < len(motions):
        #    #if (
        #    #    motions[i][0][0] == motions[i+1][0][0] == motions[i+2][0][0] == motions[i+3][0][0] and
        #    #    motions[i][0][1] == motions[i+1][0][1] == motions[i+2][0][1] == motions[i+3][0][1] and
        #    #    motions[i+1][0][2] >= tool_up_z and motions[i+2][0][2] >= tool_up_z
        #    #):
        #    #    print motions[i:i+4]
        #    #    del motions[i+1:i+3]
        #    #else:
        #    
        #    if motions[i][0][2] < tool_up_z:
        #        j = i
        #        while (
        #            j < len(motions) and
        #            motions[i][0][0] == motions[j][0][0] and
        #            motions[i][0][1] == motions[j][0][1]
        #        ):
        #            j += 1
        #        j -= 1
        #        
        #        if j >= i+2: 
        #            good = True
        #            for k in xrange(i,j-1):
        #                if motions[k][0][2] < motions[j][0][2]:
        #                    good = False
        #        
        #            if good:
        #                any_big_motions = False
        #                for k in xrange(max(0,i-20),i):
        #                    d = math.sqrt(
        #                        (motions[k][0][0]-motions[i][0][0])**2+
        #                        (motions[k][0][1]-motions[i][0][1])**2+
        #                        (motions[k][0][2]-motions[i][0][2])**2
        #                    )
        #                    if d > 2*40: any_big_motions = True
        #                
        #                if any_big_motions:
        #                    print i,j
        #                    del motions[i+1:j]
        #                else:
        #                    print i,j, 'but taking a breather'
        #    
        #    i += 1
    
    # Emit ========================================================================

    if percent:
        i = int(len(motions)*percent/100.0)
        motions = [((motions[i][0][0],motions[i][0][1],tool_up_z),horizontal_v)] + motions[i:]

    if plot:
        pos = motions[0][0]
        t = 0.0
        for new_pos,v in motions[1:]:
            d = math.sqrt(
                (pos[0]-new_pos[0])**2+
                (pos[1]-new_pos[1])**2+
                (pos[2]-new_pos[2])**2
            )
            t += d / 40.0 / v
            pos = new_pos
        print 'Running time: %.1f units' % (t/60.0/60.0)
        
        import pylab
        
        xs = [ ]
        ys = [ ]
        zs = [ ]
        vs = [ ]
        for pos,v in motions:
            xs.append(pos[0])
            ys.append(pos[1])
            zs.append(pos[2])
            vs.append(v)
        
        pylab.ion()
        
        pylab.figure(figsize=(12,12))
        pylab.subplot(3,1,1)
        pylab.plot(xs,ys,alpha=0.1,color='r')
        a, = pylab.plot(xs,ys,color='b')
        pylab.gca().set_aspect('equal', 'datalim')
        pylab.subplot(3,1,2)
        b, = pylab.plot(xs,zs)
        pylab.gca().set_aspect('equal', 'datalim')
        pylab.subplot(3,1,3)
        c, = pylab.plot(ys,zs)
        pylab.gca().set_aspect('equal', 'datalim')
        #pylab.show()
        
        window = 1000
        i = 0
        while True:
            a.set_xdata(xs[i:i+window])
            a.set_ydata(ys[i:i+window])
            b.set_xdata(xs[i:i+window])
            b.set_ydata(zs[i:i+window])
            c.set_xdata(ys[i:i+window])
            c.set_ydata(zs[i:i+window])
            i += window // 3
            i = i % len(xs)
            pylab.draw()
        
        return
    
    
    print motions[0][0]
    mover = Mover(horizontal_v, vertical_v, commands[:body_start], 
                  commands[body_end:], motions[0][0], False) #smart)
    del motions[0]
    for pos, v in motions:
        mover.goto(pos,v)
    mover.close()
    
    print len(mover.commands), 'commands'
    
    execute(mover.commands, port)
    

if __name__ == '__main__':
    tool_diam = float(sys.argv[1])
    plot = False
    smart = False
    twitch = False
    percent = 0
    port = '/dev/ttyUSB0'
    x = 0.0
    y = 0.0
    filenames = [ ]
    for item in sys.argv[2:]:
        if item == 'plot':
            plot = True
        elif item == 'smart':
            smart = True
        elif item == 'twitch':
            twitch = True
        elif '=' in item:
            param,value = item.split('=')
            if param == 'percent':
                percent = float(value)
            elif param == 'port':
                port = value
            elif param == 'x':
                x = float(value)
            elif param == 'y':
                y = float(value)
            else:
                assert False
        else:
            assert os.path.exists(item)
            filenames.append(item)

    assert smart or not twitch

    for filename in filenames:
        do_it(tool_diam=tool_diam, filename=filename, percent=percent, plot=plot, smart=smart, port=port, x=x, y=y, twitch=twitch)
        percent = 0

