
import math

from . import design, shape, profile, pack

from nesoni import config, legion

def decorate(prof, pos, align, amount=0.2):
    amount = prof(pos)*amount
    pos += amount * align
    deco_profile = profile.Profile(
        [ pos+amount*i for i in [-1,0,1]],
        [ amount*i      for i in [0,1,0] ],
    )    
    return prof + deco_profile.clipped(prof.start(),prof.end())

@config.Float_flag('mill_diameter', 'Diameter of milling bit.')
@config.Bool_flag('mill_ball', 'Is it a ball-mill rather than an end-mill? Extra depth will be added so the bit cuts through into the base.')
class Miller(config.Configurable):
    mill_diameter = 3.0
    mill_ball = True
        
    def miller(self, pattern, xribs=[], yribs=[]):    
        extent = pattern.extent()
        height = extent.zmax - extent.zmin
        
        bit_pad = self.mill_diameter * 1.25
        extra_depth = self.mill_diameter*0.5 if self.mill_ball else 0.0
        a = bit_pad
        b = bit_pad + (height+extra_depth)/10.0
        pad_cone = shape.extrude_profile(profile.Profile(
                [extent.zmin-extra_depth,extent.zmax],[a*2,b*2]
            ), 
            cross_section=lambda d: shape.circle(d,16))
        
        extra = b + 0.5
        
        extent = pattern.extent()
        mill = shape.block(
            extent.xmin-extra,       extent.xmax+extra,
            extent.ymin-extra,       extent.ymax+extra,
            extent.zmin-extra_depth, extent.zmax,
        )
        
        mill.remove( pattern.polygon_mask().to_3().minkowski_sum(pad_cone) )
        mill.add( pattern )
        
        rib_width = 1.0
        rib_height = 2.0
        for x in xribs:
            block = shape.block(
                x-rib_width*0.5, x+rib_width*0.5,
                extent.ymin-extra,extent.ymax+extra,
                extent.zmin-extra_depth,extent.zmin+rib_height
                )
            mill.add(block)
        
        for y in yribs:
            block = shape.block(
                extent.xmin-extra,extent.xmax+extra,
                y-rib_width*0.5, y+rib_width*0.5,
                extent.zmin-extra_depth,extent.zmin+rib_height
                )
            mill.add(block)

        return mill


@config.Bool_flag('draft', 'Draft output')
class Make_base(config.Action):
    draft = False
    
    # We'll need a lot of memory, so run exclusively
    def cores_required(self):
        return legion.coordinator().get_cores()

    def save(self, shape, prefix):
        prefix = self.get_workspace()/prefix
        
        shape.save(prefix + '.stl')
        
        import sketch
        sketch.sketch(shape, prefix + '-sketch.svg')

    def _before_run(self):
        if self.draft:
            shape.draft_mode()
        self.get_workspace()

class Make(config.Action_with_output_dir, Make_base):
    pass


class Working(object): pass

@config.String_flag('prefix', 'Output file prefix (useful if you want to make your design several different ways).')
@config.Bool_flag('fingerpads',
    'Flatten area around finger holes, '
    'possibly producing a better seal.'
    )
@config.String_flag('join',
    'Printing: Join type, options are:\n'
    'weld - ABS pieces to be joined by acetone welding, or similar.\n'
    'straight - Straight socket.\n'
    'taper - Tapered socket.\n'
    )
@config.Float_flag('gap', 
    'Printing: Amount of gap all around in the joins between segments '
    'for straight or tapered joins. '
    'The best value for this will depend on the accuracy of your printer. '
    'If a joint is too loose and leaks, it can be sealed using wax or similar.')
@config.Bool_flag('thick_sockets',
    'Add some extra thickness around sockets.'
    )
@config.Float_flag('dilate',
    'Increase bore diameter by this much. '
    'Use if your 3D printer is poorly calibrated on concave curves.'
    )
