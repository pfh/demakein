#!/usr/bin/env python3

import copy, math

import profile, design

from nesoni import config

pflute_fingerings = [
        ('D4',   [1,1,1,1,1,1]),
        ('E4',   [0,1,1,1,1,1]),
        ('F4',   [1,0,1,1,1,1]),
        ('F#4',  [1,1,0,1,1,1]),
        ('G4',   [0,0,0,1,1,1]),
        ('G#4',  [1,1,1,0,1,1]),
        ('A4',   [0,0,0,0,1,1]),
        ('Bb4',  [0,0,1,1,0,1]),
        ('B4',   [0,0,0,0,0,1]),            
        ('C5',   [0,0,0,1,1,0]),                        
        ('C#5',  [0,0,0,0,0,0]), #Note: 0,0,1,0,0,0 lets you put a finger down           

        ('D5',   [1,1,1,1,1,0]),
        ('D5',   [1,1,1,1,1,1]),

        ('E5',   [0,1,1,1,1,1]),
        ('F5',   [1,0,1,1,1,1]),
        ('F#5',  [0,1,0,1,1,1]),
        ('G5',   [0,0,0,1,1,1]),
        #('G#5',  [0,0,1,0,1,1]),
        ('A5',   [0,0,0,0,1,1]),
       ('Bb5',  [1,1,1,0,1,1]), 
        ('B5',   [0,1,1,0,1,1]),
         
#        ('C6',   [1,1,1,0,1,0]),  # 1,0,1,0,1,0 may also be good 
        ('C6', [0,1,1,0,0,1]),
        #('C#6',  [1,1,1,0,0,0]),
        
        ('D6',   [1,1,1,1,1,1]), 
        #('E6',   [0,1,0,0,1,1]), 
    ]
        
folk_fingerings = [
        ('D4',   [1,1,1,1,1,1]),
        ('E4',   [0,1,1,1,1,1]),
        ('F#4',  [0,0,1,1,1,1]),
        ('G4',   [0,0,0,1,1,1]),
        ('A4',   [0,0,0,0,1,1]),
        ('B4',   [0,0,0,0,0,1]),
        ('C5',   [0,0,0,1,1,0]),
        ('C#5',  [0,0,0,0,0,0]),
        ('D5',   [1,1,1,1,1,0]),
        ('E5',   [0,1,1,1,1,1]),
        ('F#5',  [0,0,1,1,1,1]),
        ('G5',   [0,0,0,1,1,1]),
        ('A5',   [0,0,0,0,1,1]),
        ('B5',   [0,0,0,0,0,1]),
        #('C#6',  [1,1,1,0,0,0]),
        ('C#6',  [0,0,0,0,0,0]),
        ('D6',   [1,1,1,1,1,0]),

      #  ('D4*3',   [1,1,1,1,1,1]),
      #  ('E4*3',   [0,1,1,1,1,1]),
      #  ('F#4*3',  [0,0,1,1,1,1]),
      #  ('G4*3',   [0,0,0,1,1,1]),
      #  ('A4*3',   [0,0,0,0,1,1]),
        #('B4*3',   [0,0,0,0,0,1]),
        #('C#5*3',  [0,0,0,0,0,0]),

        #('E6',   [0,1,1,1,1,1]),
        #('F6',   [1,0,1,1,1,1]),
        #('G6',   [1,0,0,1,1,1]),
        #('A6',   [0,1,1,1,1,0]), #?        
    ]

dorian_fingerings = [
        ('D4',   [1,1,1,1,1,1]),
        ('E4',   [0,1,1,1,1,1]),
        ('F4',   [0,0,1,1,1,1]),
        ('G4',   [0,0,0,1,1,1]),
        ('A4',   [0,0,0,0,1,1]),
        ('Bb4',  [0,0,1,1,0,1]),
        ('B4',   [0,0,0,0,0,1]),
        ('C5',   [0,0,0,0,0,0]),
        ('D5',   [1,1,1,1,1,1]),
        ('E5',   [0,1,1,1,1,1]),
        ('F5',   [0,0,1,1,1,1]),
        ('G5',   [0,0,0,1,1,1]),
        ('A5',   [0,0,0,0,1,1]),
        ('Bb5',  [0,0,0,1,0,1]),
        ('B5',   [0,0,0,0,0,1]),
        ('C6',   [0,0,0,0,0,0]),
        ('D6',   [1,1,1,1,1,1]),
    ]

