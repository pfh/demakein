"""

Matrices at arbitrary offsets

"""

import numpy, subprocess, os

def bound_intersection(bounds1, bounds2):
    (x1,y1,width1,height1) = bounds1
    (x2,y2,width2,height2) = bounds2
    if width1 == 0 or height1 == 0: return bounds2
    if width2 == 0 or height2 == 0: return bounds1
    x = max(x1,x2)
    y = max(y1,y2)
    width = max(0, min(x1+width1,x2+width2)-x)
    height = max(0, min(y1+height1,y2+height2)-y)
    return (x,y,width,height)

def bound_union(bounds1, bounds2):
    (x1,y1,width1,height1) = bounds1
    (x2,y2,width2,height2) = bounds2
    if width1 == 0 or height1 == 0: return bounds2
    if width2 == 0 or height2 == 0: return bounds1
    x = min(x1,x2)
    y = min(y1,y2)
    width = max(x1+width1,x2+width2)-x
    height = max(y1+height1,y2+height2)-y
    return (x,y,width,height)

class Big_matrix(object):
    def __init__(self, x,y,data):
        self.x = x
        self.y = y
        self.height, self.width = data.shape[:2]
        self.data = data
    
    def shift(self, x,y):
        return Big_matrix(self.x+x,self.y+y,self.data)
    
    def bounds(self):
        return (self.x,self.y,self.width,self.height)
    
    def clip(self, x,y,width,height):
        if y == self.y and x == self.x and width == self.width and height == self.height: 
            return self
        result = zeros(x,y,width,height,self.data.dtype)
        x1 = max(self.x,x)
        x2 = min(self.x+self.width,x+width)
        y1 = max(self.y,y)
        y2 = min(self.y+self.height,y+height)
        if y1 < y2 and x1 < x2:
            result.data[y1-y:y2-y,x1-x:x2-x] = self.data[y1-self.y:y2-self.y,x1-self.x:x2-self.x]
        return result
    
    def apply(self, other, bounds, operation):
        a = self.clip(*bounds)
        b = other.clip(*bounds)
        return Big_matrix(a.x,a.y,operation(a.data,b.data))
    
    def union_apply(self, other, operation):
        bounds = bound_union(self.bounds(),other.bounds())
        return self.apply(other, bounds, operation)
        
    def intersection_apply(self, other, operation):
        bounds = bound_intersection(self.bounds(),other.bounds())
        return self.apply(other, bounds, operation)
    
    def __and__(self,other):
        return self.intersection_apply(other,lambda a,b: a&b)
    def __or__(self,other):
        return self.union_apply(other,lambda a,b: a|b)
    
    def and_not(self, other):
        return self.apply(other, self.bounds(), lambda a,b: a&~b)
    
    def spans(self):
        for y in range(self.height):
            start = 0
            for x in range(self.width):
                if not self.data[y,x]:
                    if start != x:
                        yield y+self.y, start+self.x, x+self.x
                    start = x+1
            if start != self.width:
                yield y+self.y, start+self.x, self.width+self.x

    def morph(self, mask, operation):
        spans = [ None, self ]
        def get_span(n):
            while len(spans) <= n:
                spans.append(operation(spans[-1],self.shift(len(spans)-1,0)))
            return spans[n]
        result = None
        for y,x1,x2 in mask.spans():
            span = get_span(x2-x1).shift(x1,y)
            if result is None:
                result = span
            else:
                result = operation(result, span)
        assert result is not None, 'empty mask'
        return result
    
    def dilate(self,mask):
        return self.morph(mask, lambda a,b: a|b)
    
    def erode(self,mask):
        return self.morph(mask, lambda a,b: a&b)
    
    def open(self,mask):
        return self.erode(mask).dilate(mask)
    
    def close(self,mask):
        return self.dilate(mask).erode(mask)

    def trace(self,res=1.0):
        return trace(self,res)


def ones(x,y,width,height,type=bool):
    return Big_matrix(x,y, numpy.ones((height,width),type))

def zeros(x,y,width,height,type=bool):
    return Big_matrix(x,y, numpy.zeros((height,width),type))

def zero(type=bool):
    return zeros(0,0,0,0,type)






def line_param(x1,y1,x2,y2):
    if x2 == x1:
        return 0.0,y1
    m = (y2-y1)/(x2-x1)
    c = y1-m*x1
    return m,c

def int_floor(x):
    return int(numpy.floor(x))

def int_ceil(x):
    return int(numpy.ceil(x))

