#!/usr/bin/env python

import sys, math, pickle, time, os
try:
    import numpy
except:
    import numpypy as numpy

import nesoni
from nesoni import config


def begin_commands(x,y):
    return [ 
        '', '^IN', '!MC0', 'V15.0' '^PR' 'Z0,0,2420', '^PA', '!MC1',
        'Z%(x)d,%(y)d,2420' % locals(),
    ]

#end_commands = [ '!VZ15.0', '!ZM0', '!MC0', '^IN' ]
end_commands = [ '!MC0' ]


GOLDEN = 2.0/(5**0.5+1.0)

def read_stl(filename):
    """ Returns iterator over triangles in an STL. """
    with open(filename,'rU') as f:
        verts = [ ]
        for line in f:
            parts = line.rstrip().split()
            if parts[0] == 'vertex':
                verts.append((float(parts[1]),float(parts[2]),float(parts[3])))
            elif parts[0] == 'endloop':
                assert len(verts) == 3
                yield verts
                verts = [ ]
        assert not verts


def line_param(x1,y1,x2,y2):
    """ m,c for y=mx+c 
        given two points on line """
    
    if x2 == x1:
        return 0.0,y1
    m = (y2-y1)/(x2-x1)
    c = y1-m*x1
    return m,c

def line_points2(x1,y1,x2,y2):
    """ Integer points near a line between integer coordinates
    """
    steps = int(max(abs(x2-x1),abs(y2-y1)))
    
    if steps == 0: return [ (x1,y1) ]
    
    result = [ ]
    rounder = steps//2
    for i in xrange(steps+1):
        result.append((
           x1+((x2-x1)*i+rounder)//steps,
           y1+((y2-y1)*i+rounder)//steps,
        ))
    return result

def draw_triangle(tri, rast):
    verts = sorted(tri, key=lambda vert: vert[0])
    
    #normal = numpy.cross(tri[1]-tri[0],tri[2]-tri[0])
    a = tri[1]-tri[0]
    b = tri[2]-tri[0]
    normal = numpy.array([
       a[1]*b[2]-a[2]*b[1],
       a[2]*b[0]-a[0]*b[2],
       a[0]*b[1]-a[1]*b[0]
    ])
    
    
    area2 = numpy.sum(normal*normal)
    if area2 < 1e-8: return
    if abs(normal[2]) < 1e-8: return 
    #n0*x+n1*y+n2*z = nc
    #z = nc/n2-n0/n2*x-n1/n2*y
    
    nc = numpy.dot(normal, tri[0])
    
    nc2 = nc/normal[2]
    n02 = normal[0]/normal[2]
    n12 = normal[1]/normal[2]
    
    m1,c1 = line_param(verts[0][0],verts[0][1],verts[1][0],verts[1][1])
    m2,c2 = line_param(verts[1][0],verts[1][1],verts[2][0],verts[2][1])
    m3,c3 = line_param(verts[0][0],verts[0][1],verts[2][0],verts[2][1])

    mz1,cz1 = line_param(verts[0][0],verts[0][2],verts[1][0],verts[1][2])
    mz2,cz2 = line_param(verts[1][0],verts[1][2],verts[2][0],verts[2][2])
    mz3,cz3 = line_param(verts[0][0],verts[0][2],verts[2][0],verts[2][2])
        
    x1 = verts[0][0]
    x2 = verts[1][0]
    x3 = verts[2][0]
    
    maximum = numpy.maximum
    arange = numpy.arange
    ceil = numpy.ceil
        
    if x1 != x2:
        for x in xrange(int(numpy.ceil(x1)),int(x2)+1):
            y1 = m1*x+c1
            y2 = m3*x+c3
            z1 = mz1*x+cz1
            z2 = mz3*x+cz3
            if y1 > y2:
                y1,y2 = y2,y1
            y1 = int(ceil(y1))
            y2 = int(y2)+1
            ys = arange(y1,y2)
            zs = nc2-n02*x-n12*ys
            sl = rast[y1:y2, x]
            #maximum(sl, zs, sl)
            sl[:] = maximum(sl,zs)
    
    if x2 != x3:
        for x in xrange(int(numpy.ceil(x2)),int(x3)+1):
            y1 = m2*x+c2
            y2 = m3*x+c3
            z1 = mz2*x+cz2
            z2 = mz3*x+cz3
            if y1 > y2:
                y1,y2 = y2,y1
            y1 = int(ceil(y1))
            y2 = int(y2)+1
            ys = arange(y1,y2)
            zs = nc2-n02*x-n12*ys
            sl = rast[y1:y2, x]
            #maximum(sl, zs, sl)
            sl[:] = maximum(sl,zs)


