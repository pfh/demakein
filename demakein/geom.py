"""

Large parts of this are just python translations of lib2geom.

"""


import collections, math



class XYZ(collections.namedtuple('XYZ','x y z')):
    def __neg__(self):
        return XYZ(-self.x,-self.y,-self.z)
    
    def __add__(self, other):
        return XYZ(self.x+other.x,self.y+other.y,self.z+other.z)

    def __sub__(self, other):
        return XYZ(self.x-other.x,self.y-other.y,self.z-other.z)

    def __mul__(self, other):
        return XYZ(self.x * other, self.y * other, self.z * other)
        
    def __rmul__(self, other):
        return self*other

    def dot(self, other):
        return self.x*other.x+self.y*other.y+self.z*other.z
    
    def cross(self, other):
        return XYZ(
            self.y*other.z-self.z*other.y,
            self.z*other.x-self.x*other.z,
            self.x*other.y-self.y*other.x
            )
    
    def mag2(self):
        return self.dot(self)
    
    def mag(self):
        return math.sqrt(self.mag2())

    def unit(self):
        return (1.0/self.mag()) * self



class Linear(collections.namedtuple('Linear','a0 a1')):
    """ f(t) = a0*(1-t)+a1*t
    """

    def __call__(self, t):
        return self.a0*(1-t)+self.a1*t

    def __add__(self, other): 
        return type(self)(self.a0+other.a0,self.a1+other.a1)

    def __sub__(self, other): 
        return type(self)(self.a0-other.a0,self.a1-other.a1)

    def __mul__(self, other): 
        return type(self)(self.a0*other,self.a1*other)
        
    def __rmul__(self, other):
        return self*other

    def tri(self):
        return self.a1-self.a0

    def hat(self):
        return (self.a1+self.a0)*0.5


