
import sys, math
try:
    import numpy
except:
    import numpypy as numpy

sys.path.append('../make-instrument')
import config


def begin_commands(x,y):
    return [ 
        '', '^IN', '!MC0', 'V15.0' '^PR' 'Z0,0,2420', '^PA', '!MC1',
        'Z%(x)d,%(y)d,2420' % locals(), #'Z%(x)d,%(y)d,40' % locals() 
    ]

end_commands = [ '!VZ15.0', '!ZM0', '!MC0', '^IN' ]



GOLDEN = (5**0.5+1)/2

def read_stl(filename):
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

def offset_slices(mata,matb, x,y):
    sy,sx = mata.shape[:2]
    if x >= 0:
        ax1,ax2 = 0,sx-x
        bx1,bx2 = x,sx
    else:
        ax1,ax2 = -x,sx
        bx1,bx2 = 0,sx+x
    if y >= 0:
        ay1,ay2 = 0,sy-y
        by1,by2 = y,sy
    else:
        ay1,ay2 = -y,sy
        by1,by2 = 0,sy+y
    return mata[ay1:ay2,ax1:ax2], matb[by1:by2,bx1:bx2]


def line_param(x1,y1,x2,y2):
    if x2 == x1:
        return 0.0,y1
    m = (y2-y1)/(x2-x1)
    c = y1-m*x1
    return m,c

def line_points2(x1,y1,x2,y2):
    steps = max(abs(x2-x1),abs(y2-y1))
    
    if steps == 0: return [ (x1,y1) ]
    
    result = [ ]
    rounder = steps//2
    for i in xrange(steps+1):
        result.append((
           x1+((x2-x1)*i+rounder)//steps,
           y1+((y2-y1)*i+rounder)//steps,
        ))
    return result

