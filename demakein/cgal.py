
import sys, os, math

import cpp

import shape

CODE = r"""
#include <CGAL/Exact_predicates_exact_constructions_kernel.h>
#include <CGAL/Simple_homogeneous.h>

#include <CGAL/Nef_polyhedron_3.h>
#include <CGAL/Polyhedron_incremental_builder_3.h>
#include <CGAL/Polyhedron_3.h>
#include <CGAL/minkowski_sum_3.h>

#include <CGAL/Polygon_2.h>
#include <CGAL/Polygon_with_holes_2.h>
#include <CGAL/Polygon_set_2.h>
#include <CGAL/Boolean_set_operations_2.h>
#include <CGAL/minkowski_sum_2.h>
#include <CGAL/Small_side_angle_bisector_decomposition_2.h>
#include <CGAL/connect_holes.h>

#include <vector>
#include <iostream>
#include <sstream>

//typedef CGAL::Exact_predicates_exact_constructions_kernel Kernel;
//typedef CGAL::Extended_homogeneous<CGAL::Gmpz>            Kernel;
//typedef CGAL::Cartesian<CGAL::Gmpq>                       Kernel;
//typedef CGAL::Homogeneous<CGAL::Gmpz>                     Kernel;

//2024-04-27 Formerly this worked:
//typedef CGAL::Simple_homogeneous<CGAL::Gmpz>                Kernel;

//2024-04-27 This is now needed (Ubuntu 22.04.4, libcgal 5.4-1): 
typedef CGAL::Simple_cartesian<CGAL::Gmpq>                Kernel;


typedef Kernel::Point_3                                   Point_3;
typedef Kernel::Vector_3                                  Vector_3;
typedef CGAL::Polyhedron_3<Kernel>                        Polyhedron;
typedef CGAL::Nef_polyhedron_3<Kernel>                    Nef_polyhedron;
typedef Polyhedron::HalfedgeDS                            HalfedgeDS;
typedef CGAL::Aff_transformation_3<Kernel>                Aff_transformation_3;

typedef Kernel::Point_2                                   Point_2;
typedef Kernel::Vector_2                                  Vector_2;
typedef CGAL::Polygon_2<Kernel>                           Polygon_2;
typedef CGAL::Polygon_with_holes_2<Kernel>                Polygon_with_holes_2;
typedef CGAL::Polygon_set_2<Kernel>                       Polygon_set_2;
typedef CGAL::Aff_transformation_2<Kernel>                Aff_transformation_2;
typedef CGAL::Small_side_angle_bisector_decomposition_2<Kernel> Decomposition_strategy;

class Build_polyhedron : public CGAL::Modifier_base<HalfedgeDS> {
public:
    std::vector<Kernel::Point_3> points;
    std::vector< std::vector<int> > facets;

    Build_polyhedron() {}
    void operator()( HalfedgeDS& hds) {
        CGAL::Polyhedron_incremental_builder_3<HalfedgeDS> B( hds, true);
         
        B.begin_surface( points.size(), facets.size() );
    
        for(std::vector<Kernel::Point_3>::iterator it = points.begin();
            it < points.end();
            it++) {
            B.add_vertex(*it);
        }
        
        for(std::vector< std::vector<int> >::iterator it = facets.begin();
            it < facets.end();
            it++) {
            B.begin_facet();
            for(std::vector<int>::iterator it1 = it->begin();
                it1 < it->end();
                it1++) {
                B.add_vertex_to_facet(*it1);
            }
            B.end_facet();
        }
        
        B.end_surface();
    }
};

"""

CMAKE_CODE = r"""

find_package(CGAL REQUIRED)

include(${CGAL_USE_FILE})

"""

M = cpp.Module(os.path.join(os.path.expanduser('~'),'.demakein'), CODE, CMAKE_CODE)

def int_round(value):
    return int(math.floor(value+0.5))