class Make_instrument(config.Action_with_working_dir, Make_base):
    gap = 0.2
    fingerpads = False
    join = 'weld'
    thick_sockets = False
    dilate = 0.0
    prefix = ''

    def _before_run(self):
        self.working = Working()
        self.working.designer = design.load(self.working_dir)
        self.working.spec = self.working.designer.instrument

    def _after_run(self):
        del self.working
        
    def save(self, shape, prefix):
        Make_base.save(self, shape, self.prefix+prefix)

    def get_cuts(self):
        length = self.working.top
        spec = self.working.spec
    
        result = [ ]
        for division in self.working.designer.divisions:
            cuts = [ ]
            for hole, above in division:
                if hole >= 0:
                    lower = spec.hole_positions[hole] + 2*spec.hole_diameters[hole]
                else:
                    lower = 0.0
                    
                if hole < len(spec.hole_positions)-1:
                    upper = spec.hole_positions[hole+1] - 2*spec.hole_diameters[hole]
                else:
                    upper = length
                    
                cut = lower + (upper-lower)*above
                cuts.append(cut)
            result.append(cuts)
        return result

    def make_segments(self, up=False, flip_top=False):
        for item in self.get_cuts():
            self.segment(item, up, flip_top)

    def make_instrument(
             self,
             inner_profile, outer_profile, 
             hole_positions, hole_diameters, hole_vert_angles, hole_horiz_angles,
             xpad, ypad, with_fingerpad,
             outside_extras = [], bore_extras = []):
        outside = shape.extrude_profile(outer_profile)
        instrument = outside.copy()        
        bore = shape.extrude_profile(inner_profile + self.dilate)
                      
        for i, pos in enumerate(hole_positions):
            angle = hole_vert_angles[i]
            radians = angle*math.pi/180.0
        
            height = outer_profile(pos)*0.5 
            inside_height = inner_profile(pos)*0.5 
            shift = math.sin(radians) * height
            
            #hole_length = (
            #    math.sqrt(height*height+shift*shift) + 
            #    hole_diameters[i]*0.5*abs(math.sin(radians)) + 
            #    4.0)
            
            hole_diameter_correction = math.cos(radians) ** -0.5
            hole_diameter = hole_diameters[i] * hole_diameter_correction
                
            cross_section = shape.squared_circle(xpad[i], ypad[i]).with_effective_diameter
            
            #h1 = inside_height*0.75
            h1 = inside_height*0.5
            shift1 = math.sin(radians)*h1
            h2 = height*1.5
            shift2 = math.sin(radians)*h2
            hole = shape.extrusion([h1,h2],
                [ cross_section(hole_diameter).offset(0.0,shift1),
                  cross_section(hole_diameter).offset(0.0,shift2) ])
            hole.rotate(1,0,0, -90)
                
            #hole = shape.prism(
            #    hole_length, hole_diameters[i],
            #    cross_section)                
            #hole.rotate(1,0,0, -90-angle)
            
            hole.rotate(0,0,1, hole_horiz_angles[i])
            hole.move(0,0,pos + shift)
            
            if with_fingerpad[i] and self.fingerpads:
                pad_height = height*0.5+0.5*math.sqrt(height**2-(hole_diameters[i]*0.5)**2)
                pad_depth = (pad_height-inside_height)
                pad_mid = pad_depth*0.25
                pad_diam = hole_diameter*1.3
                fingerpad = shape.extrude_profile(
                    profile.Profile([-pad_depth,-pad_mid,0.0],[pad_diam+pad_mid*2,pad_diam+pad_mid*2,pad_diam]),
                    cross_section=cross_section)
                fingerpad_negative = shape.extrude_profile(
                    profile.Profile([0.0,pad_mid,pad_depth],[pad_diam,pad_diam+pad_mid*8,pad_diam+pad_mid*8]),
                    cross_section=cross_section)
                
                wall_angle = -math.atan2(0.5*(outer_profile(pos+pad_diam*0.5)-outer_profile(pos-pad_diam*0.5)),pad_diam)*180.0/math.pi
                fingerpad.rotate(1,0,0, wall_angle)
                fingerpad_negative.rotate(1,0,0, wall_angle)
                
                fingerpad.move(0,0,pad_height)
                fingerpad_negative.move(0,0,pad_height)
                fingerpad.rotate(1,0,0, -90)
                fingerpad_negative.rotate(1,0,0, -90)
                fingerpad.rotate(0,0,1, hole_horiz_angles[i])
                fingerpad_negative.rotate(0,0,1, hole_horiz_angles[i])
                fingerpad.move(0,0,pos) # - 0.2*hole_diameters[i]*math.sin(radians)) #????????????????????
                fingerpad_negative.move(0,0,pos) # - 0.2*hole_diameters[i]*math.sin(radians)) #?????????????????????
                outside.add(fingerpad)
                outside.remove(fingerpad_negative)
                instrument.add(fingerpad)
                instrument.remove(fingerpad_negative)

            bore.add(hole)
            if angle or hole_horiz_angles[i]:
                outside.remove(hole)
        
        for item in outside_extras:
            outside.add(item)
            instrument.add(item)
        for item in bore_extras:
            bore.add(item)
        
        instrument.remove(bore)
        instrument.rotate(0,0,1, 180)
        
        self.working.instrument = instrument
        self.working.outside = outside
        self.working.bore = bore
        self.working.top = instrument.size()[2]        
        self.save(instrument, 'instrument')

    def segment(self, cuts, up=False, flip_top=False):
        working = self.working
        length = working.top
        remainder = working.instrument.copy()
        if self.thick_sockets:
            bore = self.working.bore
        inner = working.spec.inner
        outer = working.spec.outer
        
        if up:
            cuts = [ length-item for item in cuts[::-1] ]
            remainder.rotate(0,1,0, 180)
            remainder.move(0,0,length)
            if self.thick_sockets:
                bore = bore.copy()
                bore.rotate(0,1,0, 180)
                bore.move(0,0,length)
                
            inner = inner.reversed().moved(length)
            outer = outer.reversed().moved(length)
        
        if self.join == 'weld':
            socket = self._weld_join
        elif self.join == 'straight':
            socket = self._straight_socket 
        elif self.join == 'taper':
            socket = self._tapered_socket
        else:
            assert False, 'Unknown join type: '+self.join
        
        shapes = [ ]
        for cut in cuts:
            d1 = inner(cut)
            d4 = outer(cut)
            d5 = outer.maximum() * 2.0
            #p1 = cut-d4*0.4
            #p3 = cut+d4*0.4
            
            sock_length = d4*0.8
            p1 = cut-sock_length
            p3 = cut
            if not up and self.join != 'weld':
                p1 += sock_length
                p3 += sock_length
            
            if self.thick_sockets:
                d4_orig = d4
                d4 += min(d4*0.2, (d4-d1)*0.5)
                prof_thicker = profile.Profile(
                    [ p1-(d4-d4_orig), p1, p3 ],
                    [ (d1+d4)*0.5, d4, d4 ],
                )
                thicker = shape.extrude_profile(prof_thicker)
                thicker.remove(bore)
                remainder.add(thicker)
                del thicker
            
            mask_inside, mask_outside = socket(
                p1,
                p3,
                length,
                d1,
                d4,
                d5
                )
            
            item = remainder.copy()
            item.remove(mask_outside)                
            remainder.clip(mask_inside)
            shapes.append(item)
            del mask_inside
            del mask_outside
        shapes.append(remainder)
        shapes = shapes[::-1]
        
        for i, item in enumerate(shapes):
            if (not flip_top) or \
               (up and i != len(shapes)-1) or \
               (not up and i != 0):               
                item.rotate(0,1,0, 180)
            item.position_nicely()
            self.save(item, '%d-piece-%d' % (len(shapes),i+1))
        
        #size = outer.maximum() * 4.0
        #template = pack.Pack(size,size,5000.0)
        #packables = [ [pack.Packable([item], 0.0, 1.0)] for item in shapes ]
        #[ packed ] = pack.pack(template, packables)
        #render = packed.render_print()
        #render.position_nicely()
        #self.save(render, '%d-piece-all' % len(shapes))
        
        #self.working.segments = shapes

    def _straight_socket(
                self,
                p1,
                p3,
                length,
                d1,
                d3,
                d4
                ):       
            d2 = (d1+d3) / 2.0
            
            p2 = p1 + (d2-d1)*0.5
                    
            d1a = d1 - self.gap
            p1b = p1 - self.gap
            
            d2a = d2 - self.gap
            d2b = d2 + self.gap
            
            prof_inside = profile.Profile(
                [ p1,  p2,  p3,  length+50 ],
                [ d1a, d2a, d2a, d4 ],
                [ d1a, d2a, d4,  d4 ],
            )
            prof_outside = profile.Profile(
                [ p1b, p2,  p3,  length+50 ],
                [ d1,  d2b, d2b, d4 ],
                [ d1,  d2b, d4,  d4 ],
            )
            mask_inside = shape.extrude_profile(prof_inside)
            mask_outside = shape.extrude_profile(prof_outside)
            return mask_inside, mask_outside

    def _tapered_socket(
                self,
                p1,
                p3,
                length,
                d1,
                d4,
                d5
                ):       
            d3 = (d1+d4) / 2.0
            d2 = (d1+d3) / 2.0
            
            p2 = p1 + (d2-d1)
                    
            d1a = d1 - self.gap
            p1b = p1 - self.gap
            
            d2a = d2 - self.gap
            d2b = d2 + self.gap

            d3a = d3 - self.gap
            d3b = d3 + self.gap
            
            prof_inside = profile.Profile(
                [ p1,  p2,  p3,  length+50 ],
                [ d1a, d2a, d3a, d5 ],
                [ d1a, d2a, d5,  d5 ],
            )
            prof_outside = profile.Profile(
                [ p1b, p2,  p3,  length+50 ],
                [ d1,  d2b, d3b, d5 ],
                [ d1,  d2b, d5,  d5 ],
            )
            mask_inside = shape.extrude_profile(prof_inside)
            mask_outside = shape.extrude_profile(prof_outside)
            return mask_inside, mask_outside

    def _weld_join(self,z0,z1,zmax,d0,d1,dmax):
        prof = profile.Profile(
            [ z1, zmax+50 ],
            [ dmax, dmax]
            )
        mask_upper = shape.extrude_profile(prof)
        mask_lower = mask_upper.copy()
        
        triangle = shape.Loop([
            (0.5, 0.0),
            (0.0, math.sqrt(0.75)),
            (-0.5, 0.0),
            ])
        triangle_upper = triangle.scale(d0*0.5+self.gap)
        triangle_lower  = triangle.scale(d0*0.5-self.gap)
        d1_3 = d0*0.6666+d1*0.3334
        d2_3 = d0*0.3334+d1*0.6666
        for i in xrange(1,5):
            bump = shape.extrusion(
                [ d1_3*0.5-self.gap*0.5, d2_3*0.5-self.gap*0.5, dmax*0.5 ],
                [ triangle_upper.scale(0.0), triangle_upper, triangle_upper ]
                )
            bump.rotate(1,0,0,-90)
            bump.rotate(0,0,1,180+360.0/5*i)
            bump.move(0,0,z1)
            mask_upper.add(bump)

            bump = shape.extrusion(
                [ d1_3*0.5+self.gap*0.5, d2_3*0.5+self.gap*0.5, dmax*0.5 ],
                [ triangle_lower.scale(0.0), triangle_lower, triangle_lower ]
                )
            bump.rotate(1,0,0,-90)
            bump.rotate(0,0,1,180+360.0/5*i)
            bump.move(0,0,z1)
            mask_lower.add(bump)
        
        return mask_lower, mask_upper

        
