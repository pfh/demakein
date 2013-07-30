
import math

from . import design, make, shape, profile

from nesoni import config

def grow(loop,thickness):
    extent = loop.extent()
    xsize = extent.xmax-extent.xmin
    ysize = extent.ymax-extent.ymin
    return loop.scale2(
        (xsize+thickness*2.0)/xsize,
        (ysize+thickness*2.0)/ysize
        )


@config.help(
    '[Experimental, not yet working] Make a printable reed.'
    )
class Make_reed(make.Make):
    def run(self):
        diameter = 8.0
        flare = 2.0
        length = 30.0
        
        stem_length = 5.0
        stem_diameter = diameter + 6.0 
        
        thickness0 = 1.0
        thickness1 = 0.05
                
        bottom = shape.circle(diameter)
        top = shape.lens(0.99).with_circumpherence(math.pi*diameter*flare)
        
        stem = shape.circle(stem_diameter)

        reed = shape.extrusion(
            [0.0,stem_length,stem_length,stem_length+length],
            [stem,stem,grow(bottom,thickness0),grow(top,thickness1)]
            )
        inside = shape.extrusion(
            [0.0,stem_length,stem_length+length],
            [bottom,bottom,top]
            )
        
        reed.remove(inside)
        
        #wedge_thickness = 0.2
        #wedge_loop = shape.Loop([
        #    (length*0.5, 0.0),
        #    (length*1.01, wedge_thickness*0.5),
        #    (length*1.01, -wedge_thickness*0.5)
        #    ])
        #wedge = shape.extrusion([-diameter*4,diameter*4],[wedge_loop,wedge_loop])
        #wedge.rotate(0,1,0,-90)
        #reed.remove(wedge)
        
        self.save(reed, 'reed')

        
@config.help(
    '[Experimental] Make a reed-shaping doodad.'
    )
class Make_reed_shaper(make.Make):
    def run(self):
        diameter = 7.0 
        length = 15.0
        
        thickness0 = 2.0
        thickness1 = 2.0
        
        outside = shape.empty_shape()
        inside = shape.empty_shape()

        for lens_amount in [ 0.85 ]:                
            #bottom = shape.circle(diameter)
            top = shape.lens(lens_amount).with_circumpherence(math.pi*diameter)
            bottom = top
            
            outside.add(shape.extrusion(
                [0.0,length],
                [grow(bottom,thickness0),grow(top,thickness1)]
                ))
            inside.add(shape.extrusion(
                [0.0,length],
                [bottom,top]
                ))
        
        thing = outside.copy()
        thing.remove(inside)

        wedge_thickness = diameter*0.2
        wedge_loop = shape.Loop([
            (length*0.333, 0.0),
            (length*1.01, wedge_thickness*0.5),
            (length*1.01, -wedge_thickness*0.5)
            ])
        wedge = shape.extrusion([-diameter*4,diameter*4],[wedge_loop,wedge_loop])
        wedge.rotate(0,1,0,-90)
        #wedge.rotate(0,0,1,90)
        thing.remove(wedge)

        self.save(thing, 'shaper')
        