def rotation_matrix(x,y,z,angle):
    length = math.sqrt(x*x+y*y+z*z)
    x = x/length
    y = y/length
    z = z/length
    angle = angle * (math.pi/180.0)
    c = math.cos(angle)
    s = math.sin(angle)
    return [
        [ c+x*x*(1-c),   x*y*(1-c)-z*s, x*z*(1-c)+y*s ],
        [ y*x*(1-c)+z*s, c+y*y*(1-c),   y*z*(1-c)-x*s ],
        [ z*x*(1-c)-y*s, z*y*(1-c)+x*s, c+z*z*(1-c)   ],
    ]

def transform_point_3(matrix, point):
    return tuple(
        sum( matrix[i][j] * point[j] for j in (0,1,2) )
        for i in (0,1,2)
    )

def extent_3(points):
    xs = []
    ys = []
    zs = []
    for point in points:
        xs.append(point[0])
        ys.append(point[1])
        zs.append(point[2])
    return shape.Limits(min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))


class Shape(object):
    """ Wrapper around Nef_polyhedron """
    
    def __init__(self, nef):
        self.nef = nef

    def copy(self):
        return Shape(M.new('Nef_polyhedron(a)',a=self.nef))

    def extent(self):
        xs = []
        ys = []
        zs = []
        for tri in self.iter_triangles(): #Possibly slow?
            for point in tri:
                xs.append(point[0])
                ys.append(point[1])
                zs.append(point[2])
        #for vertex in M.iterate('a.vertices_begin()','a.vertices_end()',a=self.nef):
        #    point = M('a.point()',a=vertex)
        #    xs.append(M('CGAL::to_double(a.x())',a=point))
        #    ys.append(M('CGAL::to_double(a.y())',a=point))
        #    zs.append(M('CGAL::to_double(a.z())',a=point))
        return shape.Limits(min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))
    
    def size(self):
        xmin,xmax,ymin,ymax,zmin,zmax = self.extent()
        return xmax-xmin,ymax-ymin,zmax-zmin

    def iter_triangles(self):
        point_cache = { }
        def get_cache(p):
            if p not in point_cache:
                point_cache[p] = p
            return point_cache[p]
        
        polyhedron = M.new('Polyhedron()')
        #M('a.interior().convert_to_polyhedron(b)',a=self.nef,b=polyhedron)
        M('a.convert_to_polyhedron(b)',a=self.nef,b=polyhedron)
        
        #assert M('(int)a.is_valid(true, 3)',a=polyhedron)
        
        triangles = [ ]
        for item in M.iterate('a.facets_begin()','a.facets_end()',a=polyhedron):
            verts = [ ]
            for item2 in M.circulate('a.facet_begin()',a=item):
                #point = M('a.vertex()->point()',a=item2)
                verts.append(get_cache((
                     M('CGAL::to_double(a.vertex()->point().x())',a=item2),
                     M('CGAL::to_double(a.vertex()->point().y())',a=item2),
                     M('CGAL::to_double(a.vertex()->point().z())',a=item2),
                )))
                
            assert len(verts) == 3
            yield tuple(verts)
    
    def triangles(self):
        return list(self.iter_triangles())

    def save(self, filename):
        print filename,
        sys.stdout.flush()
        with open(filename,'wb') as f:
            print >> f, 'solid'
            n = 0
            for tri in self.iter_triangles():
                n += 1
                print >> f, 'facet normal 0 0 0'
                print >> f, 'outer loop'
                for vert in tri:
                    print >> f, 'vertex %f %f %f' % tuple(vert)
                print >> f, 'endloop'
                print >> f, 'endfacet'
            print >> f, 'endsolid'
        print n, 'triangles'

    def remove(self, other):
        M.do('a -= b',a=self.nef,b=other.nef)

    def add(self, other):
        M.do('a += b',a=self.nef,b=other.nef)

    def clip(self, other):
        M.do('a *= b',a=self.nef,b=other.nef)

    def inverse(self):
        return Shape(M('!a',a=self.nef))

    def minkowski_sum(self, other):
        return Shape(M('CGAL::minkowski_sum_3(a,b)',a=self.nef,b=other.nef))

    def rotate(self, x,y,z,angle, accuracy=1<<16):
        if not angle: return    
        rot = rotation_matrix(x,y,z,angle)        
        transform = M.call('Aff_transformation_3',
            *[ int_round(item*accuracy) for row in rot for item in row ] + [ accuracy ]
        )
        M.do('a.transform(b)',a=self.nef, b=transform)
        
        # Rotation of a nef appears to be extremely memory hungry
        # TODO: retain exact representation
        #
        #verts = [ ]
        #vert_index = { }
        #tris = [ ]
        #for tri in self.iter_triangles():
        #    tri_verts = [ ]
        #    for point in tri:
        #        if point not in vert_index:
        #            vert_index[point] = len(verts)
        #            verts.append(point)
        #        tri_verts.append(vert_index[point])
        #    tris.append(tri_verts)
        #
        #self.nef = create([ shape.transform_point_3(rot,item) for item in verts ], tris).nef
        
    
    def move(self, x,y,z, accuracy=1<<16):
        transform = M('Aff_transformation_3(CGAL::TRANSLATION,Vector_3(a,b,c,d))',
            a=int_round(x*accuracy), b=int_round(y*accuracy), c=int_round(z*accuracy), d=accuracy
        )
        M.do('a.transform(b)',a=self.nef, b=transform)

    def position_nicely(self):
        e = self.extent()
        self.move(-0.5*(e.xmin+e.xmax),-0.5*(e.ymin+e.ymax),-e.zmin)

    def mask(self, res):
        import mask
        
        lines = [ ]
        
        for points in self.triangles():
            points = [ (x*res,y*res) for x,y,z in points ]
            points = points + [ points[0] ]
            
            area = 0.0
            for i in range(len(points)-1):
                area += (
                    (points[i+1][0]-points[i][0])*
                    (points[i+1][1]+points[i][1])*0.5
                )
            if area > 0.0: 
                points = points[::-1]
            for i in range(len(points)-1):
                lines.append( points[i]+points[i+1] )
            
        return mask.make_mask(lines)
    
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
        
        
        #result = empty_shape_2()
        #for triangle in self.triangles():
        #    result.add( create_polygon_2([ (x,y) for x,y,z in triangle ]) )
        #return result
        
    
    #def show(self):
    #    app = M.new('QApplication(argc, argv)',argc=0,argv=0)
    #    widget = M('new CGAL::Qt_widget_Nef_3<Nef_polyhedron_3>(a)',a=self.nef)
    #    M.do('a.setMainWidget(b)',a=app,b=widget)
    #    M.do('a.show()',a=widget)
    #    return M('a.exec()',a=app)