def fingerings_with_embouchure(fingerings):
    return [
       (note, fingering+[0])
       for note, fingering in fingerings
       ]
    
    

@config.Float_flag('embextra', 
    'Constant controlling extra effective height of the embouchure hole due to lips, etc. '
    'Small adjustments of this value will change the angle at which the flute needs to be blown '
    'in order to be in tune.')
class Flute_designer(design.Instrument_designer):
    closed_top = True
    
    # 2.5/8 = 0.3    ~ 20 cents flat
    # 5/8 = 0.6      ~ too high
    # 0.45 (sop_flute_5)   ~ a tiny bit low
    # 0.53 (sop_flute_8)   ~ a tiny bit low?, needed to push cork in 1.5mm
    #                        + perfect, printed plastic sop flute
    # 0.56                 ~ definitely high, printed plastic sop flute
    
    embextra = 0.53

    def patch_instrument(self, inst):
        inst = copy.copy(inst)        
        inst.hole_lengths[-1] += inst.hole_diameters[-1] * self.embextra
        return inst

    def calc_emission(self, emission, fingers):
        """ Emission is relative to embouchure hole
            ie we assume the amplitude at the embouchure hole is fixed. """
        return math.sqrt(sum(item*item for item in emission[:-1])) / emission[-1]

        
#    
#    @property
#    def hole_extra_height_by_diameter(self):
#        return [ 0.0 ] * 6 + [ self.embextra ]
    
    #hole_extra_height_by_diameter = [ 0.0 ] * 6 + [ 0.53 ]
    
    initial_length = design.wavelength('D4') * 0.5

    n_holes = 7
    
    @property
    def initial_hole_fractions(self):
        return [ 0.175 + 0.5*i/(self.n_holes-1) for i in range(self.n_holes-1) ] + [ 0.97 ]

    
#    min_hole_diameters = design.sqrt_scaler([ 6.5 ] * 6  + [ 12.2 ])
#    max_hole_diameters = design.sqrt_scaler([ 11.4 ] * 6 + [ 13.9 ])
#    max_hole_diameters = design.sqrt_scaler([ 11.4 ] * 6 + [ 10.5 ])

#    min_hole_diameters = design.power_scaler(1/3., [ 3.0 ] * 6  + [ 11.3 ])
#    max_hole_diameters = design.power_scaler(1/3., [ 11.4 ] * 6 + [ 11.4 ])
    
    @property
    def min_hole_diameters(self):
        x = [3.0]*(self.n_holes-1) + [11.3]
        scale = self.scale ** (1./3)
        return [ item*scale for item in x ]

    @property
    def max_hole_diameters(self):
        x = [11.4]*(self.n_holes-1) + [11.4]
        scale = self.scale ** (1./3)
        return [ item*scale for item in x ]


    # These assume a six hole flute, and must be overridden on flutes with a different number of holes:

    hole_horiz_angles = [0.0, 0.0, 0.0, 5.0, 0.0, 0.0, 0.0]    

    divisions = [
        [ (5, 0.0) ],
        [ (2, 0.0), (5, 0.333) ],
        [ (-1, 0.9), (2, 0.0), (5, 0.333), ],
        [ (-1, 0.9), (2,0.0), (5,0.0), (5,0.7) ],
        ]


@config.Float_flag('inner_taper', 'Amount of tapering of bore. Smaller = more tapered.')
@config.Float_flag('outer_taper', 'Amount of tapering of exterior. Smaller = more tapered.')
class Tapered_flute(Flute_designer):
    inner_taper = 0.75
    outer_taper = 0.85
    
    #inner_diameters = design.sqrt_scaler([ 14.0, 14.0, 18.4, 21.0, 18.4, 18.4 ])
    @property
    def inner_diameters(self):
        scale = self.scale ** (1./2)
        return [
            18.4 * self.inner_taper * scale,
            18.4 * self.inner_taper * scale,
            18.4 * (0.5+self.inner_taper*0.5) * scale,
            18.4 * scale,
            21.0 * scale,
            21.0 * scale,
            18.4 * scale,
            18.4 * scale,
            ]

    #initial_inner_fractions = [ 0.25, 0.75 ]
    #min_inner_fraction_sep = [ 0.0, 0.0, 0.0 ]
    
    initial_inner_fractions = [ 0.25,  0.3,  0.7, 0.8,0.81, 0.9 ]
    min_inner_fraction_sep = [ 0.01, 0.1,0.1, 0.01, 0.01, 0.01, 0.01 ]

    #outer_diameters = design.sqrt_scaler([ 22.1, 32.0, 26.1 ])
    @property
    def outer_diameters(self):
        scale = self.scale ** (1./2)
        return [
            29.0 * self.outer_taper * scale,
            29.0 * self.outer_taper * scale,
            29.0 * scale,
            29.0 * scale,
            #30.0 * scale,
            #30.0 * scale,
            #32.0 * scale,
            #29.0 * scale,
            ]

    initial_outer_fractions = [ 0.01, 0.666 ]
    min_outer_fraction_sep = [ 0.0, 0.5, 0.0 ] #Looks and feels nicer