def raster(filename, res):
    """ Produce a depth map from an STL file
        at specified resolution. """

    tris = numpy.array(list(read_stl(filename)))
    low = numpy.minimum.reduce(numpy.minimum.reduce(tris,0), 0)
    high = numpy.maximum.reduce(numpy.maximum.reduce(tris,0), 0)
    
    tris[:,:,0] -= low[0]
    tris[:,:,1] -= low[1]
    tris[:,:,2] -= high[2]
    size = high-low
    
    tris *= res
    size *= res
    
    rast = numpy.empty((int(size[1])+1,int(size[0])+1), 'float64')
    rast[:,:] = -size[2]
    
    print 'Raster size:', rast.shape[0], 'x', rast.shape[1]
    
    for tri in tris:
        draw_triangle(tri, rast)
    
    #return (rast+0.5).astype('int16')
    result = numpy.empty(rast.shape, 'int16')
    for y in xrange(rast.shape[0]):
        for x in xrange(rast.shape[1]):
            result[y,x] = int(rast[y,x]+0.5)
    return result



#def circle_mask(radius):
#    import mask
#    
#    rad_up = int(radius+1)
#    ox = rad_up ...plus one?
#    oy = rad_up
#    size = rad_up * 2
#    data = numpy.zeros((size,size),'bool')
#    for y in xrange(size):
#        for x in xrange(size):
#            if (x-ox)**2+(y-oy)**2 <= radius**2:
#                data[y,x] = True
#    return mask.Big_matrix(-ox,-oy,data)
#
#def erode(mat, radius):
#    import mask
#    
#    mask_result = mask.Big_matrix(0,0,mat).erode( circle_mask(radius) )
#    return mask_result.clip(0,0,mat.shape[1],mat.shape[0]).data

#def morph(mask, radius, erode=True):
#    r = int(radius-0.5)
#    if r < 1:
#        return mask.copy()
#    
#    element = cv.CreateStructuringElementEx(r*2+1,r*2+1,r+1,r+1,cv.CV_SHAPE_ELLIPSE)
#    mat = cv.fromarray(mask.astype('uint8'))
#    if erode:
#         cv.Erode(mat, mat, element)
#    else:
#         cv.Dilate(mat, mat, element)
#    return numpy.asarray(mat).astype('bool')
#
#def erode(mask, radius):
#    return morph(mask, radius, True)
#def dilate(mask, radius):
#    return morph(mask, radius, False)

def dilate(mask, radius):
    sy,sx = mask.shape
    
    dilation = mask.copy()    
    dilation_amount = 0
    
    result = numpy.zeros(mask.shape,bool)  
    for y in xrange(int(radius),-1,-1):
        x = int(math.sqrt(radius*radius-y*y))
        while dilation_amount < x:
            dilation_amount += 1
            dilation[:,:sx-dilation_amount] |= mask[:,dilation_amount:]
            dilation[:,dilation_amount:] |= mask[:,:sx-dilation_amount]
        result[:sy-y,:] |= dilation[y:,:]
        result[y:,:] |= dilation[:sy-y,:]
    return result

#m = numpy.zeros((5,5),bool)
#m[2,2] = True
#print dilate(m,0.0)
#foo

def erode(mask, radius):
    return ~dilate(~mask, radius)


def contours(mask):
    """ Return clockwise contours 
        (anticlockwise around holes) 
    """
    import cv
    storage = cv.CreateMemStorage()
    
    cont = cv.FindContours(cv.fromarray(mask.astype('uint8')),storage)    
    if not len(cont): 
        return [ ]
    
    approx = cv.ApproxPoly(cont,storage,cv.CV_POLY_APPROX_DP,1.0, 1)

    item = approx
    result = [ ]
    while item:
        assert item.v_next() is None and item.v_prev() is None
        result.append( list(item) )
        item = item.h_next()
    return result

def circle_points(radius):
    iradius = int(radius)
    points = [ ]
    for y in xrange(-iradius,iradius+1):
        for x in xrange(-iradius,iradius+1):
            if y*y+x*x <= radius*radius:
                points.append((x,y))
    return points

def end_mill(radius):
    return [ (x,y,0) for x,y in circle_points(radius) ]