def empty_shape():
    return Shape(M.new('Nef_polyhedron'))

def create(verts, tris, name=None, accuracy=1<<16):
    polyhedron = M.new('Polyhedron()')
    
    builder = M.new('Build_polyhedron()')
    
    for tri in tris:
        assert len(tri) == 3
    
    #seen = set()
    vert_hash = { }
    vert_remap = [ ]
    n_vert_merges = 0
    for vert in verts:
        [x,y,z] = [ int_round(item*accuracy) for item in vert ]
        #assert (x,y,z) not in seen
        #seen.add((x,y,z))
        if (x,y,z) not in vert_hash:
            point = M.new('Point_3(a,b,c,d)',a=x,b=y,c=z,d=accuracy)
            M.do('a.points.push_back(b)',a=builder,b=point)
            vert_hash[(x,y,z)] = len(vert_hash)
        else:
            n_vert_merges += 1
        vert_remap.append(vert_hash[(x,y,z)])
    
    n_tri_losses = 0
    for tri in tris:
        #assert tri[0] != tri[1] and tri[0] != tri[2] and tri[1] != tri[2]
        tri = [ vert_remap[i] for i in tri ]
        if tri[0] == tri[1] or tri[0] == tri[2] or tri[1] == tri[2]:
            n_tri_losses += 1
            continue
        
        vec = M.new('std::vector<int>()')
        for item in tri: 
            M.do('a.push_back(b)',a=vec,b=item)
        M.do('a.facets.push_back(b)',a=builder,b=vec)
    
    if n_vert_merges or n_tri_losses:
        print 'Verts merged: %d of %d, triangles discarded: %d of %d' % (n_vert_merges, len(verts), n_tri_losses, len(tris))
    
    M.do('a.delegate(b)',a=polyhedron,b=builder)
    
    assert M('a.is_closed()',a=polyhedron), 'Polyhedron is not closed'        

    nef = M.new('Nef_polyhedron(a)',a=polyhedron)    
    
    assert M('a.is_valid()',a=nef)
    assert M('a.is_simple()',a=nef)    
    
    return Shape(nef)

