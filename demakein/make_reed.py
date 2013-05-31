
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
        
        