class S_basis(tuple):
    """ length>=1 immutable list of Linear
    
        f(t) = sum self[i](t) * s**t where s = t*(1-t)
    """

    def __call__(self, t):
        s = t*(1-t)
        result = self[0](t)
        p = s
        for i in xrange(1,len(self)):
            result += self[i](t) * p
            p *= s
        return result
    
    def __repr__(self):
        return 'S_basis(' + repr(list(self)) + ')'
        
    def scaled(self,other): 
        return type(self)( item*other for item in self )
    
    def shifted(self, i):
        return type(self)((self[0]*0,)*i+tuple(self))
    
    def truncated(self, n):
        return type(self)(self[:n])
    
    def _compat(self,other):
        size = max(len(self),len(other))
        if len(self) < size:
            self = type(other)(tuple(self) + (self[0]*0,)*(size-len(self)))
        if len(other) < size:
            other = type(other)(tuple(other) + (other[0]*0,)*(size-len(other)))
        return size, self, other
    
    def __add__(self, other):
        size, self, other = self._compat(other)
        return type(self)( self[i]+other[i] for i in xrange(size) )

    def __sub__(self, other):
        size, self, other = self._compat(other)
        return type(self)( self[i]-other[i] for i in xrange(size) )

    def multiplied(self, other, operator):
        zero = operator(self[0].a0*0,other[0].a0*0)
        
        c = [Linear(zero,zero)]*(len(self)+len(other))
        for j in xrange(len(other)):
            for i in xrange(j,j+len(self)):
                tri = operator(other[j].tri(),self[i-j].tri())
                c[i+1] = c[i+1] + Linear(-tri,-tri)
                c[i] = c[i] + Linear(operator(other[j].a0,self[i-j].a0), operator(other[j].a1,self[i-j].a1))
        #while len(c) > 1 and c[-1] == zero:
        #    del c[-1]
        return S_basis(c)
    
    def __mul__(self, other):
        return self.multiplied(other, lambda a,b: a*b)
        
    def __rmul__(self, other):
        return self*other
    
    def dot(self, other):
        return self.multiplied(other, lambda a,b: a.dot(b))
    
    def divided(self, other, k):
        return least_squares(
            S_basis([Linear(self[0].a0/other[0].a0,self[0].a1/other[0].a1)]),
            lambda x: other*x-self,
            lambda x: other,
            lambda x: ZERO,
            k)
    
        #remainder = self
        #result = [ ]
        #for i in xrange(k):
        #    if len(remainder) <= i:
        #        break
        #    ci = Linear(remainder[i].a0/other[0].a0, remainder[i].a1/other[0].a1)
        #    result.append(ci)
        #    remainder = remainder - (S_basis([ci])*other).shifted(i)
        #return S_basis(result)

    def reciprocal(self, k):
        return ONE.divided(self, k)
    
    def derivative(self):
        c = [ ]
        for k in xrange(len(self)-1):
             d = (2*k+1)*(self[k].a1 - self[k].a0)
             c.append(Linear(
                 d + (k+1)*self[k+1].a0,
                 d - (k+1)*self[k+1].a1
                 ))
        k = len(self)-1
        d = (2*k+1)*(self[k].a1 - self[k].a0)
        c.append(Linear(d,d))
        return S_basis(c)

    def integral(self):
        a = [ self[0]*0 ]
        for k in xrange(1,len(self)+1):
            ahat = self[k-1].tri()*(-1.0/(2*k))
            a.append(Linear(ahat,ahat))
        aTri = self[0].a0*0
        for k in xrange(len(self)-1,-1,-1):
            aTri = (self[k].hat() + (k+1)*0.5*aTri)*(1.0/(2*k+1))
            a[k] = a[k] + Linear(-0.5*aTri,0.5*aTri)
        return S_basis(a)
    
    def sqrt(self, k):
        return least_squares(self, lambda x: x*x-self, lambda x: x.scaled(2), lambda x: ONE.scaled(2), k)

        #""" Calculate square root by newton's method """
        #result = self
        #for i in xrange(iters):
        #    result = (result+self.divided(result, k)).scaled(0.5)
        #return result

    def compose(self, other):
        """ Calculate f(t)=self(other(t)) """
        s = (ONE-other)*other
        result = S_basis([self[0]*0])
        for i in xrange(len(self)-1,-1,-1):
            result = result*s + (ONE-other).scaled(self[i].a0) + other.scaled(self[i].a1)
            #S_basis([Linear(self[i].a0,self[i].a0)]) + other.scaled(self[i].a1-self[i].a0)
        return result

    def solve(self, target, k, iters=20):
        """ Solve self.compose(x) = target for x using Newton's method            
        """
        result = target
        deriv = self.derivative()
        for i in xrange(iters):
            result = result - (self.compose(result) - target).divided(deriv.compose(result), k)
            result = result.truncated(k)
        return result.truncated(k)

    def inverse(self, k, iters=5):
        return self.solve(IDENTITY, k, iters)

        
ONE = S_basis([Linear(1.0,1.0)])
ZERO = S_basis([Linear(0.0,0.0)])
IDENTITY = S_basis([Linear(0.0,1.0)])


#def fit(initial, transform, k, iters):
#    def score(guess):
#        tx = transform(guess)
#        return (tx*tx).integral()[0].tri()
#    
#    result = initial
#    current = score(result)
#    
#    #basis = [ ]
#    #slant = IDENTITY-ONE.scaled(0.5)
#    #for i in xrange(k):
#    #    basis.append(ONE.shifted(i))
#    #    basis.append(slant.shifted(i))
#        #basis.append(IDENTITY.shifted(i))
#        #basis.append((ONE-IDENTITY).shifted(i))
#        
#    #needs to be an orthogonal basis
#    
#    # Legendre polynomials
#    X = IDENTITY.scaled(2.0)-ONE   # Compress from -1,1 to 0,1
#    basis = [ ONE, X ]
#    while len(basis) < k:
#        n = len(basis)
#        basis.append( (basis[-1]*X).scaled((2*n+1)/(n+1.0)) - basis[-2].scaled(n/(n+1.0)) )
#    
#    #plot(*basis)
#    #foo
#    
#    step = 1.0
#    for i in xrange(iters):
#        for item in basis:
#            low = result + item.scaled(-step)
#            low_score = score(low)
#            high = result + item.scaled(step)
#            high_score = score(high)
#            
#            c = current
#            a = (high_score+low_score)*0.5-current
#            b = high_score-a-c
#
#            if high_score < current:
#                result = high
#                current = high_score
#                #step *= 2.0
#            if low_score < current:
#                result = low
#                current = low_score
#                #step *= 2.0
#
#            if a:
#                min_point = -0.5/step*b/a
#                new = result + item.scaled( min_point )
#                new_score = score(new)                
#                if new_score < current:
#                    result = new
#                    current = new_score
#                    step = max(step, abs(min_point)*2.0)
#        step *= 0.85
#        print current, step
#        #if not step: break
#
#    return result


