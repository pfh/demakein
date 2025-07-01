

from . import shape

class Shape(object):
    def __init__(self, mesh):
        self.mesh = mesh
    
    def copy(self):
        return Shape(self.mesh.copy())
    
    def save(self, filename):
        self.mesh.export(filename)
    
    def cleanup(self):
        #old = len(self.mesh.faces)
        self.mesh.update_faces(self.mesh.nondegenerate_faces())
        #new = len(self.mesh.faces)
        #if old != new:
        #    print("Cleaned degenerate faces", old, new, new-old)
    
    def triangles(self):
        return [ tuple(map(tuple,tri)) for tri in self.mesh.triangles.tolist() ]
    
    def extent(self):
        b = self.mesh.bounds
        return shape.Limits(b[0,0],b[1,0],b[0,1],b[1,1],b[0,2],b[1,2])
    
    def move(self, x,y,z):
        self.mesh.apply_transform(
            [[1,0,0,x],
             [0,1,0,y],
             [0,0,1,z],
             [0,0,0,1]])
    
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


def create(verts, faces, name=None):
    import trimesh
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    return Shape(mesh)


