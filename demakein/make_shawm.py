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
@config.Bool_flag('dock', 'Reed docking thing at top. (Not needed for drinking straw reed.)')
@config.Float_flag('dock_top', 'Diameter at top of dock.')
@config.Float_flag('dock_bottom', 'Diameter at bottom of dock, should hold reed snugly.')
@config.Float_flag('dock_length', 'Length of dock.')
@config.Bool_flag('decorate', 'Add some decorative rings.')
@config.Bool_flag('bauble', 'Add a gratuitous bauble to the end.')
class Make_reed_instrument(make.Make_millable_instrument):
    dock = False
    
    #7,5 was too small
    #9,6 was just a tad loose
    dock_top = 8.5
    dock_bottom = 5.5
    dock_length = 15

    decorate = False
    bauble = False
    
    def run(self):
        spec = self.working.spec
        
        length = spec.length
        
        #length = spec.inner.pos[-2]
        #if self.working.designer.do_trim:
        #    length *= 0.855 #Reed accounts for part of length, etc
        #    # 0.865 was still rather short (Feb 2014)
        #    # 0.875 needed a rather short reed (shapeways tenor, November 2012)
        
        #length = spec.inner.pos[-2]
        #assert spec.inner(length) == self.working.designer.bore
        #self.log.log('Generated shape is %.0f%% of length of simulated instrument, rest is reed.\n' % (length*100.0 / spec.length))        
        #self.log.log('(Effective) reed length: %.1fmm\n' % (spec.length-length))
        
        outer_profile = spec.outer #.clipped(0,length)
        inner_profile = spec.inner #.clipped(0,length)
        
        if self.dock:
           dock_inner = profile.make_profile([
               [0.0, self.dock_bottom],
               [self.dock_length, self.dock_top],
               ])
           
           dock_outer = profile.make_profile([
               [length - 5.0, outer_profile(length)],
               [length, self.dock_top + 5.0],
               [length + self.dock_length, self.dock_top + 5.0],
               ])
           
           inner_profile = inner_profile.appended_with(dock_inner)
           outer_profile = outer_profile.max_with(dock_outer)
        
        
        m = outer_profile.maximum()
        
        if self.bauble:
            end_dock_length = 5.0
            print 'Bauble dock: %.1fmm diameter, %.1fmm length' % (m, end_dock_length)
            bauble = make_bauble.Make_bauble(self.working_dir,dock_length=end_dock_length,dock_diameter=m).run()
            fixer = profile.make_profile([(0.0,m),(end_dock_length,m),(end_dock_length*2,0.0)])
            outer_profile = outer_profile.max_with(fixer)
        
        if not self.dock:
            dock_diam = self.working.designer.bore * 4.0
            dock_length = 20.0
            fixer = profile.make_profile([(length-dock_length*1.25,0.0),(length-dock_length,dock_diam)])
            outer_profile = outer_profile.max_with(fixer)
        
        if self.decorate:
            if not self.bauble:
                outer_profile = make.decorate(outer_profile, 0.0, 1.0, 0.05)
            outer_profile = make.decorate(outer_profile, length-dock_length*1.25, -1.0, 0.15)
        
        n_holes = self.working.designer.n_holes
        

        
        self.make_instrument(
            inner_profile=inner_profile.clipped(-50,inner_profile.end()+50),
            outer_profile=outer_profile,
            hole_positions=spec.hole_positions,
            hole_diameters=spec.hole_diameters,
            hole_vert_angles=spec.hole_angles,
            hole_horiz_angles=self.working.designer.hole_horiz_angles,
            xpad = [ 0.0 ] * n_holes,
            ypad = [ 0.0 ] * n_holes,
            with_fingerpad = self.working.designer.with_fingerpad,
        )
        
        if self.bauble:
            bauble.rotate(1,0,0, 180)
            bauble.move(0,0,end_dock_length)
            binst = self.working.instrument.copy()
            binst.add(bauble)
            self.save(binst, 'baubled-instrument')

        self.make_parts(up = True)
        

        #if not self.mill:
        #    self.segment([ cut1, cut3, cut5 ], up=True)
        #    self.segment([ cut2, cut4 ], up=True)
        #    self.segment([ cut3 ], up=True)
        #else:
        #    pack.cut_and_pack(
        #        self.working.outside, self.working.bore,
        #        upper_segments, lower_segments,
        #        xsize=self.mill_length, 
        #        ysize=self.mill_width, 
        #        zsize=self.mill_thickness,
        #        bit_diameter=self.mill_diameter,
        #        save=self.save,
        #    )
        
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


@config.help('Make a dock extender, to adjust tuning.')
@config.Float_flag('bore', 'Bore diameter.')
@config.Float_flag('dock_top', 'Diameter at top of dock.')
@config.Float_flag('dock_bottom', 'Diameter at bottom of dock, should hold reed snugly.')
@config.Float_flag('dock_length', 'Length of dock.')
@config.Float_flag('extension', 'Extension amount.')
@config.Float_flag('gap', 'Amount of gap all around, to allow extender to fit into dock.')
class Make_dock_extender(make.Make):
    bore = 4.0
    dock_top = 8.5
    dock_bottom = 5.5
    dock_length = 15.0
    extension = 10.0
    gap = 0.2

    def run(self):    
        dock_inner = profile.make_profile([
            [-5.0, self.dock_top],
            [self.dock_length, self.dock_bottom, self.bore],
            [self.dock_length + self.extension + 5.0, self.bore],
            ])
        
        dock_outer = profile.make_profile([
            [0.0, self.dock_top+5.0],
            [self.extension, self.dock_top+5.0, self.dock_top - self.gap*2.0],
            [self.extension+self.dock_length, self.dock_bottom - self.gap*2.0],
            ])

        inner = shape.extrude_profile(dock_inner)
        thing = shape.extrude_profile(dock_outer)
        thing.remove(inner)
        self.save(thing, "extender-%.1fmm" % self.extension)
    

if __name__ == '__main__': 
    shape.main_action(Make_shawm())