def newtonoid(initial, fp,fpp, k):
    """ Choose x to minimize the integral of f(x) over [0,1] """
    def scorep(a,b):
        return (b*fp(a)).integral()[0].tri()    
    def scorepp(a,b):
        return (b*b*fpp(a)).integral()[0].tri()

    result = initial
    #current = score(result)
    
    # Legendre polynomials
    X = IDENTITY.scaled(2.0)-ONE   # Compress from -1,1 to 0,1
    basis = [ ONE, X ]
    while len(basis) < k*2:
        n = len(basis)
        basis.append( (basis[-1]*X).scaled((2*n+1)/(n+1.0)) - basis[-2].scaled(n/(n+1.0)) )
    
    #plot(*basis)
    #foo
    
    step = 1.0
    for i in xrange(k*8):
        for item in basis:
            #c = score(result)
            #b = scorep(result)
            #a = 0.5*scorepp(result)            
            #step = -b/2a
            
            step = -scorep(result,item)/scorepp(result,item)
            #print step
            new = result + item.scaled(step)
        
                #new = result + item.scaled( min_point )
            #new_score = score(new)                
            #if new_score < current:
            result = new
            #current = new_score
        #step *= 0.85
        #print current, step
        #if not step: break

    return result

def least_squares(guess, f,fp,fpp, k):
    """ Choose x to minimize the integral of f(x)^2 over [0,1] """    
    #def f2(x): 
    #    y = f(x)
    #    return y*y
    def f2p(x):
        return (fp(x)*f(x)).scaled(2.0)
    def f2pp(x):
        yp = fp(x)
        return (fpp(x)*f(x)+yp*yp).scaled(2.0)
    return newtonoid(
        guess,
        f2p,
        f2pp,
        k)

"""TODO: optimize path for aesthetics
"""

class Frame(collections.namedtuple('Frame', 'origin x y z')):
    """ Origin and orthogonal basis. """

    def apply(self, point):
        return self.origin + self.x*point.x + self.y*point.y+ self.z*point.z
    
    def unapply(self, point):
        point = point - self.origin
        return XYZ(self.x.dot(point),self.y.dot(point),self.z.dot(point))


class Path(collections.namedtuple('Path','path velocity normal position')):
    def find(self, position):
        low = 0.0
        high = 1.0
        for i in xrange(32):
            mid = (low+high)*0.5
            value = self.position(mid)
            if position < value:
                high = mid
            elif position > value:
                low = mid
            else:
                return mid #Unlikely.
        return (low+high)*0.5

    def get_length(self):
        return self.position[0].a1

    def get_frame(self, position):
        t = self.find(position)
        point = self.path(t)
        
        z = self.velocity(t).unit()
        x = self.normal(t)
        x = (x - z*x.dot(z)).unit()
        y = z.cross(x)
        return Frame(point, x,y,z)

    def get_point(self, position):
        return self.path(self.find(position))
    
    def get_bentness(self, a,b):
        aa = self.find(a)
        bb = self.find(b)
        seg = self.path.compose(S_basis([Linear(aa,bb)]))
        straight = seg[:1]
        diff = seg-straight
        return math.sqrt( diff.dot(diff).integral()[0].tri() / seg[0].tri().mag2() )
        