def line_points3(x1,y1,z1,x2,y2,z2):
    steps = max(abs(x2-x1), abs(y2-y1), abs(z2-z1))
    
    if steps == 0: return [ (x1,y1,z1) ]
    
    result = [ ]
    rounder = steps//2
    for i in xrange(steps+1):
        result.append((
           x1+((x2-x1)*i+rounder)//steps,
           y1+((y2-y1)*i+rounder)//steps,
           z1+((z2-z1)*i+rounder)//steps,
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
    
    print rast.shape
    
    for tri in tris:
        draw_triangle(tri, rast)
    
    #return (rast+0.5).astype('int16')
    result = numpy.empty(rast.shape, 'int16')
    for y in xrange(rast.shape[0]):
        for x in xrange(rast.shape[1]):
            result[y,x] = int(rast[y,x]+0.5)
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

def ovoid_mill(radius, zradius):
    return [
        (x,y, int(zradius-numpy.sqrt(radius*radius-x*x-y*y)*zradius/radius +0.5))
        for x,y in circle_points(radius)
    ]

def unmill(rast, mill_points):
    padx = max(item[0] for item in mill_points)
    pady = max(item[1] for item in mill_points)
    sy,sx = rast.shape
    padded = numpy.zeros((sy+pady*2,sx+padx*2), rast.dtype)
    padded[pady:pady+sy,padx:padx+sx] = rast
    
    result = rast.copy()
    
    old_height = 0
    for x,y,height in sorted(mill_points, key=lambda item:item[2]):
        if height != old_height:
            numpy.add(padded, height-old_height, padded)
            old_height = height
            print height
        #numpy.maximum(
        #    result,
        #    padded[pady+y:pady+sy+y,padx+x:padx+sx+x],
        #    result
        #)
        result[:,:] = numpy.maximum(
            result,
            padded[pady+y:pady+sy+y,padx+x:padx+sx+x],
        )
    return result


class Searcher:
    def __init__(self, r, r_ext):
        self.blat = circle_points(r)
        self.ext = circle_points(r_ext)
    
    def reset(self):
        self.todo = self.blat[:] 
        self.seen = set(self.todo)
        self.i = 0
    
    def __iter__(self): 
        return self
    
    def next(self):
        if self.i == len(self.todo): raise StopIteration()
        item = self.todo[self.i]
        self.i += 1
        return item
    
    def good(self, x,y):
        for dx,dy in self.ext:
            item = (x+dx, y+dy)
            if item not in self.seen:
                self.todo.append(item)
                self.seen.add(item)
            
    

"""

Strategy: seek always the point of maximum raster distance
(when local, locally, when run out of local, globally)

Local motion is subject to contraints:
- can't cut above a certain depth
- can't cut more than a certain amount
  - less near final surface

global move requires distance transform
note furthest point
local cutting can't get closer than a fraction of this

"""

@config.Int_flag('res')
@config.Positional('filename')
class Raster(config.Configurable):
    res = 40
    bit_diameter = 3.0
    cutting_depth = 0.5
    vertical_speed = 0.5
    horizontal_speed = 10.0
    movement_speed = 10.0
    tool_up = 2.0 #Distance from cutting surface at which fast motion is allowed
    filename = None

    def setup(self):
        self.rast = raster(self.filename, self.res)
        print 'Loaded'
        self.ysize, self.xsize = self.rast.shape
        self.zmin = numpy.minimum.reduce(self.rast.flat)

        print 'Distance offsets'
        self.increasing_distance_offsets = [ ]
        for x in xrange(-self.xsize,self.xsize+1):
            for y in xrange(-self.ysize,self.ysize+1):
                self.increasing_distance_offsets.append((x,y))
        self.increasing_distance_offsets.sort(key=lambda i: i[0]*i[0]+i[1]*i[1])
        print 'Ok'
        
        self.speed_ratio = self.horizontal_speed / self.vertical_speed
        
        self.res_tool_up = int( self.res*self.tool_up +0.5)
        self.res_cutting_depth = int( self.res*self.cutting_depth )
        self.res_bit_diameter = self.res*self.bit_diameter
        self.res_bit_radius = self.res_bit_diameter*0.5
        self.res_bit_points = end_mill(self.res_bit_radius)
        self.res_clear_points = end_mill(self.res_bit_radius * 2)
        self.res_edge_clearance = max(
            max(abs(x) for x,y,z in self.res_bit_points),
            max(abs(y) for x,y,z in self.res_bit_points)
        )
        
        assert self.res_cutting_depth >= 1

        print 'Unmill'
        self.tool_rast = unmill(self.rast, self.res_bit_points)
        print 'Ok'
        
        self.cut_surface = numpy.zeros(self.rast.shape, self.rast.dtype)
        self.tool_safe = numpy.zeros(self.rast.shape, self.rast.dtype)
        self.tool_safe_depends = [
            [ [(x,y)] for x in xrange(self.xsize) ]
            for y in xrange(self.ysize)
        ]
        self.tool_safe_updates = set()
        
        self.tool_can_cut_to = numpy.maximum(self.tool_rast, -self.res_cutting_depth)
        self.tool_can_cut_to_depends = [
            [ [(x,y)] for x in xrange(self.xsize) ]
            for y in xrange(self.ysize)
        ]
        self.tool_can_cut_to_updates = set()

        #self.heatseeker = numpy.zeros(self.rast.shape, 'float64')
        #self.heatseeker_updates = [ ]
        #for x in xrange(self.xsize):
        #    for y in xrange(self.ysize):
        #        self.heatseeker_updates.append( (0.0, x,y) )

        self.position = (self.res_edge_clearance,self.res_edge_clearance,self.res_tool_up)
        self.path = [ (self.position, True) ]

        self._max_cut_volume = { }

    def max_cut_volume(self, dx,dy,dz):
        if (dx,dy,dz) not in self._max_cut_volume:
            depths = { }
            for x,y,z in self.res_bit_points:
                depths[(x,y)] = z
            
            volume = 0
            for x,y,z in self.res_bit_points:
                x1 = x-dx
                y1 = y-dy
                if (x1,y1) in depths:
                    volume += max(0, min(depths[(x1,y1)]-dz, self.res_cutting_depth))
                else:
                    volume += self.res_cutting_depth
            self._max_cut_volume[(dx,dy,dz)] = volume
            
        return self._max_cut_volume[(dx,dy,dz)]

    def distance_below(self, rast, x,y,z, z_scale=1):
        d = 1<<30
        for dx,dy in self.increasing_distance_offsets:
            this_d = dx*dx+dy*dy
            if this_d >= d: break
            
            x1 = x+dx
            y1 = y+dy
            if x1 < 0 or y1 < 0 or x1 >= self.xsize or y1 >= self.ysize:
                dz = 0
            else:
                dz = min(0, rast[y1,x1]-z) * z_scale
                this_d += dz*dz
            d = min(d, this_d)            
        return numpy.sqrt(d)

    def cone_volume(self, rast, x,y,z, min_radius, max_radius):
        volume = 0
        for dx,dy in self.increasing_distance_offsets:
            this_d = math.sqrt(dx*dx+dy*dy)
            if this_d <= min_radius: continue
            if this_d > max_radius: break

            x1 = x+dx
            y1 = y+dy
            if x1 < 0 or y1 < 0 or x1 >= self.xsize or y1 >= self.ysize:
                z1 = 0
            else:
                z1 = rast[y1,x1]
            
            volume += max(0, z1-z - (this_d-min_radius))

        return volume

    def cut_volume(self, x,y,z, safe=True):
        """ Return volume that would be cut, or None for bad cut """
        c = self.res_edge_clearance
        if x < c or x >= self.xsize-c or y < c or y >= self.ysize-c:
            return None
        
        volume = 0
        for dx,dy,dz in self.res_bit_points:
            amount = max(0, self.cut_surface[y+dy,x+dx] - (z+dz))
            if safe and amount > self.res_cutting_depth: return None
            volume += amount
            
        return volume

    def update_safe(self, x,y):
        if x < 0 or y < 0 or x >= self.xsize or y >= self.ysize: return
        
        value = self.zmin-1
        dep_x = -1
        dep_y = -1
        for dx,dy,dz in self.res_bit_points:
            x1 = x-dx
            y1 = y-dy
            if x1 < 0 or x1 >= self.xsize or y1 < 0 or y1 >= self.ysize:
                new_value = 0
            else:
                new_value = self.cut_surface[y1,x1]-dz
            if new_value > value:
                value = new_value
                dep_x = x1
                dep_y = y1
        value = min(0,value)
        
        if self.tool_safe[y,x] != value:
            self.tool_safe[y,x] = value
            while self.tool_can_cut_to_depends[y][x]:
               self.tool_can_cut_to_updates.add(self.tool_can_cut_to_depends[y][x].pop())
        if dep_x >= 0 and dep_x < self.xsize and dep_y >= 0 and dep_y < self.ysize:
            self.tool_safe_depends[dep_y][dep_x].append( (x,y) )

    def update_can_cut_to(self, x,y):
        if x < 0 or y < 0 or x >= self.xsize or y >= self.ysize: return
        
        value = self.tool_safe[y,x]
        dep_x = x
        dep_y = y
        for dx,dy,dz in self.res_clear_points:
            x1 = x-dx
            y1 = y-dy
            if (x1 < 0 or x1 >= self.xsize or y1 < 0 or y1 >= self.ysize or
                self.tool_rast[y1,x1] >= self.tool_safe[y1,x1]):                             #!!!
                new_value = self.zmin
            else:
                new_value = self.tool_safe[y1,x1]-dz
            if new_value > value:
                value = new_value
                dep_x = x1
                dep_y = y1
        value = min(0,value) - self.res_cutting_depth
        value = max(value, self.tool_rast[y,x])
        self.tool_can_cut_to[y,x] = value
        if (dep_x >= 0 and dep_x < self.xsize and dep_y >= 0 and dep_y < self.ysize and
            value != self.tool_rast[y,x]):
            self.tool_can_cut_to_depends[dep_y][dep_x].append( (x,y) )
    
    def do_updates(self):
        while self.tool_safe_updates:
            self.update_safe(*self.tool_safe_updates.pop())
        while self.tool_can_cut_to_updates:
            self.update_can_cut_to(*self.tool_can_cut_to_updates.pop())

    def _cut(self, x,y,z):
        assert self.tool_rast[y,x] <= z
        assert self.tool_can_cut_to[y,x] <= z

        for dx1,dy1,dz1 in self.res_bit_points:
            x1 = x+dx1
            y1 = y+dy1
            z1 = z+dz1
            if z1 < self.cut_surface[y1,x1]:
                self.cut_surface[y1,x1] = z1
                
                while self.tool_safe_depends[y1][x1]:
                    self.tool_safe_updates.add(self.tool_safe_depends[y1][x1].pop())
    
    def cut(self, x,y,z):
        self._cut(x,y,z)
        self.do_updates()


    def exit_path(self, x,y,z):
        """ Sequence of points from x,y,z to height zero,
            moving away from cut surface. 
        
            Reverse sequence to move in to cutting surface.
        """
        assert self.tool_safe[y,x] <= z

        path = [ ((x,y,z), self.distance_below(self.tool_safe, x,y,z)) ]
        while path[-1][0][2] < 0:
            best = 1<<30
            best_pos = None
            for dx,dy in self.increasing_distance_offsets[:9]:
                x1 = path[-1][0][0] + dx
                y1 = path[-1][0][1] + dy
                z1 = path[-1][0][2] + 1
                if not self.tool_safe[y1,x1] <= z1: 
                    continue
                d = self.distance_below(self.tool_safe, x1,y1,z1)
                if d < best:
                    best = d
                    best_pos = (x1,y1,z1)
            assert best_pos is not None
            path.append((best_pos, best))
        
        return path

    def motion_speed(self, dx,dy,dz):
        if dz >= 0:
            return self.horizontal_speed    
        dist_true = numpy.sqrt(dx*dx+dy*dy+dz*dz)
        dz *= self.speed_ratio
        dist_stretched = numpy.sqrt(dx*dx+dy*dy+dz*dz)
        return self.horizontal_speed * dist_true / dist_stretched

    def move_to(self, x,y,z, fast=False):
        if self.position == (x,y,z):
            return
    
        #if fast:
        #    speed = self.movement_speed
        #else:
        #    dx = x-self.position[0]
        #    dy = y-self.position[1]
        #    dz = (z-self.position[2])
        #    dist_true = numpy.sqrt(dx*dx+dy*dy+dz*dz)
        #    dz *= self.speed_ratio
        #    dist_stretched = numpy.sqrt(dx*dx+dy*dy+dz*dz)
        #    speed = self.horizontal_speed * dist_true / dist_stretched
        # Do this after simplifying path, at end
        
        #print 'goto', x,y,z,fast
        
        if len(self.path) >= 2 and self.path[-2][1] == fast and self.path[-1][1] == fast:
            dx1 = self.path[-1][0][0]-self.path[-2][0][0]
            dy1 = self.path[-1][0][1]-self.path[-2][0][1]
            dz1 = self.path[-1][0][2]-self.path[-2][0][2]
            dx2 = x-self.path[-1][0][0]
            dy2 = y-self.path[-1][0][1]
            dz2 = z-self.path[-1][0][2]
            dot = dx1*dx2+dy1*dy2+dz1*dz2
            l1 = dx1*dx1+dy1*dy1+dz1*dz1
            l2 = dx2*dx2+dy2*dy2+dz2*dz2
            if dot >= 0 and dot*dot == l1*l2:
                print 'omit', self.path[-2], self.path[-1], x,y,z,fast
                del self.path[-1]
            
        self.position = (x,y,z)
        self.path.append((self.position, fast))
    
    def get_commands(self):
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
                dz *= self.speed_ratio
                dist_stretched = numpy.sqrt(dx*dx+dy*dy+dz*dz)            
                new_v = self.horizontal_speed * dist_true / dist_stretched
        
            if v is None or abs(v-new_v) > 0.05:
                commands.append('V%.1f' % new_v)
                v = new_v
            move(new_pos)
            pos = new_pos
        commands.extend( end_commands )
        return commands

    def cut_to(self, x,y,z):
        #print 'cut', x,y,z
        self.cut(x,y,z)
        self.move_to(x,y,z)

    def cut_line_points(self, points):
        for point in points:
            self._cut(*point)
        self.do_updates()
        self.move_to(*points[-1])

    def exit(self):
        if self.position[2] < 0:
            path = self.exit_path(*self.position)
            for pos, dist in path:
                self.move_to(*pos, fast = dist >= self.res_tool_up)
        self.move_to(self.position[0],self.position[1],self.res_tool_up, fast = True)

    def enter(self,x,y,z):
        assert self.position[2] == self.res_tool_up
        path = self.exit_path(x,y,z)[::-1]
        self.move_to(path[0][0][0],path[0][0][1],self.res_tool_up, fast=True)
        for pos, dist in path:
            self.move_to(*pos, fast = dist >= self.res_tool_up)

    def goto(self, x,y,z):
        self.exit()
        self.enter(x,y,z)


    def cut_volume_set(self, points):
        zs = { }
        for x,y,z in points:
            for dx,dy,dz in self.res_bit_points:
                key = (int(x+dx),int(y+dy))
                zs[key] = min(zs.get(key, 0), z+dz)
        
        volume = 0
        for (x,y),z in zs.items():
            volume += max(0, self.cut_surface[y,x] - z)
        return volume

    def max_unclear_z(self):
        unclear = self.tool_safe[ self.tool_safe > self.tool_rast ]
        if not len(unclear): return self.zmin
        return numpy.maximum.reduce(unclear)

    def go(self):
        c = self.res_edge_clearance
        
        #min_z = self.max_unclear_z() - self.res_cutting_depth
        
        searcher = Searcher(self.res_bit_radius * 4, self.res_bit_radius)
        
        self.cut_to(self.position[0],self.position[1],0)
        
        while True:
            x,y,z = self.position

            best = None
            searcher.reset()
            for dx,dy in searcher:
                x1 = x+dx
                y1 = y+dy
                if x1 < c or x1 >= self.xsize-c or y1 < c or y1 >= self.ysize-c: continue

                z1 = self.tool_can_cut_to[y1,x1]
                #if z1 == self.tool_safe[y1,x1]: continue
            
                if dx == 0 and dy == 0:
                    points = [(x,y,z),(x1,y1,z1)]
                else:
                    points = line_points2(x,y,x1,y1)
                    i_end = len(points)-1
                    
                    for x2,y2 in points:
                        z1 = max(z1, self.tool_can_cut_to[y2,x2])

                    grade = float(z-z1) / -i_end
                                            
                    for i,(x2,y2) in enumerate(points):
                        if i == i_end: continue
                        dz = self.tool_can_cut_to[y2,x2] - z1
                        grade = min(grade, float(dz) / (i-i_end))
                    points = [
                        (x2,y2, int(math.ceil(z1+grade*(i-i_end))))
                        for i,(x2,y2) in enumerate(points)
                    ]
                
                assert not (z1 < points[0][2] and z < points[0][2])
                
                rise = points[0][2] - z
                assert rise >= 0
                
                speed = self.motion_speed(x1-x,y1-y,z1-(z+rise))
                length = math.sqrt((x1-x)**2+(y1-y)**2+(z1-(z+rise))**2)
                #if not length: continue
                
                #score = float(self.cut_volume_set(points)) / length * speed
                #score = float(self.cut_volume_set(points)) / (length + self.res_bit_radius) * speed
                
                score = float(sum( max(0,self.tool_safe[y2,x2]-z2) for x2,y2,z2 in points )) 
                
                score += min(self.tool_safe[y1,x1],z1) - self.tool_can_cut_to[y1,x1]
                fall = z1 - self.tool_can_cut_to[y1,x1]
                
                t = rise/self.movement_speed + length/speed + fall/self.vertical_speed                 
                avg_speed = (rise+length+fall) / t
                
                score = score / (t + self.res_bit_diameter/self.horizontal_speed) # math.sqrt(avg_speed / t)
                
                if best is None or score >= best:
                    searcher.good( dx,dy )
                    if score > 0:
                        best = score
                        best_points = points
            
            if not best: break
            
            print best, best_points[0][2]-z, len(best_points)
            self.move_to(*best_points[0])
            self.cut_line_points(best_points)
            self.cut_to(best_points[-1][0],best_points[-1][1],self.tool_can_cut_to[best_points[-1][1],best_points[-1][0]])
            #    continue
            #
            ##min_z = self.max_unclear_z() - self.res_cutting_depth
            #
            #for dx,dy in self.increasing_distance_offsets:
            #    x1 = x+dx
            #    y1 = y+dy
            #    if x1 < c or x1 >= self.xsize-c or y1 < c or y1 >= self.ysize-c: continue
            #    #if self.tool_safe[y1,x1] > min_z and self.tool_can_cut_to[y1,x1] > self.tool_rast[y1,x1]:
            #    if self.tool_can_cut_to[y1,x1] < self.tool_safe[y1,x1]:
            #        self.exit()
            #        self.enter(x1,y1,self.tool_safe[y1,x1])
            #        print 'move to', x1,y1,self.tool_safe[y1,x1]
            #        break
            #else:
            #    break



            
            #for point in best_points:
            #    self.cut_to(*point)
            
    #def update_priority(self, x,y):
    #    c = self.res_edge_clearance
    #    if x < c or x >= self.xsize-c or y < c or y >= self.ysize-c: return
    #    
    #    assert self.tool_safe[y,x] >= self.tool_rast[y,x]
    #    if self.tool_safe[y,x] <= self.tool_rast[y,x]:
    #        self.priorities[y,x] = 0
    #        return
    #    
    #    #self.priorities[y,x] = self.tool_safe[y,x] - self.zmin+1 
    #    
    #    #self.priorities[y,x] = (self.tool_safe[y,x] - self.tool_rast[y,x]) 
    #    #self.priorities[y,x] = self.cut_volume(x,y,self.tool_rast[y,x], safe=False)
    #    
    #    z = max(self.tool_rast[y,x],self.tool_safe[y,x]-self.res_cutting_depth)
    #    self.priorities[y,x] = self.cut_volume(x,y,z, safe=False)
    #    
    #    self.priorities[y,x] += 1e10 - self.cone_volume(self.tool_safe, x,y,z, self.res_bit_radius,self.res_bit_radius*2) 
    #    
    #    #self.priorities[y,x] += 1e10 - self.distance_below(self.tool_rast, x,y,self.tool_safe[y,x])
    #
    #def go(self):
    #    self.priorities = numpy.zeros(self.rast.shape, 'float64')
    #    for y in xrange(self.ysize):
    #        for x in xrange(self.xsize):
    #            self.update_priority(x,y)
    #    
    #    while True:
    #        x,y,z = self.position
    #        while z > self.tool_safe[y,x]:
    #            z -= 1
    #            self.cut_to(x,y,z)            
    #        
    #        best = None
    #        cutoff = (self.res_bit_radius )**2
    #        for dx,dy in self.increasing_distance_offsets:
    #            if best is not None and dx*dx+dy*dy > cutoff: break
    #            x1 = x+dx
    #            y1 = y+dy
    #            if x1 < 0 or x1 >= self.xsize or y1 < 0 or y1 >= self.ysize: continue
    #            this = self.priorities[y1,x1]
    #            if this > 0 and (best is None or this > best):
    #                best = this
    #                best_move = dx,dy
    #       
    #        if best is None: break
    #        
    #        dx,dy = best_move
    #        x1 = x+dx
    #        y1 = y+dy
    #        z1 = max(self.tool_safe[y1,x1]-self.res_cutting_depth,self.tool_rast[y1,x1])
    #        
    #        while True:
    #            dx = x1-x
    #            dy = y1-y            
    #            dz = max(-1, z1-z)
    #            l = float(max(abs(dx),abs(dy)))
    #            if l != 0:
    #                dx = int(math.floor(dx/l+0.5))
    #                dy = int(math.floor(dy/l+0.5))
    #            
    #            while self.tool_rast[y+dy,x+dx] > z+dz or self.cut_volume(x+dx,y+dy,z+dz) is None:
    #                dz += 1
    #            while dz > 1:
    #                z += 1
    #                dz -= 1
    #                self.move_to(x,y,z)
    #            
    #            if not dx and not dy and not dz: break
    #            
    #            x += dx
    #            y += dy
    #            z += dz
    #            assert self.cut_volume(x,y,z) is not None
    #            self.cut_to(x,y,z)
    #            
    #            cutoff = (self.res_bit_radius * 2)**2
    #            for dx, dy in self.increasing_distance_offsets:
    #                if dx*dx+dy*dy > cutoff: break
    #                self.update_priority(x+dx,y+dy)
    #    
        
    #def nibble(self, min_distance=0.0, ideal_rate=0.5):
    #    """ move around cutting into surface
    #    """
    #    ldx = 0
    #    ldy = 0
    #    ldz = 0
    #    while True:
    #        x,y,z = self.position
    #        
    #        best_score = None
    #        best_step = None
    #        for dx,dy in self.increasing_distance_offsets[:9]:
    #            for dz in (-1,0,1):
    #                if dx == 0 and dy == 0 and dz >= 0: continue
    #                    
    #                x1 = x+dx
    #                y1 = y+dy
    #                z1 = z+dz
    #                if x1 < 0 or x1 >= self.xsize or y1 < 0 or y1 >= self.ysize: continue
    #                if z1 >= 0: continue
    #
    #                if self.tool_rast[y1,x1] > z1: continue
    #                if self.tool_safe[y1,x1] <= z1: continue
    #                
    #                volume = self.cut_volume(x1,y1,z1)
    #                if volume is None: continue
    #                
    #                #d = self.distance_below(self.tool_rast, x1,y1,z1)
    #                #if d < min_distance: continue
    #                
    #                d = self.distance_below(self.rast, x1,y1,z1)
    #                
    #                cg = self.cone_gradient(self.tool_safe, x1,y1,z1, self.res_bit_radius, self.res_bit_radius*2)
    #                
    #                max_volume = self.max_cut_volume(dx,dy,dz)
    #                #score = volume * d #( min(float(volume)/max_volume, ideal_rate) )
    #                #score = d-abs( float(volume)/max_volume - ideal_rate )
    #                
    #                #score = dx*ldx+dy*ldy+dz*ldz #+ self.tool_safe[y1,x1]-self.tool_rast[y1,x1] - (( float(volume)/max_volume - ideal_rate )**2)  #+dz*ldz
    #                #score = dx*ldx+dy*ldy+dz*ldz -(( float(volume)/max_volume - ideal_rate )**2)  #+dz*ldz
    #                
    #                score = -cg -(( float(volume)/max_volume - ideal_rate )**2)
    #                
    #                if best_score is None or score > best_score:
    #                    best_score = score
    #                    best_step = (dx,dy,dz)
    #        
    #        if best_score is None: break
    #        
    #        dx,dy,dz = best_step
    #        self.cut_to(x+dx,y+dy,z+dz)
    #
    #        f = 0.1
    #        f1 = 1.0-f
    #        ldx = ldx*f1 + dx*f
    #        ldy = ldy*f1 + dy*f
    #        ldz = ldz*f1 + dz*f / self.speed_ratio
    #
    #def go(self):
    #    while True:
    #        best = None
    #        c = self.res_edge_clearance
    #        for x in xrange(c,self.xsize-c):
    #            for y in xrange(c,self.ysize-c):
    #                z = self.tool_safe[y,x]
    #                if z == self.tool_rast[y,x]: continue
    #                assert self.tool_rast[y,x] < z
    #                
    #                assert self.cut_volume(x,y,z-1)
    #                
    #                this = self.distance_below(self.tool_rast, x,y,z)
    #                if best is not None and this < best: continue
    #                
    #                #vol = self.cut_volume(x,y,z+1)
    #                #if vol is None or vol == 0: continue
    #                
    #                best = this
    #                best_pos = (x,y,z)
    #        
    #        if best is None: break
    #        x,y,z = best_pos
    #        print best_pos, self.tool_rast[y,x],self.tool_safe[y,x], self.cut_volume(x,y,z-1)
    #        self.enter(*best_pos)
    #        self.nibble()
    #        self.exit()
    
    #def x_cuts(self, y, z):
    #    below = self.tool_rast[y,:] <= z
    #    start = 0
    #    segs = [ ]
    #    for x in xrange(len(below)):
    #        if not below[x]:
    #            if start != x:
    #                segs.append((start,x))
    #            start = x+1
    #    return segs
    #
    #def x_scan(self, z_step):
    #    z = -z_step*0.5
    #    y_step = self.bit_diameter * 0.5
    #    y_start = 0.0
    #    while z >= self.zmin:
    #        y = y_start+y_step
    #        while y < self.ysize-y_step:
    #            print z,y,self.x_cuts(y,z)
    #            y += y_step
    #    
    #        y_start = (y_start + GOLDEN*y_step) % y_step
    #        z -= z_step
         

r = Raster()
r.parse(sys.argv[1:])
r.setup()
r.go()

import pickle
f = open('r.dump','wb')
print >> f, r.path
f.close()

f = open('commands.prn','wb')
for command in r.get_commands():
    print >> f, command + ';'
f.close()
print 'wrote commands.prn'

#r.x_scan(1.0*r.res)
#
#import pylab
#
#pylab.imshow(r.cut_surface, origin='lower')
#
##pylab.imshow(
##[
##   [ r.distance_below(r.rast, x,y,0) 
##     for x in xrange(r.xsize) ]
##   for y in xrange(r.ysize)
##],
##origin='lower')
##
##pylab.subplot(3,1,1)
##pylab.imshow(r.rast, origin='lower')
##pylab.subplot(3,1,2)
##pylab.imshow(r.tool_rast, origin='lower')
##pylab.subplot(3,1,3)
##pylab.imshow(unmill(r.tool_rast, ovoid_mill(r.bit_diameter*0.5, r.res * 0.1)), origin='lower')
#pylab.show()
#
