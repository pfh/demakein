"""

8mm thickness, 6mm holes

C6

D6 
got: 1120Hz -> 309mm
want: 294.6
error: 14.4mm

E6 
got: 1231Hz -> 281.2mm
want: 262.5mm
error: 18.7mm

G6 
got: 1462 -> 236.7mm
want: 220.7mm
error: 16.0mm

C7 
got: 1942Hz ~ 178.2mm
want: 165.4mm
error: 12.8mm

average: 15.5 wavelength = 3.87 lengths = 0.645 diameters

"""



import sys, os, math
sys.path.insert(0, os.path.split(__file__)[0])

import design, make, shape, profile

from nesoni import config

RES = 20

LENGTH_CORRECTION = -0.7
   #-0.645 # * diameter
   # Hole is rounded at end, so make it a little longer
   # - unknown further correction 

SCALE = [
    'C6',
    'D6',
    'E6',
    'F6',
    'G6',
    'A6',
    'B6',
    'C7',
    'D7',
]

#SCALE = [
#    'F6',
#    'G6',
#    'A6',
#    'C7',
#    'D7',
#    'F7',
#]

def make_hole(diameter, length):
    pos = [ 0.0 ]
    diam = [ diameter ]
    
    radius = diameter*0.5
    n = 4
    for i in range(0,n):
        x = math.pi/2 * float(i)/n
        pos.append(length+radius*(math.sin(x)-1))
        diam.append(diameter*math.cos(x))
    
    prof = profile.Profile(pos,diam,diam)
    hole = shape.extrude_profile(prof)
    
    return hole