def ball_mill(radius):
    return [
        (x,y, int(radius-numpy.sqrt(radius*radius-x*x-y*y) +0.5))
        for x,y in circle_points(radius)
    ]

def unmill(rast, mill_points):
    padx = max(item[0] for item in mill_points)
    pady = max(item[1] for item in mill_points)
    sy,sx = rast.shape
    padded = numpy.zeros((sy+pady*2,sx+padx*2), rast.dtype)
    padded[pady:pady+sy,padx:padx+sx] = rast
    
    result = rast.copy()
    
    mill_points = sorted(mill_points, key=lambda item:item[1])
    
    for y in xrange(sy):
        row = result[y]
        sys.stdout.write('\r%d ' % (sy-y))
        sys.stdout.flush()
        for ox,oy,oheight in mill_points:
            numpy.maximum(row,padded[pady+y-oy,padx-ox:padx+sx-ox]-oheight,row)
    
    sys.stdout.write('\r \r')
    sys.stdout.flush()
    
    #old_height = 0
    #for x,y,height in sorted(mill_points, key=lambda item:item[2]):
    #    if height != old_height:
    #        numpy.subtract(padded, height-old_height, padded)
    #        old_height = height
    #    print x,y,height
    #    numpy.maximum(
    #        result,
    #        padded[pady-y:pady+sy-y,padx-x:padx+sx-x],
    #        result
    #    )
    return result




