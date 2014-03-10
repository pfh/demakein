
import bisect, math
from raphs_curves import cornu


class Profile:
    def __init__(self, pos, low, high=None):
        if high is None: high = low
        self.pos = pos
        self.low = low
        self.high = high
    

    def __call__(self, position, high=False):
        if position < self.pos[0]:
            return self.low[0]
        if position > self.pos[-1]:
            return self.high[-1]
        i = bisect.bisect_left(self.pos, position)
        if self.pos[i] == position:
            if high:
                 return self.high[i]
            else:
                 return self.low[i]

        t = float(position - self.pos[i-1])/(self.pos[i]-self.pos[i-1])
        return (1.0-t)*self.high[i-1] + t*self.low[i]


    def __repr__(self):
        return 'Profile' + repr((self.pos,self.low,self.high))


    def start(self):
        return self.pos[0]
    

    def end(self):
        return self.pos[-1]


    def maximum(self):
        return max(max(self.low),max(self.high))


    def morph(self, other, operator):
        """ Fairly dumb way to combine profiles. 
            Won't work perfectly for min, max. """
        if not isinstance(other, Profile):
            other = Profile([0.0],[other],[other])
        pos = sorted(set(self.pos + other.pos))
        low = [ operator(self(p,False),other(p,False)) for p in pos ]
        high = [ operator(self(p,True),other(p,True)) for p in pos ]
        return Profile(pos,low,high)

    def max_with(self, other):
        return self.morph(other, lambda a,b: max(a,b))

    def min_with(self, other):
        return self.morph(other, lambda a,b: min(a,b))

    def __add__(self, other):
        return self.morph(other, lambda a,b: a+b)

    def __sub__(self, other):
        return self.morph(other, lambda a,b: a-b)

    def clipped(self, start, end):
        """ Clip or extend a profile """
        
        pos = [ start ]
        low = [ self(start, True) ]
        high = [ self(start, True) ]
        
        for i, p in enumerate(self.pos):
            if p <= start or p >= end: continue
            pos.append(p)
            low.append(self.low[i])
            high.append(self.high[i])
        
        pos.append(end)
        low.append(self(end, False))
        high.append(self(end, False))
        return Profile(pos,low,high)

    def reversed(self):
        """ Reverse profile. Positions are negated. """
        new_pos = [ -item for item in self.pos[::-1] ]
        return Profile(new_pos, self.high[::-1], self.low[::-1])

    def moved(self, offset):
        new_pos = [ item+offset for item in self.pos ]
        return Profile(new_pos, self.low, self.high)

    def appended_with(self, other):
        other = other.moved(self.pos[-1])
        return Profile(
            self.pos[:-1] + other.pos,
            self.low + other.low[1:],
            self.high[:-1] + other.high,
            )

    def as_stepped(self, max_step):
        pos = [ ]
        
        low = [ ]
        high = [ ]

        for i in range(len(self.pos)-1):
            pos.append(self.pos[i])
        
            ax = self.pos[i]
            ay = self.high[i]
            bx = self.pos[i+1]
            by = self.low[i+1]
            n = int( float(abs(by - ay)) / max_step )+1
            if not n: continue            
            pos.extend( (bx-ax)*float(j)/n+ax for j in range(1,n) )

        pos.append(self.pos[-1])
        
        diams = [ self(0.5*(pos[i]+pos[i+1])) for i in range(len(pos)-1) ]
        low = [ diams[0] ] + diams
        high = diams + [ diams[-1] ]
        
        #for i in range(len(pos)-1):
        #    assert high[i] == low[i+1], repr((high[i],low[i+1]))
        
        return Profile(pos,low,high)


def length(x,y):
    return math.sqrt(x*x+y*y)

def cornu_yx(t,mirror):
    # Reparamaterize for constant absolute rate of turning
    t = math.sqrt(abs(t)) * (1 if t > 0 else -1)
    y,x = cornu.eval_cornu(t)
    if mirror: y = -y
    return y,x