#
#class Straight_flute(Flute_designer):
#    inner_diameters = design.sqrt_scaler([ 18.4, 18.4, 21.0, 18.4, 17.0 ])
#    initial_inner_fractions = [ 0.7, 0.8, 0.9 ]    
#    min_inner_fraction_sep = [ 0.5, 0.03, 0.0, 0.0 ]
#    # Note constraint of bulge to upper half of tube.
#    # There seems to be an alternate solution for the folk flute
#    #   where it's stretched out over 3/4 of the flute's length.
#
#    outer_diameters = design.sqrt_scaler([ 28.0, 28.0 ])
#
#    #initial_outer_fractions = [ 0.666 ]
#    #min_outer_fraction_sep = [ 0.666, 0.0 ] #Looks and feels nicer
#

@config.help(
    'Design a flute with a recorder-like fingering system.'
    )
class Design_pflute(Tapered_flute):
    fingerings = fingerings_with_embouchure(pflute_fingerings)
    balance = [ 0.1, None, None, 0.05 ]    
    #hole_angles = [ -30.0, -30.0, 30.0, -30.0, 30.0, -30.0, 0.0 ]
    #hole_angles = [ 30.0, -30.0, 30.0, 0.0, 0.0, 0.0, 0.0 ]
    hole_angles = [ 30.0, -30.0, 30.0, 0.0, 0.0, 0.0, 0.0 ]

    max_hole_spacing = design.scaler([ 45.0, 45.0, None, 45.0, 45.0, None ])


@config.help(
    'Design a flute with a pennywhistle-like fingering system.'
    )
class Design_folk_flute(Tapered_flute):
    fingerings = fingerings_with_embouchure(folk_fingerings)
    balance = [ 0.01, None, None, 0.01 ]    
    hole_angles = [ -30.0, 30.0, 30.0,  -30.0, 0.0, 30.0, 0.0 ]
    #min_hole_diameters = design.sqrt_scaler([ 7.5 ] * 6  + [ 12.2 ])
    #max_hole_diameters = design.sqrt_scaler([ 11.4 ] * 6 + [ 13.9 ])
    
    max_hole_spacing = design.scaler([ 35.0, 35.0, None, 35.0, 35.0, None ])


#
#class With_tuning_holes(Design_pflute):
#    #@property
#    #def n_holes(self):
#    #    x = super(With_tuning_holes,self).n_holes
#    #    print x
#    #    return 1+x
#    
#    tuning_holes = 2
#    
#    @property
#    def min_hole_diameters(self):
#        x = super(With_tuning_holes,self).min_hole_diameters
#        return [ 0.1 ]*self.tuning_holes+x
#    @property
#    def max_hole_diameters(self):
#        x = super(With_tuning_holes,self).max_hole_diameters
#        d = self.inner_diameters[0]
#        return [d*0.5]*self.tuning_holes+x
#    @property
#    def balance(self):
#        x = super(With_tuning_holes,self).balance
#        return [None]*self.tuning_holes+x
#    @property
#    def max_hole_spacing(self):
#        x = super(With_tuning_holes,self).max_hole_spacing
#        return [None]*self.tuning_holes+x
#    @property
#    def initial_hole_fractions(self):
#        x = super(With_tuning_holes,self).initial_hole_fractions
#        return [ (i+1.0)/(self.tuning_holes+1.0) for i in xrange(self.tuning_holes) ]+x
#    @property
#    def hole_angles(self):
#        x = super(With_tuning_holes,self).hole_angles
#        return [0.0]*self.tuning_holes+x
#    @property
#    def fingerings(self):
#        x = super(With_tuning_holes,self).fingerings
#        return [ (a,[0]*self.tuning_holes+b) for a,b in x ]
#