def make_mask(lines):
    base_x = int_floor(min( min(x1,x2) for x1,y1,x2,y2 in lines ))
    base_y = int_floor(min( min(y1,y2) for x1,y1,x2,y2 in lines ))
    width  = int_ceil(max( max(x1,x2) for x1,y1,x2,y2 in lines )) - base_x + 1
    height = int_ceil(max( max(y1,y2) for x1,y1,x2,y2 in lines )) - base_y + 1
    
    line_count = { }
    for x1,y1,x2,y2 in lines:
        if x1 < x2:
            n = 1
            key = (x1,y1,x2,y2)
        else:
            n = -1
            key = (x2,y2,x1,y1)
        line_count[key] = line_count.get(key,0) + n
    
    count = numpy.zeros((height,width), 'int32')
    
    for (x1,y1,x2,y2), n in line_count.items():
        if n == 0: continue 
        ix1 = int_ceil(x1)
        ix2 = int_ceil(x2)
        if ix1 == ix2: continue

        m,c = line_param(x1,y1,x2,y2)
        for x in range(ix1,ix2):
            y = int_ceil(m*x+c)
            count[y-base_y,x-base_x] += n
    
    for y in range(1, height):
        count[y] += count[y-1]

    return Big_matrix(base_x, base_y, count > 0)




def write_pbm(f, data):
    f.write('P1\n%d %d\n' % (data.shape[1],data.shape[0]))
    for line in data:
        f.write(''.join([ '1' if item else '0' for item in line ]))
        #f.write('\n')

def save(prefix, mask):
    with open(prefix+'.pbm','wt') as f: write_pbm(f, mask.data)
    os.system('pnmtopng <%s.pbm >%s.png' % (prefix,prefix))


def trace(mask, res=1.0):
    import shape
    
    process = subprocess.Popen([
        'potrace', '-a', '-1', '-t', '0', '-u', '100', '-b', 'svg'
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    
    write_pbm(process.stdin, mask.data)

    from xml.etree import ElementTree
    doc = ElementTree.parse(process.stdout)

    loops = [ ]    
    for path in doc.getroot().findall('{http://www.w3.org/2000/svg}g/{http://www.w3.org/2000/svg}path'):
        items = path.attrib['d'].split()
        items = [ int(item.strip('Mczl')) for item in items ]
        for i in range(2,len(items)):
            items[i] += items[i-2]
        
        loop = [ ]
        for i in range(len(items)//2):
            loop.append( (mask.x+items[i*2]*0.01-0.5,mask.y+mask.data.shape[0]-items[i*2+1]*0.01-0.5) )
        
        i = 0
        while i < len(loop):
            if loop[i] == loop[(i+1)%len(loop)]:
                del loop[i]
            else:
                i += 1
        
        assert len(loop) == len(set(loop))        
        
        loops.append( shape.Loop(loop[::-1]).scale(1.0/res) )
    return loops
    
    #loop = [ ]
    #loops = [ loop ]
    #for line in process.stdout:
    #     parts = line.rstrip().split()
    #     if parts[0] != 'TYPE:': continue
    #     assert parts[2] == 'X:' and parts[4] == 'Y:'
    #     if parts[1] == '2': continue
    #     if parts[1] == '3':
    #          loop = [ ]
    #          loops.append(loop)
    #     loop.append( (0.5+mask.x+int(parts[3])*0.01,0.5+mask.y+int(parts[5])*0.01) )
    #return [ shape.Loop(item[::-1]) for item in loops ]


if __name__ == '__main__':
    import shape
    loop = shape.Loop( shape.circle(50.0)[:50] )
    with open('/tmp/test.pbm','wt') as f: write_pbm(f,loop.mask(1.0).data)
    print( max(x for x,y in loop) - min(x for x,y in loop) )
    for i in range(10):
         mask = loop.mask(1.0)
         with open('/tmp/test2.pbm','wt') as f: write_pbm(f,mask.data)
         [ loop ] = trace(mask)
         print( max(x for x,y in loop), min(x for x,y in loop) )
         print( max(y for x,y in loop), min(y for x,y in loop) )
         print()
         #print( min(x for x,y in loop) )
    #mask[5,5] = 0
    with open('/tmp/test2.pbm','wt') as f: write_pbm(f,mask.data)
    
    
    #mask = shape.circle(20).mask(40)
    #
    #thing = zeros(0,0,100,100)
    #thing.data[:,:] = True
    #
    #thing = thing | thing.shift(100,100)
    #thing = thing.close(mask)
    #with open('/tmp/test3.pbm','wt') as f: write_pbm(f,thing.data)
    
    