def path(point0,vec0,norm0,point1,vec1,norm1):
    #a = S_basis([Linear(XYZ(0.0,0.0,0.0), XYZ(1.0,1.0,0.0))])
    #b = S_basis([Linear(XYZ(3.0,0.0,0.0), XYZ(0.0,-1.0,0.0))])
    #arc = a + (S_basis([Linear(-a[0].tri(),a[0].tri())])+b).shifted(1)
    tri = point1-point0
    
    length = tri.mag()
    print '.', length
    vec0 = vec0.unit()
    vec1 = vec1.unit()
    for i in xrange(4):
        s = length
        path = S_basis([Linear(point0,point1),Linear(vec0*s-tri,vec1*-s+tri)])    
        velocity = path.derivative()
        speed = velocity.dot(velocity).sqrt( 6 )
        position = speed.integral()
        position = position - ONE.scaled(position[0].a0)
        length = position[0].a1
        print '-', length
    
    normal = S_basis([Linear(norm0,norm1)])
    
    return Path(path, velocity, normal, position)


def plot(*items):
    import pylab

    ts = [ i/100.0 for i in xrange(101) ]
    for item in items:
        pylab.plot(ts, [ item(t) for t in ts ])
    pylab.show()
         
if __name__ == '__main__':
    import pylab
    
    x = IDENTITY+ONE.scaled(0.0)
    #dent = x.sqrt(2) #( (x).compose(IDENTITY) - IDENTITY ).divided(x.derivative(),5) #inverse(10,1)
    
    #dent = fit(x, lambda y: y*y-x, 10, 100)
    dent = least_squares(x, lambda y: y*y-x, lambda y: y.scaled(2), lambda y: ONE.scaled(2), 2)
    
    #dent = (dent*dent)#.truncated(20)
    #dent = b
    #r = 0.25
    #a = S_basis([Linear(0.5-r, 0.5+r)])
    #b = a.inverse(1)
    
    
    
    #a = ONE + IDENTITY*(ONE-IDENTITY)
    #a = a.compose(a)
    #b = a.reciprocal(5)
    #a = b.inverse(5)
    #b = a.inverse(5)
    
    #dent = x.compose(a).reciprocal(3).compose(b)
    #dent = b
    #dent = dent + (x-dent.reciprocal(5)).reciprocal(5)
    
    #a = S_basis([Linear(XYZ(0.0,0.0,0.0), XYZ(1.0,1.0,0.0))])
    #b = S_basis([Linear(XYZ(3.0,0.0,0.0), XYZ(0.0,-1.0,0.0))])
    #arc = a + (S_basis([Linear(-a[0].tri(),a[0].tri())])+b).shifted(1)
    #
    #velocity = arc.derivative()
    #speed = velocity.dot(velocity).sqrt(10)
    #position = speed.integral()
    #position = position - ONE.scaled(position(0.0))
    #scaler = position.scaled(1.0/position(1.0))
    #iscaler = scaler.inverse(10, 100)
    #dent = scaler.compose(iscaler)
    #
    #arc = arc.compose(scaler)
    
    #print position(0.0), position(1.0)
    
    #print arc.derivative()(0), arc.derivative()(1)
    
    ts = [ i/100.0 for i in xrange(101) ]
    #pylab.plot([ arc(t).x for t in ts ],[ arc(t).y for t in ts ],'.')
    pylab.plot([ dent(t) for t in ts ])
    pylab.plot([ x(t)**0.5 for t in ts ], 'o')
    pylab.show()
    #print arc(0.5)
    
    #print ONE
    #print ONE.compose(IDENTITY)
    
    #a = IDENTITY*IDENTITY + IDENTITY
    #b = a.inverse(10)
    #print a
    #print b
    #print a.compose(b).truncated(5)

    #x = S_basis([Linear(1.0,2.0)])
    #print (x*x)(3)
    #y = (x*x).sqrt(4)
    #for i in xrange(11):
    #    t = i/10.0
    #    print x(t), y(t)
    #
    #print S_basis([Linear(0.01,4.0)]).sqrt(4)