def create_polygon_3(verts, accuracy=1<<16):
    vec = M.new('std::vector<Point_3>')

    for vert in verts:
        [x,y,z] = [ int_round(item*accuracy) for item in vert ]
        M.do('a.push_back(Point_3(b,c,d,e))',a=vec,b=x,c=y,d=z,e=accuracy)
    
    return Shape(M.new('Nef_polyhedron(a.begin(),a.end())',a=vec))

#Needs more complicated representation
#def create_halfspace():
#    return Shape(M.new('Nef_polyhedron(Nef_polyhedron::Plane_3(0,0,1,0))'))

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

def load_stl(filename):
    verts = [ ]
    vert_index = { }
    tris = [ ]
    for triangle in read_stl(filename):
        tri = [ ]
        for point in triangle:
            if point not in vert_index:
                vert_index[point] = len(verts)
                verts.append(point)
            tri.append(vert_index[point])
        assert len(set(tri)) == 3, tri
        tris.append(tri)
    
    return create(verts, tris)



def show_only(*shapes):
    pass




class Shape_2(object):
    def __init__(self, pset):
        self.pset = pset

    def copy(self):
        return Shape_2(M.new('Polygon_set_2(a)',a=self.pset))
    
    def _iter_polygons_with_holes(self):
        phole_vec = M.new('std::vector<Polygon_with_holes_2>')
        M.do('a.polygons_with_holes(std::back_inserter(b))', a=self.pset,b=phole_vec)        
        for phole in M.iterate('a.begin()','a.end()',a=phole_vec):
            yield phole
            
    def loops(self, holes=True):
        def point_decode(point):
            return (
                M('CGAL::to_double(a.x())',a=point),
                M('CGAL::to_double(a.y())',a=point)
            )
        def polygon_decode(poly):
            return shape.Loop([ point_decode(item) for item in M.iterate('a.vertices_begin()','a.vertices_end()',a=poly) ])
    
        loops = [ ]
    
        for phole in self._iter_polygons_with_holes():
            assert not M('a.is_unbounded()',a=phole)
            loops.append( polygon_decode( M('a.outer_boundary()',a=phole) ) )
            if holes:
                loops.extend( polygon_decode(item) for item in  M.iterate('a.holes_begin()','a.holes_end()',a=phole) )
        return loops

    def loop(self, holes=True):
        [ result ] = self.loops(holes)
        return result

    def extent(self):
        xs = [ ]
        ys = [ ]
        for loop in self.loops():
            for point in loop:
                xs.append(point[0])
                ys.append(point[1])
        return shape.Limits_2(
            min(xs), max(xs),
            min(ys), max(ys),
        )
    
    def to_3(self):
        #TESTME!
   
        def polygon_recode(poly):
            vec = M.new('std::vector<Point_3>')
            for point_3 in M.iterate('a.vertices_begin()','a.vertices_end()',a=poly):
                M.do('a.push_back(Point_3(b.x(),b.y(),0))',a=vec,b=point_3)
            return Shape(M.new('Nef_polyhedron(a.begin(),a.end())',a=vec))
        
        #result = empty_shape()
        result = None
        for phole in self._iter_polygons_with_holes():
            phole_3 = polygon_recode( M('a.outer_boundary()',a=phole) )
            for hole in M.iterate('a.holes_begin()','a.holes_end()',a=phole):
                phole_3.remove( polygon_recode(hole) )
            if result is None:
                result = phole_3
            else:
                result.add(phole_3)
        
        assert result is not None #CGAL gets explodey with empty shapes
            
        return result
        
    def remove(self, other):
        M.do('a.difference(b)',a=self.pset,b=other.pset)

    def add(self, other):
        M.do('a.join(b)',a=self.pset,b=other.pset)

    def clip(self, other):
        M.do('a.intersection(b)',a=self.pset,b=other.pset)

    def invert(self):
        M.do('a.complement()',a=self.pset)
    
    def orientation(self):
        return M('(int)a.orientation()',a=self.pset)
    
    def is_empty(self):
        return M('a.is_empty()',a=self.pset)


    def _reduce_things(self, things):
        if not things:
            return empty_shape_2()
        while len(things) > 1:
            item = things.pop(-1)
            things[len(things)//2].add(item)
        return things[0]

    def move(self, x,y, accuracy=1<<16):
        #transform = M('Aff_transformation_2(CGAL::TRANSLATION,Vector_2(a,b,c))',
        #    a=int_round(x*accuracy), b=int_round(y*accuracy), c=accuracy
        #)
        offset = M('Vector_2(a,b,c)',
            a=int_round(x*accuracy), b=int_round(y*accuracy), c=accuracy
        )
        def transform(polygon):
            vec = M.new('std::vector<Point_2>')
            for point in M.iterate('a.vertices_begin()','a.vertices_end()',a=polygon):
                M.do('a.push_back(b+c)',a=vec,b=point,c=offset)
            return M.new('Polygon_2(a.begin(),a.end())',a=vec)
        
        #M.do('a.transform(b)',a=self.pset, b=transform)
        things = [ ]
        for phole in self._iter_polygons_with_holes():
            outside = transform( M('a.outer_boundary()',a=phole) )
            insides = M.new('std::vector<Polygon_2>')
            for inside in M.iterate('a.holes_begin()','a.holes_end()',a=phole):
                inside = transform(inside)
                M.do('a.push_back(b)',a=insides,b=inside)
            thing = M.new('Polygon_set_2(Polygon_with_holes_2(a,b.begin(),b.end()))',a=outside,b=insides)
            things.append(thing)       
            
        self.pset = self._reduce_things(things)

    def intersects(self, other):
        temp = self.copy()
        temp.clip(other)
        return not temp.is_empty()
    
        #return M('CGAL::do_intersect(a,b)',a=self.pset,b=other.pset)
        #bholes = list(other._iter_polygons_with_holes())
        #for ahole in self._iter_polygons_with_holes():
        #    for bhole in bholes:
        #        if M('CGAL::do_intersect(a,b)',a=ahole,b=bhole):
        #            return True
        #return False

    def minkowski_sum(self, other):
        things = [ ]
        my_polys = map(_connect_holes,self._iter_polygons_with_holes())
        other_polys = map(_connect_holes,other._iter_polygons_with_holes())
        for a in my_polys:
            for b in other_polys:
                things.append(Shape_2(
                    M.new(
                        'Polygon_set_2(CGAL::minkowski_sum_2(a,b,Decomposition_strategy()))',
                        a=a,b=b)
                    ))
        return self._reduce_things(things)

    def erosion(self, other):
        ext1 = self.extent()
        ext2 = other.extent()
        #Generous margin
        r = max(abs(item) for item in list(ext1)+list(ext2))
        inner_loop = shape.square(r*3)
        outer_loop = shape.square(r*5)
        
        negative = outer_loop.shape_2()
        negative.remove(self)
        dilation = negative.minkowski_sum(other)
        result = inner_loop.shape_2()
        result.remove(dilation)
        return result
    
    def offset_curve(self, amount, quality=None):
        """ +ve dilation
            -ve erosion """
        if amount == 0.0:
            return self.copy()
        elif amount > 0.0:
            return self.minkowski_sum(shape.circle(amount*2.0, quality).shape_2())
        else:
            return self.erosion(shape.circle(amount*-2.0, quality).shape_2())    
        

def _connect_holes(poly_with_holes):
    """ Converts a polygon_with_holes to a polygon """
    vec = M.new('std::vector<Point_2>')
    M.do('CGAL::connect_holes(a,std::back_inserter(b))',a=poly_with_holes,b=vec)
    poly = M.new('Polygon_2(a.begin(),a.end())',a=vec)
    return poly


def empty_shape_2():
    return Shape_2(M.new('Polygon_set_2'))


def create_polygon_2(verts, accuracy=1<<16):
    vec = M.new('std::vector<Point_2>')

    for vert in verts:
        [x,y] = [ int_round(item*accuracy) for item in vert ]
        M.do('a.push_back(Point_2(b,c,d))',a=vec,b=x,c=y,d=accuracy)
    
    poly = M.new('Polygon_2(a.begin(),a.end())',a=vec)
    
    orientation = M('(int)a.orientation()',a=poly)
    
    if orientation == 0:
        return empty_shape_2()
        
    if orientation < 0:
        M('a.reverse_orientation()',a=poly)
    
    return Shape_2(M.new('Polygon_set_2(a)',a=poly))
    



def main(func, *args, **kwargs):
    #return M.run(func,sys.argv[1:],*args,**kwargs)
    return func(sys.argv[1:],*args,**kwargs)


if __name__ == '__main__':
    def run():
        #print module.as_reference('new int(42)').__dict__
        #print 'hello'
        #return
    
        polyhedron = M.new('Polyhedron()')
    
        #builder = module('Build_polyhedron()')
        #
        #for p in [(1,0,0),(0,1,0),(0,0,1)]:
        #    point = module.call('Kernel::Point_3',*p)
        #    module('a.points.push_back(b)',a=builder,b=point)
        #
        #for f in [(0,1,2)]:
        #    vec = module('std::vector<int>()')
        #    for item in f: 
        #        module('a.push_back(b)',a=vec,b=item)
        #    module('a.facets.push_back(b)',a=builder,b=vec)
        #
        #module('a.delegate(b)',a=polyhedron,b=builder)
    
        M('a.make_tetrahedron(Point_3(0,0,0),Point_3(1,0,0),Point_3(0,1,0),Point_3(0,0,1))',a=polyhedron)
    
        print M('a.size_of_vertices()',a=polyhedron)
        print M('a.size_of_halfedges()',a=polyhedron)
        print M('a.size_of_facets()',a=polyhedron)
        
        print 'Closed:', M('(int)a.is_closed()',a=polyhedron)
        
        nef = M.new('Nef_polyhedron(a)',a=polyhedron)
        
        print 'Simple:', M('(int)a.is_simple()',a=nef)
        
        polyhedron2 = M.new('Polyhedron()')
        M('a.convert_to_polyhedron(b)',a=nef,b=polyhedron2)
    
        print 'Closed:', M('(int)a.is_closed()',a=polyhedron2)
        
        #i = module('a.facets_begin()',a=polyhedron2)
        #end = module('a.facets_end()',a=polyhedron2)
        #while module('a<b',a=i,b=end):
        #    value = module('*a',a=i)
        #    print 'boop'
        #    module('a++',a=i)
            
        for item in M.iterate('a.facets_begin()','a.facets_end()',a=polyhedron2):
            print 'boop'
            for item2 in M.circulate('a.facet_begin()',a=item):
                print M('a.vertex()->point()',a=item2)
    
        print 'lovely'
    
    #M.run(run)
    run()
    