@config.Bool_flag('mill', 'Create shapes for milling (rather than 3D printing).')
@config.Float_flag('mill_diameter', 'Milling: Bit diameter for milling (affects gap size when packing pieces).')
@config.Float_flag('mill_length', 'Milling: Wood length for milling.')
@config.Float_flag('mill_width', 'Milling: Wood width for milling.')
@config.Float_flag('mill_thickness', 'Milling: Wood thickness for milling.')
class Make_millable_instrument(Make_instrument):
    mill = False
    mill_diameter = 3.0    
    mill_length = 180.0
    mill_width = 130.0
    mill_thickness = 19.0
    
    def make_parts(self, up=False, flip_top=False, extra_packables=[ ]):
        if self.mill:
            self.make_workpieces(extra_packables)
        else:
            self.make_segments(up, flip_top)
    
    def make_workpieces(self, extra_packables=[ ]):
        length = self.working.top
        cuts = sorted(set( item/length for scheme in self.get_cuts() for item in scheme ))
        upper_segments, lower_segments = pack.plan_segments(cuts, self.mill_length / length)
        pack.cut_and_pack(
            self.working.outside, self.working.bore,
            upper_segments, lower_segments,
            xsize=self.mill_length, 
            ysize=self.mill_width, 
            zsize=self.mill_thickness,
            bit_diameter=self.mill_diameter,
            save=self.save,
            
            extra_packables=extra_packables,
            )
        


