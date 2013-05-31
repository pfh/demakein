"""

F-shawm
theory  495.5

design  438.4
actual  399
ratio   

"""


import sys, os, math
sys.path.insert(0, os.path.split(__file__)[0])

from . import design, make, profile, shape, pack, make_bauble

from nesoni import config

@config.help("""\
Produce 3D models using the output of "demakein make-shawm:".
""")
@config.Bool_flag('decorate', 'Add some decorative rings.')
@config.Bool_flag('bauble', 'Add a gratuitous bauble to the end.')
class Make_shawm(make.Make_millable_instrument):
    decorate = True
    bauble = False
    
    def run(self):
        spec = self.working.spec
        
        length = spec.length * 0.865 #Reed accounts for part of length, etc
        # 0.875 needed a rather short reed (shapeways tenor, November 2012)
        
        #length = spec.inner.pos[-2]
        #assert spec.inner(length) == self.working.designer.bore
        #self.log.log('Generated shape is %.0f%% of length of simulated instrument, rest is reed.\n' % (length*100.0 / spec.length))        
        #self.log.log('(Effective) reed length: %.1fmm\n' % (spec.length-length))
        
        outer_profile = spec.outer.clipped(0,length)
        
        m = outer_profile.maximum()
        
        if self.bauble:
            end_dock_length = 5.0
            print 'Bauble dock: %.1fmm diameter, %.1fmm length' % (m, end_dock_length)
            bauble = make_bauble.Make_bauble(self.working_dir,dock_length=end_dock_length,dock_diameter=m).run()
        else:
            end_dock_length = m * 0.05
        fixer = profile.make_profile([(end_dock_length,m),(end_dock_length,m),(end_dock_length+m*0.333,0.0)])
        outer_profile = outer_profile.max_with(fixer)
        
        dock_diam = self.working.designer.bore * 4.0
        dock_length = 10.0
        fixer = profile.make_profile([(length-dock_length*1.25,0.0),(length-dock_length,dock_diam)])
        outer_profile = outer_profile.max_with(fixer)
        
        if self.decorate:
            if not self.bauble:
                outer_profile = make.decorate(outer_profile, 0.0, 1.0, 0.05)
            outer_profile = make.decorate(outer_profile, length-dock_length*1.25, -1.0, 0.15)
        
        n_holes = self.working.designer.n_holes
        if n_holes == 6:
            hole_horiz_angles = [ 0.0 ] * 6
            cut2 = spec.inner_hole_positions[0]*0.5+spec.inner_hole_positions[1]*0.5
            cut3 = spec.inner_hole_positions[2]*0.5+spec.inner_hole_positions[3]*0.5
            cut4 = spec.inner_hole_positions[5]*1.3-spec.inner_hole_positions[4]*0.3

            cut1a = spec.hole_positions[0]
            cut1a -= outer_profile(cut1a)*0.5
            cut1b = (cut2+outer_profile(cut2)*0.25) * 0.5
            cut1 = min(cut1a,cut1b)

        else:
            hole_horiz_angles = [ -20.0 ] + [ 0.0 ] * 6 + [ 180.0 ]
            cut1 = spec.hole_positions[0]*0.5+spec.hole_positions[1] * 0.5        

            cut2 = spec.inner_hole_positions[2]*0.5+spec.inner_hole_positions[3] * 0.5
            cut3 = spec.inner_hole_positions[3]*0.5+spec.inner_hole_positions[4] * 0.5
            cut4 = spec.inner_hole_positions[4]*0.5+spec.inner_hole_positions[5] * 0.5
        
        cut5a = spec.hole_positions[-1]
        cut5a += outer_profile(cut5a)*0.5        
        cut5b = length*0.5+cut3*0.5
        cut5b -= outer_profile(cut5b)*0.25
        cut5 = max(cut5a, cut5b)

        if self.mill:
            cut0 = cut1*0.5
            cut6 = length*0.5+cut5*0.5
            upper_segments, lower_segments = pack.plan_segments([cut0/length,cut1/length,cut2/length,cut3/length,cut4/length,cut5/length,cut6/length], self.mill_length / length)
        
        self.make_instrument(
            inner_profile=spec.inner.clipped(-50,length+50),
            outer_profile=outer_profile,
            hole_positions=spec.hole_positions,
            hole_diameters=spec.hole_diameters,
            hole_vert_angles=spec.hole_angles,
            hole_horiz_angles=hole_horiz_angles,
            xpad = [ 0.0 ] * n_holes,
            ypad = [ 0.0 ] * n_holes,
            with_fingerpad = [ True ] * n_holes,
        )
        
        if self.bauble:
            bauble.rotate(1,0,0, 180)
            bauble.move(0,0,end_dock_length)
            binst = self.working.instrument.copy()
            binst.add(bauble)
            self.save(binst, 'baubled-instrument')

        if not self.mill:
            self.segment([ cut1, cut3, cut5 ], length, up=True)
            self.segment([ cut2, cut4 ], length, up=True)
            self.segment([ cut3 ], length, up=True)
        else:
            pack.cut_and_pack(
                self.working.outside, self.working.bore,
                upper_segments, lower_segments,
                xsize=self.mill_length, 
                ysize=self.mill_width, 
                zsize=self.mill_thickness,
                bit_diameter=self.mill_diameter,
                save=self.save,
            )
        
        #self.working.instrument.rotate(0,1,0, 180)
        #self.working.instrument.move(0,0,length)
        #need to flip spec
        #self.segment([ length-cut3, length-cut2, length-cut1 ], length)
        
        
        #shape.Make_instrument.run(self)
        #        
        #designer = self.designer
        #spec = self.instrument
        #
        ##length = spec.length * 0.91 # Shorten to allow reed effective length. TODO: Tune this
        #length = spec.length * 0.875 # Based on trimming alto_shawm
        #width = max(spec.outer.low)
        #
        #instrument = shape.extrude_profile(spec.outer.clipped(0,length))
        #outside = shape.extrude_profile(spec.outer.clipped(0,length))
        #bore = shape.extrude_profile(spec.inner.clipped(-50,length+50))
        #
        #xpad = [ 0.0 ] * 8
        #ypad = [ 0.0 ] * 8
        #angle = [ -20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 180.0 ]
        #drill_outside = [ 1 ] + [ 0 ] * 7
        #
        #for i, pos in enumerate(spec.hole_positions):
        #    height = spec.outer(pos)*0.5 + 4.0
        #    hole = shape.prism(
        #        height, spec.hole_diameters[i],
        #        shape.squared_circle(xpad[i], ypad[i]).with_effective_diameter
        #    )
        #    hole.rotate(1,0,0, -90)
        #    hole.rotate(0,0,1, angle[i])
        #    hole.move(0,0,pos)
        #    bore.add(hole)
        #    if drill_outside[i]:
        #        outside.remove(hole)
        #
        #instrument.remove(bore)
        #
        #self.save(instrument,'instrument.stl')
        #
        #shapes = pack.cut_and_pack(
        #    outside, bore,
        #    self.SCHEMES[self.scheme][0], self.SCHEMES[self.scheme][1],
        #    xsize=self.SCHEMES[self.scheme][2], ysize=self.SCHEMES[self.scheme][3], zsize=self.thickness,
        #    bit_diameter=3.0,
        #    res=10,
        #    output_dir=self.output_dir
        #)
        #
        #shape.show_only(instrument, *shapes)        
        #
        
        #if self.forms == 1:
        #    lower, upper = shape.make_formwork(
        #        outside, bore, length,
        #        [ 0.0, 0.65, 1.0 ],
        #        [ 0.0, 0.4, 1.0 ],
        #        3.0, 6.0, thickness[0], 200.0
        #    )
        #    
        #    self.save(lower,'lower.stl')
        #    self.save(upper,'upper.stl')
        #    
        #    shape.show_only(instrument, lower, upper)
        #
        #elif self.forms == 2:
        #    lower1, upper1 = shape.make_formwork(
        #        outside, bore, length,
        #        [ 0.0, 0.3, 0.6, 1.0 ],
        #        [ ],
        #        3.0, 6.0, thickness[0], 200.0
        #    )
        #    lower2, upper2 = shape.make_formwork(
        #        outside, bore, length,
        #        [ ],
        #        [ 0.0, 0.4, 0.7, 1.0 ],
        #        3.0, 6.0, thickness[1], 200.0
        #    )
        #    
        #    self.save(lower1,'lower1.stl')
        #    self.save(upper1,'upper1.stl')
        #    self.save(lower2,'lower2.stl')
        #    self.save(upper2,'upper2.stl')
        #    
        #    shape.show_only(instrument, lower1,upper1,lower2,upper2)
        #
        #else:
        #     assert False, 'Unsupported number of forms'
    

if __name__ == '__main__': 
    shape.main_action(Make_shawm())