@config.Int_flag('res')
class Miller(config.Configurable):
    res = 40
    
    tool_up = 1.0
    x_speed = 15.0
    y_speed = 7.5
    z_speed = 3.0
    movement_speed = 15.0
    
    # Home z axis occasionally
    tool_zreset = 60.0
    zreset_per = 10
    
    bit_radius = 1.5
    bit_ball = False
    
    cutting_depth = 0.1
    finishing_clearance = 0.0
    finish = True
    finishing_step = 0.1
    
    @property
    def res_tool_up(self): return int(self.res * self.tool_up + 0.5)

    @property
    def res_tool_zreset(self): return int(self.res * self.tool_zreset + 0.5)

    @property
    def res_cutting_depth(self): return int(self.res * self.cutting_depth + 0.5)

    @property
    def res_finishing_clearance(self): return self.res * self.finishing_clearance

    @property
    def res_finishing_step(self): return max(1,int(self.res * self.finishing_step + 0.5))

    @property
    def res_bit_radius(self): return self.res * self.bit_radius
    
    @property
    def res_horizontal_step(self):
        if self.bit_ball:
            return self.res_finishing_step
        else:
            return self.res_bit_radius

    def __init__(self, *args, **kwargs):
        config.Configurable.__init__(self, *args,**kwargs)
        
        self.path = [ ] 
        
        self.drill_points = [ ]
        self.cut_count = 0 #For z reset

    def move_to(self, point, fast=False):
        self.path.append((point, fast))

    def cut_contour(self, z, points, is_exterior, point_score=lambda x,y,z:1):
        """ z and points at res scale """
        
        if is_exterior:
            # Drill as far from previous drill points as possible
            best = 0
            best_point = points[0]
            best_score = 1e30
            for i in xrange(len(points)):
                j = (i+1)%len(points)
                for x1,y1 in line_points2(points[i][0],points[i][1],points[j][0],points[j][1]):
                    score = sum( ((x1-x2)**2+(y1-y2)**2+1)**-1.0 for j,(x2,y2) in enumerate(self.drill_points) )
                    score *= point_score(x1,y1,z)
                    if score < best_score:
                        best = j
                        best_point = x1,y1
                        best_score = score
            
            points = [ best_point ] + points[best:] + points[:best]
            self.drill_points.append(points[0])
            
        elif self.path:
            # Move as little as possible
            last = self.path[-1][0]
        
            best = 0
            best_point = points[0]
            best_score = 1e30
            for i in xrange(len(points)):
                j = (i+1)%len(points)
                for x1,y1 in line_points2(points[i][0],points[i][1],points[j][0],points[j][1]):
                    score = (last[0]-x1)**2 + (last[1]-y1)**2
                    if score < best_score:
                        best = j
                        best_point = x1,y1
                        best_score = score
            
            points = [ best_point ] + points[best:] + points[:best]

        # Home z axis occasionally
        self.cut_count += 1
        if self.cut_count % self.zreset_per == 0 and self.path:
            last = self.path[-1][0]
            self.move_to( ((points[0][0]+last[0])//2, (points[0][1]+last[1])//2, self.res_tool_zreset), True ) 
        
        self.move_to( (points[0][0],points[0][1],self.res_tool_up), True )
        self.move_to( (points[0][0],points[0][1],max(0,z+self.res_tool_up)), True )
        
        for x,y in points:
            self.move_to( (x,y,z), False )
        self.move_to( (points[0][0],points[0][1],z), False )
        
        
        self.move_to( (points[0][0],points[0][1],self.res_tool_up), True )

    #def cut_mask(self, z, mask, clearance=0.0, outline_only=False, down_cut=True):
    #    all_contours = [ ]
    #    
    #    erode_radius = clearance + self.res_bit_radius
    #    while True:
    #         mask = erode(mask, erode_radius)
    #         if not numpy.any(mask.flatten()): 
    #             break    
    #         all_contours.extend( contours(mask) )
    #         erode_radius = self.res_bit_radius
    #         if outline_only: break
    #
    #    for item in all_contours[::-1]:
    #        if down_cut:
    #            item = item[::-1]
    #        self.cut_contour(z, item)        

    def cut_inmask(self, z, mask, in_first=0.0, out_first=0.0, in_step=None, out_step=None, down_cut=True, point_score=lambda x,y,z:1):
        all_contours = [ ]
        
        mask = erode(mask, in_first)
        mask = dilate(mask, out_first)
        is_exterior = True
        while True:
             if not numpy.any(mask.flatten()): 
                 break    
             all_contours.extend([ (is_exterior, item) for item in contours(mask) ])
             if in_step is None: break
             is_exterior = False
             mask = erode(mask, in_step)
             if out_step is not None:
                 mask = dilate(mask, out_step)

        for is_exterior, item in all_contours[::-1]:
            if down_cut:
                item = item[::-1]
            self.cut_contour(z, item, is_exterior, point_score)        

    def cut_raster(self, raster):
        if self.bit_ball:
            bit = ball_mill(self.res_bit_radius)
        else:
            bit = end_mill(self.res_bit_radius)
        print 'Unmilling'
        inraster = unmill(raster, bit)
        print 'Again'
        inagain = unmill(inraster, ball_mill(self.res_bit_radius))
        print 'Done'
        
        def point_score(x,y,z):
            return 1.0 / ((inagain[y,x]-inraster[y,x])+self.res_bit_radius)
        
        spin = 0.0
        
        cut_z = 0
        finish_z = cut_z
        min_z = numpy.minimum.reduce(raster.flatten())         
        while True:
            cut_z -= self.res_cutting_depth
            sys.stdout.write('\r%d %d  %f' % (cut_z, min_z, spin))
            sys.stdout.flush()
            inmask = inraster <= cut_z
            self.cut_inmask(cut_z, inmask, 
                            #in_first =self.res_bit_radius/3.0+self.res_finishing_clearance,
                            #out_first=self.res_bit_radius/3.0, 
                            #in_step  =self.res_bit_radius,
                            #out_step =self.res_bit_radius/3.0,
                            in_first  = self.res_finishing_clearance + self.res_bit_radius*2*spin,
                            out_first = 0.0,
                            in_step   = self.res_bit_radius*2.0,
                            out_step  = 0.0,
                            point_score=point_score)
            
            while finish_z-self.res_finishing_step >= cut_z: 
                finish_z -= self.res_finishing_step
                
                if not self.finish: continue
                
                infinish_mask = inraster <= finish_z                 
                infinish_mask_lower = inraster <= (finish_z-self.res_finishing_step)
                self.cut_inmask(finish_z, 
                                infinish_mask & ~infinish_mask_lower, #erode(infinish_mask_lower,self.res_horizontal_step * 1.5), 
                                in_first =self.res_horizontal_step*2,
                                out_first=self.res_horizontal_step,
                                in_step  =self.res_horizontal_step*2,
                                out_step =self.res_horizontal_step,
                                point_score=point_score,
                                down_cut=False
                                )
                self.cut_inmask(finish_z, infinish_mask, down_cut=False)
            
            if finish_z <= min_z: 
                break
            
            spin = (spin-GOLDEN)%1.0
        print
    
    def get_commands(self):
        speed_ratio_z = self.x_speed / self.z_speed
        speed_ratio_y = self.x_speed / self.y_speed

        commands = [ ]
        commands.extend( begin_commands(self.path[0][0][0]*40//self.res,self.path[0][0][1]*40//self.res) )
        
        def move(pos):
            pos2 = tuple( item*40//self.res for item in pos )
            commands.append('Z%d,%d,%d' % pos2)
        
        move(self.path[0][0])
        pos = self.path[0][0]
        v = None
        for new_pos, fast in self.path[1:]:
            if new_pos == pos: continue
            if fast:
                new_v = self.movement_speed
            else:
                dx = new_pos[0]-pos[0]
                dy = new_pos[1]-pos[1]
                dz = new_pos[2]-pos[2]
                dist_true = numpy.sqrt(dx*dx+dy*dy+dz*dz)
                dy *= speed_ratio_y
                dz *= speed_ratio_z
                dist_stretched = numpy.sqrt(dx*dx+dy*dy+dz*dz)            
                new_v = self.x_speed * dist_true / dist_stretched
        
            if v is None or abs(v-new_v) > 0.05:
                commands.append('V%.1f' % new_v)
                v = new_v
            move(new_pos)
            pos = new_pos
        commands.extend( end_commands )
        return commands

    def save_commands(self, filename):
        with open(filename,'wb') as f:
            for item in self.get_commands():
                print >> f, item+';'

class Wood(Miller):
    pass

class Wood_ball(Miller):
    bit_ball = True

class Fast(Miller):
    x_speed = 15.0
    y_speed = 10.0
    z_speed = 3.0
    movement_speed = 15.0
    
    cutting_depth = 0.3
    finishing_clearance = 0.5
    finish = True
    finishing_step = 0.1


class Cork(Miller):
    x_speed = 10.0
    y_speed = 10.0
    vertical_speed = 3.0
    movement_speed = 15.0
    
    cutting_depth = 0.5
    finishing_clearance = 0.0
    finish = False


MILLERS = {
   'wood-end'  : Wood,
   'wood-ball' : Wood_ball,
   'fast-end'  : Fast,
   'cork-end'  : Cork,
}


def save(object, filename):
    with open(filename,'wb') as f:
        pickle.dump(object,f,2)

def load(filename):
    with open(filename,'rb') as f:
        return pickle.load(f)


@config.Positional('stl', 'STL input file')
@config.Int_flag('res', 'Resolution.')
class Raster(config.Action):
    res = 20
    stl = None
    def run(self):
        prefix = os.path.splitext(self.stl)[0]
        rast = raster(self.stl, self.res)
        save(dict(res=self.res,raster=rast), prefix+'.raster')


@config.Positional('raster', '.raster input file')
@config.String_flag('miller', 'Miller settings')
class Path(config.Action):
    raster = None
    miller = 'wood-ball'
    def run(self):
        prefix = os.path.splitext(self.raster)[0]
        data = load(self.raster)

        template = lambda: MILLERS[self.miller](res=data['res'])
        miller = template()
        
        height, width = data['raster'].shape
        resrad = miller.res_bit_radius
        for x,y,name in [
            (resrad,resrad,'-near-left.prn'),
            (width-1-resrad,resrad,'-near-right.prn'),
            (resrad,height-1-resrad,'-far-left.prn'),
            (width-1-resrad,height-1-resrad,'-far-right.prn'),
            (width//2,height//2,'-middle.prn'),
            ]:
            miller = template()
            miller.move_to((x,y,miller.res_tool_up), True)
            miller.move_to((x,y,0), False)
            miller.save_commands(prefix+name)
        
        miller = template()
        miller.cut_raster(data['raster'])
        miller.save_commands(prefix+'-'+self.miller+'.prn')


@config.Main_section('stls', 'STL files.', empty_is_ok=False)
@config.Configurable_section('raster', 'raster: parameters')
@config.Configurable_section('path', 'path: parameters')
class All(config.Action):
    stls = [ ]
    raster = Raster()
    path = Path()
    
    def run(self):
        with nesoni.Stage() as stage:
            for filename in self.stls:
                 stage.process(self.do_one, filename)    
    
    def do_one(self, filename):
        prefix = os.path.splitext(filename)[0]
        self.raster(filename).run()
        self.path(prefix+'.raster').run()


if __name__ == '__main__':
    nesoni.run_toolbox([
        Raster,
        Path,
        All,
        ], show_make_flags=False)

#
#def do_cut(prefix, miller_name, filename):
#    data = load(filename)    
#    if isinstance(data['raster'], str):
#        data['raster'] = numpy.fromstring(data['raster'],data['dtype']).reshape(data['shape'])
#    
#    template = lambda: MILLERS[miller_name](res=data['res'])
#    miller = template()
#
#    height, width = data['raster'].shape
#    resrad = miller.res_bit_radius
#    for x,y,name in [
#        (resrad,resrad,'-near-left.prn'),
#        (width-1-resrad,resrad,'-near-right.prn'),
#        (resrad,height-1-resrad,'-far-left.prn'),
#        (width-1-resrad,height-1-resrad,'-far-right.prn'),
#        (width//2,height//2,'-middle.prn'),
#    ]:
#        miller = template()
#        miller.move_to((x,y,miller.res_tool_up), True)
#        miller.move_to((x,y,0), False)
#        miller.save_commands(prefix+name)
#
#    miller.cut_raster(data['raster'])
#    miller.save_commands(prefix+'-'+miller_name+'.prn')
#
#
#if __name__ == '__main__':
#    args = sys.argv[1:]
#    command, args = args[0],args[1:]
#    if command == 'raster':
#        [prefix, res, stl] = args
#        res = int(res)
#        do_raster(prefix, res, stl)
#    
#    elif command == 'cut':
#        [prefix, miller, filename] = args
#        
#        do_cut(prefix, miller, filename)
#    
#    elif command == 'all':
#        miller = args[0]
#        assert miller in MILLERS
#        filenames = args[1:]
#        for filename in filenames:
#            assert filename.endswith('.stl')
#        for filename in filenames:
#            print filename
#            do_raster(filename[:-4], 20, filename)
#            do_cut(filename[:-4],miller,filename[:-4]+'.raster')
#    
#    elif command == 'view':
#        [filename] = args
#        data = load(filename)
#        if isinstance(data['raster'], str):
#            data['raster'] = numpy.fromstring(data['raster'],data['dtype']).reshape(data['shape'])
#        
#        im = data['raster'].astype('float')
#        
#        print float(im.shape[1])/data['res'],'x',float(im.shape[0])/data['res'],'x',-numpy.minimum.reduce(im.flat) / data['res'], 'mm'
#        
#        im -= numpy.minimum.reduce(im.flat)
#        im /= numpy.maximum.reduce(im.flat)
#
#        import cv
#        cim = cv.fromarray( numpy.tile(im[::-1,:,None].copy(),(1,1,3)) )
#        mat = cv.CreateMat(im.shape[0]//4, im.shape[1]//4, cv.CV_64FC3)
#        print cim.type, mat.type
#        cv.Resize(cim, mat)
#        cv.ShowImage('thing', mat)
#        cv.WaitKey()
#
#        #
#        #cim = cv.fromarray( numpy.tile(im[:,:,None],(1,1,3)) )
#        #
#        #for d in xrange(-10,-300,-2):
#        #    foo = data['raster'] <= d   
#        #    
#        #    print sum(foo.flat)
#        #    foo = erode(foo, 100)
#        #    print sum(foo.flat)
#        #    
#        #    c = contours(foo)
#        #    
#        #    for contour in c:
#        #        for i in xrange(len(contour)):
#        #            cv.Line(cim, contour[i],contour[(i+1)%len(contour)], (1,0,0))
#        #            flip = cv.fromarray(numpy.asarray(cim)[::-1].copy())
#        #        cv.ShowImage('thing', flip)
#        #        cv.WaitKey(10)
#            
#            #
#            #     
#            #storage = cv.CreateMemStorage()
#            #cont = cv.FindContours(cv.fromarray(foo.astype('uint8')),storage)
#            #approx = cv.ApproxPoly(cont,storage,cv.CV_POLY_APPROX_DP,1.0, 1)
#            #
#            ##print list(approx)
#            ##print dir(approx)
#            ##print approx.h_prev(),approx.h_next(),approx.v_prev(),approx.v_next()
#            #
#            ##cv.DrawContours(cim, cont, (0,0,1), (0,0,1), 0)
#            #cv.DrawContours(cim, approx, (1,0,0), (0,1,0), 0)
#            #
#            ##cv.DrawContours(cim, list(approx), (1,0,0),(0,1,0), 0)
#            #
#            ##for x,y in approx:
#            ##    cim[y,x] = (1,0,1)
#            #
#            #for x,y in cont:
#            #    #cim[y,x] = (0,0,1)
#            #    cv.Circle(cim, (x,y), 2, (0,0,1))
#            #
#            #    flip = cv.fromarray(numpy.asarray(cim)[::-1].copy())
#            #    cv.ShowImage('thing', flip)
#            #    cv.WaitKey(10)
#        cv.WaitKey()
#        
#    else:
#        assert False
#