@config.help("""\
Make a Viking-style panpipe.
""")
@config.Float_flag('thickness', 'Instrument thickness.\n(Wood thickness should be half this if milling.)')
@config.Float_flag('wall', 'Minimum wall thickness')
@config.Int_flag('transpose', 'Transpose (semitones)')
class Make_panpipe(make.Make):
    thickness = 8.0
    wall = 1.0
    transpose = 0
    
    def run(self):
        zsize = self.thickness
        
        pad = self.wall
        diameter = zsize - pad*2
        
        self.log.log('Thickness: %.1fmm\n' % zsize)
        self.log.log('Min wall thickness: %.1fmm\n' % pad)
        self.log.log('Hole diameter: %.1fmm\n' % diameter)
        
        negatives = [ ]
        lengths = [ ]
        xs = [ ]
        for i, note in enumerate(SCALE):
            print 'Make hole %d / %d' % (i+1,len(SCALE))
            length = design.wavelength(note,self.transpose)*0.25 + LENGTH_CORRECTION*diameter
            x = i*(diameter+pad)
            lengths.append(length)
            xs.append(x)
            hole = make_hole(diameter, length)
            hole.move(x,0,0)
            negatives.append(hole)
        
        string_hole_diameter = diameter*1.5
        string_hole_loop = shape.circle(string_hole_diameter)
        string_hole = shape.extrusion([-zsize,zsize],[string_hole_loop,string_hole_loop])
        string_hole.rotate(1,0,0, 90)
        
        xlow = xs[0]-zsize
        #xmid = xs[-1]*0.5
        xhigh = xs[-1]+zsize
        
        zhigh = lengths[0]+zsize*0.5
        #zmid  = max(lengths[-1]+zsize*0.5, zhigh-(xhigh-xmid))
        
        trim = min(xhigh-xlow,zhigh) * 0.5
        
        #string_x = (xmid+xhigh)*0.5 - diameter
        #string_z = (zmid+zhigh)*0.5 - diameter
        #string_z = lengths[3] + diameter*2
        #string_x = xhigh-trim*0.5-diameter
        #string_z = zhigh-trim*0.5-diameter
        
        a = math.pi*-5/8
        d = diameter * 1.5
        string_x = xhigh-trim + math.cos(a)*d
        string_z = zhigh      + math.sin(a)*d
        
        string_hole.move(string_x,0,string_z)
        
        #p = pad*0.5
        #loop = shape.Loop([(0,p),(p*2,-p),(-p*2,p)])
        #r = diameter-pad
        #stick = shape.extrusion([-r,r],[loop,loop])
        #
        #for i in xrange(-1,len(SCALE)+2):
        #    for j in xrange(int(zhigh / (diameter+pad))+1):
        #        x = (i-0.5)*(diameter+pad)
        #        z = r + j*(diameter+pad)
        #        c = stick.copy()
        #        if (i^j)&1:
        #            c.rotate(0,1,0,90)
        #        c.move(x,-diameter*0.5-pad,z)
        #        negatives.append(c)
        
        loop = shape.Loop([
            (xlow,0),
            (xhigh,0),
            (xhigh,zhigh-trim),
            (xhigh-trim,zhigh),
            (xlow,zhigh)
        ])

        bev = zsize / 4.0
        loop_bevel = shape.Loop([
            (xlow,bev),
            (xhigh,bev),
            (xhigh,zhigh-trim),
            (xhigh-trim,zhigh),
            (xlow,zhigh)
        ])
        
        #mask = loop.mask(RES)
        
        #amount = diameter * 0.5
        #op = shape.circle(amount).mask(RES)
        #mask = mask.open(op)
        
        #loop = mask.trace(RES)[0]
        
        #sloop = mask.erode(op).trace(RES)[0]
        
        #z1 = zsize*0.5-amount
        z2 = zsize*0.5
        
        #positive = shape.extrusion([-z2,z2],[loop,loop])
        positive = shape.extrusion([-z2,-z2+bev,z2-bev,z2],[loop_bevel,loop,loop,loop_bevel])
        positive.rotate(1,0,0,90)
        
        negative = string_hole.copy()
        for i, item in enumerate(negatives):
            print 'Merge %d / %d' % (i+1,len(negatives))
            negative.add(item)
        
        del negatives
        
        instrument = positive.copy()
        
        print 'Remove holes from instrument'
        instrument.remove(negative)
        
        del positive
        del negative
        
        instrument.rotate(1,0,0,90)
        extent = instrument.extent()

        copy = instrument.copy()
        copy.rotate(0,0,1,-45)
        cextent = copy.extent()
        copy.move(-(cextent.xmin+cextent.xmax)*0.5,
                  -(cextent.ymin+cextent.ymax)*0.5,
                  -cextent.zmin)
        self.save(copy,'instrument')
        del copy
        
        top = shape.block(
            extent.xmin-1,extent.xmax+1,
            extent.ymin-1,extent.ymax+1,
            0,extent.zmax+1
        )
        bottom = shape.block(
            extent.xmin-1,extent.xmax+1,
            extent.ymin-1,extent.ymax+1,
            extent.zmin-1,0
        )
        
        top.clip(instrument)
        bottom.clip(instrument)
        top.rotate(1,0,0,180)
        top.move(0,4,0)
        bottom.add(top)
        pattern = bottom
        
        del top
        del bottom
        
        pattern.move(0,0,z2)
        pattern.rotate(0,0,1, -90)

        bit_pad = 4.0
        extra_depth = 3.0
        a = bit_pad
        b = bit_pad + z2/10.0
        pad_cone = shape.extrude_profile(profile.Profile(
                [-extra_depth,0,z2],[a*2,a*2,b*2]
            ), 
            cross_section=lambda d: shape.circle(d,16))
        
        extra = b + 0.5
        
        extent = pattern.extent()
        mill = shape.block(
            extent.xmin-extra, extent.xmax+extra,
            extent.ymin-extra, extent.ymax+extra,
            -extra_depth, z2,
        )
        
        mill.remove( pattern.polygon_mask().to_3().minkowski_sum(pad_cone) )
        mill.add( pattern )
        
        del pad_cone
        del pattern
        
        self.save(mill, 'mill')
        
        
#        dilations = [
##            (z, shape.circle(2.0*( 2.0+z/20.0 )).mask(self.res))
##            for z in range(1)
#            (z, mask.ones(0,0,1,1) if not z else 
#                shape.circle(2.0*( z/10.0 )).mask(self.res))
#            for z in range(0,int(self.zsize),5)
#        ]

        #dilator = shape.circle(2* bit_diameter).mask(res)
        #hole_mask = mask.zero()
        #for x,y,packable in self.items:
        #    if packable.use_upper:
        #        hole_mask = hole_mask | packable.dilated_mask.offset(int(x*self.res+0.5),int(y*self.res+0.5))
        #hole_mask = hole_mask.close(dilator)
                
        #mask = bottom.mask(RES)
        #op = shape.circle(6).mask(RES)
        #loop = mask.dilate(op).trace(RES)
        #
        #z1 = -self.thickness+1.5
        #z2 = 0.0
        #loop_ext = shape.extrusion([z1,z2],[loop,loop])
        #extent = loop_ext.extent()
        #
        #cut = shape.block(
        #    extent.xmin-1,extent.xmax+1,
        #    extent.ymin-1,extent.ymax+1,
        #    z1,z2
        #)
        #cut.remove(loop_ext)
        #cut.add(bottom)
        #self.save(cut,'mill.stl')


if __name__ == '__main__': 
    shape.main_action(Make_panpipe())


