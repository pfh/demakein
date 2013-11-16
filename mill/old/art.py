"""

Tools for constructing depth maps.

"""

import numpy, math, sys
from PIL import Image

import raster

def load_mask(filename):
    #return numpy.asarray(Image.open(filename),'uint8')[::-1,:,3] >= 128 
    im = Image.open(filename)
    data = im.tostring()[3::4]
    return numpy.fromstring(data,'uint8').reshape((im.size[1],im.size[0]))[::-1,:] >= 128

def _upscan(f):
    for i, fi in enumerate(f):
        if fi == numpy.inf: continue
        for j in xrange(1,i+1):
            x = fi+j*j
            if f[i-j] < x: break
            f[i-j] = x

def distance2_transform(bitmap):
    f = numpy.where(bitmap, 0, min(bitmap.shape[0],bitmap.shape[1])**2)
    for i in xrange(f.shape[0]):
        _upscan(f[i,:])
        _upscan(f[i,::-1])
    for i in xrange(f.shape[1]):
        _upscan(f[:,i])
        _upscan(f[::-1,i])
    return f




def bulge1(mask):
    ysize,xsize = mask.shape
    height = numpy.zeros(mask.shape,'int16')
    height[mask] = max(mask.shape[0],mask.shape[1])
    
    def apply(points):
        radius = math.sqrt((points[0][0]-points[-1][0])**2+
                           (points[0][1]-points[-1][1])**2)*0.5+0.5
        midx = (points[0][0]+points[-1][0])*0.5
        midy = (points[0][1]+points[-1][1])*0.5
        for x,y in points:
            d = math.sqrt(radius*radius-(x-midx)**2-(y-midy)**2)
            height[y,x] = min(height[y,x], d)
    
    def doline(x0,y0,x1,y1):
        points = raster.line_points2(x0,y0,x1,y1)
        begin = 0
        for i in xrange(len(points)):
            if ( points[i][0] < 0 or points[i][1] < 0 or
                 points[i][0] >= xsize or points[i][1] >= ysize or 
                 not mask[points[i][1],points[i][0]] ):
               if begin != i: 
                   apply(points[begin:i])
               begin = i + 1
        if begin != len(points): 
            apply(points[begin:])
        
        #print points

    #for x in xrange(mask.shape[1]):
    #    doline(x,0,x,mask.shape[0]-1)
    #for y in xrange(mask.shape[0]):
    #    doline(0,y,mask.shape[1]-1,y)
    
    n = 32
    for i in xrange(n):
        a = i*math.pi/n
        dx = math.cos(a)
        dy = math.sin(a)
        if abs(dx) > abs(dy):
            scale = dx/xsize
            dx = xsize
            dy = dy/scale
            for y in xrange(int(-abs(dy)),ysize+int(abs(dy))):
                doline(0,y,dx,y+dy)
        else:
            scale = dy/ysize
            dx = dx/scale
            dy = ysize
            for x in xrange(int(-abs(dx)),xsize+int(abs(dx))):
                doline(x,0,x+dx,dy)
        print dx, dy
    
    return height

def bulge(mask):
    ysize,xsize = mask.shape
    
    print 'Distance2...'
    dist2 = distance2_transform(numpy.logical_not(mask))

    points = [ ]
    radius = min(mask.shape[0],mask.shape[1])//2
    for x in xrange(-radius,radius+1):
        for y in xrange(-radius,radius+1):
            points.append((x*x+y*y,x,y))
    points.sort()
    points = numpy.array(points)
    
    height = numpy.zeros(mask.shape,'int16')
    for y in xrange(mask.shape[0]):
        sys.stdout.write('\r%d '%(mask.shape[0]-y))
        sys.stdout.flush()
        for x in xrange(mask.shape[1]):
            #max_d2 = 0
            #for d2,ox,oy in points:
            #    x2 = x+ox
            #    y2 = y+oy
            #    if (x2 < 0 or x2 >= xsize or y2 < 0 or y2 >= ysize or not mask[y2,x2]):
            #        break
            #    max_d2 = d2
            max_d2 = dist2[y,x]
            if not max_d2: continue
            
            dom = False
            for ox,oy in [(-1,0),(1,0),(0,-1),(0,1)]:
                if x+ox < 0 or y+oy < 0 or x+ox >= xsize or y+oy >= ysize: 
                    continue
                if dist2[y,x] < dist2[y+oy,x+ox]:
                    dom = True
                    break
            
            
            for d2,ox,oy in points:
                if d2 >= max_d2: break
                x2 = x+ox
                y2 = y+oy
                #if d2 and math.sqrt(dist2[y2,x2])+0.001 >= math.sqrt(max_d2)+math.sqrt(d2):
                #    break
                height[y2,x2] = max(height[y2,x2], int(math.sqrt(max_d2-ox*ox-oy*oy)+0.5))
    sys.stdout.write('\r \r')
    return height


def centroid(thing):
    tot = 0.0
    totx = 0.0
    toty = 0.0
    for y in xrange(thing.shape[0]):
        for x in xrange(thing.shape[1]):
            tot += thing[y,x]
            totx += x*thing[y,x]
            toty += y*thing[y,x]
    return totx/tot, toty/tot


def save_raster(filename, res, depth):
    raster.save(dict(res=res,raster=depth.tostring(),shape=depth.shape,dtype=str(depth.dtype)), filename+'.raster')
    
    with open(filename+'.stl','wb') as f:
        def vert(x,y):
            print >> f, 'vertex %f %f %f' % (-float(x)/res,float(y)/res,-float(depth[y,x])/res)
        print >> f, 'solid'
        step = max(1,min(depth.shape[0],depth.shape[1])//200)
        for x in xrange(0,depth.shape[1]-step*2+1,step):
            for y in xrange(0,depth.shape[0]-step*2+1,step):
                print >> f, 'facet normal 0 0 0'
                print >> f, 'outer loop'
                vert(x,y)
                vert(x+step,y+step)
                vert(x+step,y)
                print >> f, 'endloop'
                print >> f, 'endfacet'            
                print >> f, 'facet normal 0 0 0'
                print >> f, 'outer loop'
                vert(x,y)
                vert(x,y+step)
                vert(x+step,y+step)
                print >> f, 'endloop'
                print >> f, 'endfacet'            
        print >> f, 'endsolid'
    

#depth = numpy.zeros(mask.shape,'int16')
#depth[mask] = -res*10

#mask = load_mask('/tmp/exp.png')
#
#print mask.shape
#res = 10
#print res
#
#depth = -bulge(mask)
#
#raster.save(dict(res=res,raster=depth), '/tmp/exp.raster')

# python raster.py view /tmp/exp.raster
# python raster.py cut /tmp/exp wood-ball /tmp/exp.raster
# python decode.py 3 plot /tmp/exp-wood-ball.prn
