
import sys, collections, math

import shape, svg

def sub(a,b):
    return tuple( aa-bb for aa,bb in zip(a,b) )

def dot(a,b):
    return sum( aa*bb for aa,bb in zip(a,b) )

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def sketch(thing, outname):
    print outname,
    sys.stdout.flush()
    
    ox = 0
    oy = 0
    
    pic = svg.SVG()
    pic.require(0,0)
    
    triangles = thing.triangles()
    
    def rot(triangles, x,y,z,angle):
        mat = shape.rotation_matrix(x,y,z,angle)
        return [ [ shape.transform_point_3(mat,item2) for item2 in item ] for item in triangles ]

    def iterator():
        #yield thing, 1
        yield triangles, 1
        
        #item_rot = thing.copy()
        #item_rot.rotate(1,0,0,-90)
        #yield item_rot, 1
        #del item_rot
        yield rot(triangles, 1,0,0,-90), 1
        
        #item_iso = thing.copy()
        #item_iso.rotate(0,0,1,-45, 256)
        #item_iso.rotate(1,0,0,-45, 256)
        #yield item_iso, 0
        #del item_iso        
        yield rot(rot(triangles, 0,0,1,-45), 1,0,0,-45), 0
    
        
#    for (item,showdim) in iterator():
#        extent = item.extent()
    for (this_triangles,showdim) in iterator():
        extent = shape.extent_3(item2 for item in this_triangles for item2 in item)
        
        if extent.xmax-extent.xmin < extent.ymax-extent.ymin:
            ox = pic.max_x + 10
            oy = -pic.max_y
        else:
            ox = 0.0
            oy = -(extent.ymax-extent.ymin)-pic.max_y - 20
        
        ox -= extent.xmin
        oy -= extent.ymin
        
        xmid = (extent.xmin+extent.xmax)*0.5
        ymid = (extent.ymin+extent.ymax)*0.5
        zmid = (extent.zmin+extent.zmax)*0.5
        if showdim:
            pic.text(ox+xmid, -oy-extent.ymax-10, '%.1fmm' % (extent.xmax-extent.xmin))
            pic.text(ox+extent.xmax + 5, -oy-ymid, '%.1fmm' % (extent.ymax-extent.ymin))    
        
        lines = collections.defaultdict(list)
        for tri in this_triangles:
            #a = numpy.array(tri)
            #normal = numpy.cross(a[1]-a[0],a[2]-a[0])
            normal = cross(sub(tri[1],tri[0]),sub(tri[2],tri[0]))
            length = math.sqrt(normal[0]**2+normal[1]**2+normal[2]**2)
            normal = (normal[0]/length,normal[1]/length,normal[2]/length)
            
            lines[(tri[0],tri[1])].append( normal )
            lines[(tri[1],tri[2])].append( normal )
            lines[(tri[2],tri[0])].append( normal )
    
        for a,b in lines:
            if (b,a) not in lines:
                weight = -1.0
                normals = lines[(a,b)]
            else:
                if (b,a) < (a,b): continue
                normals = lines[(a,b)] + lines[(b,a)]
                
                weight = -1.0
                for n1 in lines[(a,b)]:
                    for n2 in lines[(b,a)]:
                        if n1[2]*n2[2] > 0.0:
                            weight = max(weight, dot(n1,n2))
            
            weight = (1.0-weight)*0.5                
            if weight < 0.01: continue                
            weight = min(1.0,weight*2)
    
            outs = 0
            ins = 0
            for n in normals:
                if n[2] <= 1e-6:
                    ins += 1
                if n[2] >= -1e-6:
                    outs += 1
            
            if ins >= 2 and not outs:
                weight *= 0.25
            #elif outs >= 2 and not ins:
            #    weight *= 2.0
            
            pic.line([ (ox+x,-oy-y) for x,y,z in [a,b] ],width=0.2 * weight)
        
        del lines
        
    pic.save(outname)
    print


def run(args):
    for filename in args:
        prefix = filename    
        if prefix[-4:].lower() == '.stl': 
            prefix = prefix[:-4]
        outname = prefix + '-sketch.svg'
    
        item = shape.load_stl(filename)

        sketch(item, outname)
        
   
   
if __name__ == '__main__':
    shape.main(run)