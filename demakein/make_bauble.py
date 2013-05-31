
import math

from nesoni import config

from . import make, shape, profile

def wobble(diameter=1.0, wobble=0.5, spin=0.0, period=16, n=256):
    radius = diameter * 0.5
    result = [ ]
    for i in range(n):
        a = (i+0.5)*math.pi*2.0/n 
        s = spin*math.pi / 180.0
        b = math.cos((a+s)*period)
        c = math.cos((a-s*0.5)*period)*0.75
        d = 1-(1-b)*(1-c)
        r2 = radius*(1.0 + wobble*( d -0.5) )
        result.append( (math.cos(a)*r2, math.sin(a)*r2) )
    return shape.Loop(result)


@config.help(
'Make a gratuitous bauble.',
"""\
This tool is used when you use "make-shawm: --bauble yes".

Make your own gratuitous baubles to fit the cylindrical object of your choice.
"""
)
@config.Float_flag('dock_diameter','Diameter of cylinder to fit.')
@config.Float_flag('dock_length','Length of cylinder to fit.')
class Make_bauble(make.Make):
    dock_diameter = 40.0
    dock_length = 5.0
    
    def run(self):
        length = self.dock_diameter * 1.5
        inlength = length * 0.9
        pos_outer = [ 0.0, length ]
        diam_outer = [ self.dock_diameter+2.0, 0.0 ]
        angle = [ 20.0, -10.0 ]
        p_outer = profile.curved_profile(
            pos_outer, diam_outer, diam_outer, angle, angle)
        
        pos_inner = [ 0.0, inlength ]
        diam_inner = [ self.dock_diameter, 0.0 ]
        p_inner = profile.curved_profile(
            pos_inner, diam_inner, diam_inner, angle, angle)
        
        spin = profile.make_profile([(0.0,0.0),(length, 120.0)])
        
        wob = profile.make_profile([(self.dock_length*0.5,0.0),(self.dock_length,1.0),(length,0.0)])
        
        bauble = shape.extrude_profile(p_outer,spin,wob, cross_section=lambda d,s,w: wobble(d,w*0.1,s,12))        
        inside = shape.extrude_profile(
            p_inner.clipped(self.dock_length+1.0,inlength),spin.clipped(self.dock_length+1.0,inlength),wob.clipped(self.dock_length+1.0,inlength), 
            cross_section=lambda d,s,w: wobble(d,w*-0.1,s,12))
        bauble.remove(inside)
        
        dock_profile = profile.make_profile([(0.0,self.dock_diameter),(self.dock_length,self.dock_diameter),(self.dock_length+self.dock_diameter*0.5,0.0)])
        dock = shape.extrude_profile(dock_profile)
        #bauble.add(shape.extrude_profile(p_outer.clipped(0.0,self.dock_length+1.0)))
        bauble.remove(dock)
        
        self.save(bauble, 'bauble')
        return bauble
