

from . import shape

class Shape(object):
    def __init__(self, mesh):
        self.mesh = mesh
        
        # Sometimes I create meshes with identical vertices, eg at the tip of an extrusion
        self.cleanup()
        #self.check()
    
    def check(self):
        assert self.mesh.is_volume
        assert self.mesh.is_watertight
        assert self.mesh.is_winding_consistent
    
    def copy(self):
        return Shape(self.mesh.copy())
    
    def save(self, filename):
        self.mesh.export(filename)
    
    def cleanup(self):
        # TODO: this may be fragile!
        old = len(self.mesh.faces)
        self.mesh.merge_vertices(digits_vertex=5) # Merges based on round(position*1e5)
        self.mesh.update_faces(self.mesh.nondegenerate_faces(height=None))
        new = len(self.mesh.faces)
        if old != new:
            print("Cleaned", old-new, "triangles.")
        
        self.check()
        #import trimesh
        #trimesh.repair.fill_holes(self.mesh)
        #print(self.mesh.is_volume, self.mesh.is_watertight, self.mesh.is_winding_consistent)
    
    def triangles(self):
        return [ tuple(map(tuple,tri)) for tri in self.mesh.triangles.tolist() ]
    
    def extent(self):
        b = self.mesh.bounds
        return shape.Limits(b[0,0],b[1,0],b[0,1],b[1,1],b[0,2],b[1,2])
    
    def size(self):
        xmin,xmax,ymin,ymax,zmin,zmax = self.extent()
        return xmax-xmin,ymax-ymin,zmax-zmin
    
    def move(self, x,y,z):
        self.mesh.apply_transform(
            [[1,0,0,x],
             [0,1,0,y],
             [0,0,1,z],
             [0,0,0,1]])
    
    def position_nicely(self):
        e = self.extent()
        self.move(-0.5*(e.xmin+e.xmax),-0.5*(e.ymin+e.ymax),-e.zmin)
    
    def rotate(self, x,y,z,angle):
        r = shape.rotation_matrix(x,y,z,angle)
        self.mesh.apply_transform(
            [[ r[0][0],r[0][1],r[0][2],0],
             [ r[1][0],r[1][1],r[1][2],0],
             [ r[2][0],r[2][1],r[2][2],0],
             [       0,      0,      0,1]])
    
    def add(self, other):
        import trimesh
        self.mesh = trimesh.boolean.union([ self.mesh, other.mesh ], engine="manifold")
        self.cleanup()
    
    def remove(self, other):
        import trimesh
        self.mesh = trimesh.boolean.difference([ self.mesh, other.mesh ], engine="manifold")
        self.cleanup()
    
    def clip(self, other):
        import trimesh
        self.mesh = trimesh.boolean.intersection([ self.mesh, other.mesh ], engine="manifold")
        self.cleanup()
    
    # Convex hull rather than Minkowski sum used in CGAL engine
    def mill_hole(self, pad_cone):
        import trimesh
        hull = trimesh.convex.hull_points(self.mesh.vertices[:,:2])
        
        points = [ ]
        for x1,y1 in hull.tolist():
            for x2,y2,z2 in pad_cone.mesh.vertices.tolist():
                points.append((x1+x2,y1+y2,z2))
        
        result = Shape(trimesh.convex.convex_hull(points))
        result.cleanup()
        return result
    
    def polygon_mask(self):
        triangles = self.triangles()
        
        things = [ create_polygon_2([ (x,y) for x,y,z in triangle ]) 
                   for triangle in triangles ]

        if not things:        
            return empty_shape_2()

        while len(things) > 1:
            item = things.pop(-1)
            things[len(things)//2].add(item)
        return things[0]


class Shape_2(object):
    def __init__(self, geom):
        self.geom = geom
    
    def copy(self):
        return Shape_2(self.geom)
    
    def extent(self):
        xmin, ymin, xmax, ymax = self.geom.bounds
        return shape.Limits_2(xmin, xmax, ymin, ymax)
    
    def move(self, x,y):
        import shapely
        self.geom = shapely.transform(self.geom, lambda p: p + (x,y))
    
    def intersects(self, other):
        # Includes touching borders. Is this right?
        return self.geom.intersects(other.geom)
    
    def add(self, other):
        import shapely
        self.geom = shapely.union(self.geom, other.geom)
    
    def loop(self, holes):
        assert not holes
        return shape.Loop( list(self.geom.exterior.coords) )
    
    def offset_curve(self, amount, quality=None):
        """ +ve dilation
            -ve erosion """
        if amount == 0.0:
            return self.copy()
        
        import shapely
        return Shape_2( shapely.buffer(self.geom, amount) )



def create(verts, faces, name=None):
    import trimesh
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    return Shape(mesh)

def empty_shape_2():
    import shapely
    return Shape_2(shapely.Polygon())

def create_polygon_2(points):
    import shapely
    return Shape_2(shapely.Polygon(points))