def solve(a1,a2):        
    pi = math.pi
    two_pi = pi*2
    
    def score(t1,t2,mirror):
        if abs(t1-t2) < 1e-6 or max(abs(t1),abs(t2)) > pi*10.0: return 1e30
    
        y1,x1 = cornu_yx(t1, mirror)
        y2,x2 = cornu_yx(t2, mirror)
        chord_a = math.atan2(y2-y1,x2-x1)
        chord_l = length(y2-y1, x2-x1)
        this_a1 = abs(t1) #t1*t1
        this_a2 = abs(t2) #t2*t2
        if mirror:
            this_a1 = -this_a1
            this_a2 = -this_a2
        if t1 > t2:
            this_a1 += pi
            this_a2 += pi
        ea1 = (this_a1-chord_a-a1+pi)%two_pi - pi
        ea2 = (this_a2-chord_a-a2+pi)%two_pi - pi
        return ea1*ea1+ea2*ea2
    
    s = None
    n = 2
    for new_mirror in [False,True]:
        for i in range(-n,n+1):
            for j in range(-n,n+1):    
                new_t1 = i*pi/n
                new_t2 = j*pi/n
                new_s = score(new_t1,new_t2,new_mirror)
                if s is None or new_s < s:
                    t1 = new_t1
                    t2 = new_t2
                    mirror = new_mirror
                    s = new_s
       
    step = pi / n * 0.5
    while step >= 1e-4:
        for new_t1,new_t2 in [(t1+step,t2+step), (t1-step,t2-step), (t1-step,t2+step), (t1+step,t2-step)]:
            new_s = score(new_t1,new_t2,mirror)
            if new_s < s:
                s = new_s
                t1 = new_t1
                t2 = new_t2
                break
        else:
            step *= 0.5

    return t1, t2, mirror

def curved_profile(pos, low, high, low_angle, high_angle, quality=512):
    n = len(pos)

    a = [ ]
    for i in range(n-1):
        x1 = pos[i]
        y1 = high[i] * 0.5
        x2 = pos[i+1]
        y2 = low[i+1] * 0.5
        a.append( (math.atan2(y2-y1,x2-x1)+math.pi)%(math.pi*2)-math.pi )    
    def interpret(i,value):
        if value == None:
            return None
        if value == 'mean':
            return (a[i-1]+a[i])*0.5
        if value == 'up':
            return a[i]
        if value == 'down':
            return a[i-1]
        return value*math.pi/180
    low_angle = [ interpret(i,value) for i,value in enumerate(low_angle) ]
    high_angle = [ interpret(i,value) for i,value in enumerate(high_angle) ]
    
    ppos = [ ]
    plow = [ ]
    phigh = [ ]
    
    for i in range(n-1):
        ppos.append(pos[i])
        plow.append(low[i])
        phigh.append(high[i])
        
        x1 = pos[i]
        y1 = high[i] * 0.5
        x2 = pos[i+1]
        y2 = low[i+1] * 0.5
        l = length(x2-x1,y2-y1)
        a = math.atan2(y2-y1,x2-x1)
        
        if high_angle[i] is not None:
            a1 = high_angle[i] - a
        else:
            a1 = 0.0
            
        if low_angle[i+1] is not None:
            a2 = low_angle[i+1] - a
        else:
            a2 = 0.0
        
        if abs(a1-a2) < math.pi*2/quality: continue
        
        #t1 = th1
        #t2 = th2
        
        #k0,k1 = clothoid.solve_clothoid(th1/math.pi,th2/math.pi)
        #print(th1, th2, k0, k1)
        
        #if abs(k1) < 1e-6: continue
        
        #t1 = k0-k1*0.5
        #t2 = k0+k1*0.5
        
        t1, t2, mirror = solve(a1,a2)
        
        cy1,cx1 = cornu_yx(t1,mirror)
        cy2,cx2 = cornu_yx(t2,mirror)
        cl = length(cx2-cx1,cy2-cy1)
        if abs(cl) < 1e-10: continue
        
        ca = math.atan2(cy2-cy1,cx2-cx1)
        
        steps = int( abs(t2-t1) / (math.pi*2) * quality )
        for i in range(1,steps):
            t = t1+i*(t2-t1)/steps
            yy,xx = cornu_yx(t,mirror)
            aa = math.atan2(yy-cy1,xx-cx1)
            ll = length(yy-cy1,xx-cx1)            
            x = math.cos(aa-ca+a) * ll/cl*l +x1
            y = math.sin(aa-ca+a) * ll/cl*l +y1
            ppos.append(x)
            plow.append(y*2)
            phigh.append(y*2)
    
    ppos.append(pos[-1])
    plow.append(low[-1])
    phigh.append(high[-1])
    return Profile(ppos, plow, phigh)



def make_profile(spec):
    pos = [ ]
    low = [ ]
    high = [ ]
    for item in spec:
        if len(item) == 2:
            this_pos, this_low = item
            this_high = this_low
        else:
            this_pos, this_low, this_high = item
        pos.append(this_pos)
        low.append(this_low)
        high.append(this_high)
    return Profile(pos, low, high)

if __name__ == '__main__':
    from raphs_curves import cornu
    
    for i in range(20+1):
        t = i / 10.0 - 0.5
        
        y1,x1 = cornu.eval_cornu(t)
        y2,x2 = cornu.eval_cornu(t+1e-3)
        print( t, (math.atan2(y2-y1,x2-x1)+math.pi) % (2*math.pi) -math.pi )   #Angle is t^2

