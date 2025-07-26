

from . import shape

class Shape(object):
    def __init__(self, mesh):
        self.mesh = mesh
        self.cleanup()
    
    def copy(self):
        return Shape(self.mesh.copy())
    
    def save(self, filename):
        self.mesh.export(filename)
    
    def is_empty(self):
        return len(self.mesh.faces) == 0
    
    def check(self):
        if not self.mesh.is_volume:
            print("Warning: shape is not a volume")
        #assert self.mesh.is_watertight
        #assert self.mesh.is_winding_consistent
    
    def cleanup(self):
        """ Merge all vertices within a small tolerance of each other. Cull degenerate triangles. """
        import scipy.spatial
        import trimesh
        
        tol = 1e-4
        
        verts = self.mesh.vertices
        faces = self.mesh.faces
        
        # Union find algorithm
        parent = list(range(len(verts)))
        def root(i):
            root = i
            while parent[root] != root:
                root = parent[root]
            while parent[i] != i:
                i, parent[i] = parent[i], root
            return root
        
        # Merge all points within tol of each other
        for i,j in scipy.spatial.KDTree(verts).query_pairs(tol):
            parent[root(j)] = root(i)
        
        # Extract result as a list of groups
        groups = { }
        for i in range(len(verts)):
            r = root(i)
            if r not in groups: groups[r] = [ ]
            groups[r].append(i)
        groups = list(groups.values())
        
        if len(groups) != len(verts):
            print("Consolidated", len(verts)-len(groups), "points")
        
        # Average each group
        new_verts = [ verts[group].mean(0) for group in groups ]
        new_index = { }
        for i, group in enumerate(groups):
            for j in group:
                new_index[j] = i
        
        # Remap indices and discard degenerate triangles
        new_faces = [ ]
        discards = 0
        for item in faces:
            item = [ new_index[i] for i in item ]
            if len(set(item)) < 3: 
                discards += 1
                continue
            new_faces.append(item)
        
        #if discards:
        #    print("Eliminated", discards, "triangles")
        
        self.mesh = trimesh.Trimesh(vertices=new_verts, faces=new_faces)
        self.check()
    
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
        if other.is_empty(): 
            return
        self.mesh = trimesh.boolean.union([ self.mesh, other.mesh ], engine="manifold", check_volume=False)
        self.cleanup()
    
    def remove(self, other):
        import trimesh
        if self.is_empty() or other.is_empty(): 
            return
        self.mesh = trimesh.boolean.difference([ self.mesh, other.mesh ], engine="manifold", check_volume=False)
        self.cleanup()
    
    def clip(self, other):
        import trimesh
        if other.is_empty():
            self.mesh = other.mesh.copy()
            return
        self.mesh = trimesh.boolean.intersection([ self.mesh, other.mesh ], engine="manifold", check_volume=False)
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
    
    # Just provides convex hull
    def polygon_mask(self):
        return hull_2(self.mesh.vertices[:,:2])
        #triangles = self.triangles()
        #
        #things = [ create_polygon_2([ (x,y) for x,y,z in triangle ]) 
        #           for triangle in triangles ]
        #
        #if not things:        
        #    return empty_shape_2()
        #
        #while len(things) > 1:
        #    item = things.pop(-1)
        #    things[len(things)//2].add(item)
        #return things[0]


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

def empty_shape():
    return create([], [])
    


def empty_shape_2():
    import shapely
    return Shape_2(shapely.Polygon())

def create_polygon_2(points):
    import shapely
    return Shape_2(shapely.Polygon(points))

def hull_2(points):
    import shapely
    return Shape_2(shapely.MultiPoint(points).convex_hull)
