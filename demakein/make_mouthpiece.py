
import math

from nesoni import config

from . import shape, profile, make

"""

A typical trumpet mouthpiece (Kelly 5C):

cup
16mm   inner diameter
26.5mm outer diameter
depth of about 9mm

3.75mm entrance to bore
flares over ~75mm to 8mm



Cup diam 11 depth 4 bore 5 almost works with 4mm tenor shawm.

"""


def make_widget(
    tube_length,
    tube_diameter,
    cup_length,
    final_diameter,
    french=False,
):
    a = 0.0
    b = a + tube_length
    c = b + cup_length
    
    initial_outer_diameter = final_diameter
    final_outer_diameter = final_diameter + 14.0
    
    outer_profile = profile.make_profile([
         (a, initial_outer_diameter),
         (c, final_outer_diameter),
    ])
    
    inner_spec = [
         (a, tube_diameter),
    ]
    n = 1 if french else 20
    for i in range(n):
        angle = i*math.pi/2/n
        inner_spec.append((
             b+cup_length*(1-math.cos(angle)),
             tube_diameter+(final_diameter-tube_diameter)*math.sin(angle)
        ))
    inner_spec.append((c,final_diameter))
    inner_profile = profile.make_profile(inner_spec).clipped(-10.0, c+10.0)
    
    bevel = profile.make_profile([
         (c-1.0, 0.0),
         (c, 2.0)
         ])
    outer_profile = outer_profile - bevel
    inner_profile = inner_profile + bevel
    
    outer = shape.extrude_profile(outer_profile)
    inner = shape.extrude_profile(inner_profile)
    widget = outer.copy()
    widget.remove(inner)
    
    return outer, inner, widget


def make_horn(straight_length, length, d1, d2, power):
    k = (d1/d2)**(1.0/power)
    a = k*length/(1.0-k)
    print a, k
    b = d1/(abs(a)**power)
    f = lambda x: b*(abs(x+a)**power)
    
    print f(0.0), f(length)
    
    outer_profile = profile.make_profile([
         (0.0, d2+1.5),
         (straight_length+length-0.5, d2+1.5),
         (straight_length+length, d2+0.5),
    ])
    
    steps = 16
    inner_profile = profile.make_profile(
         [ (0.0, d1) ] + [
         (straight_length+i*length/steps, f(i*length/steps))
         for i in xrange(steps)
         ] + [ (straight_length+length, d2) ])
    
    outer = shape.extrude_profile(outer_profile)
    inner = shape.extrude_profile(inner_profile)
    widget = outer.copy()
    widget.remove(inner)
    
    return outer, inner, widget


@config.help("""\
[Experimental] Make a cornett mouthpiece for a shawm.
""","""\
Glue on or attach using a short length of drinking straw.
""")
@config.Float_flag('bore','Bore diameter mouthpiece connects to.')
class Make_mouthpiece(make.Make, make.Miller):
    bore = 5.0

    def run(self):
        #outer, inner, widget = make_widget(
        #     tube_length = 8.0,
        #     tube_diameter = self.bore,
        #     cup_length = 4.0, #5.0 #6.0,
        #     final_diameter = 9.0, #12.0 #15.0,
        #     )
        outer,inner,widget = make_horn(
            4.0, 8.0,
            self.bore,
            20.0,
            -1.0
            )
        self.save(widget, 'mouthpiece')
        
        #Ripped a strand of wood removing
        #mill = self.miller(widget, [0.0],[0.0])
        
        mill = self.miller(widget, [-5.0,5.0],[])
        self.save(mill, 'mill-mouthpiece')

