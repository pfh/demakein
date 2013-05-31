#!/usr/bin/env python3

"""

Note:
Without lip height adjustment (sop_flute_3), flute is a semitone flat unless cork pushed far in.

5mm was to much (sop_flute_2).

"""



import profile, design

from nesoni import config

fingerings = {
    'pflute' : [
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
    ],
        
    'folk' : [
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
        ('C#6',  [1,1,1,0,0,0]),
        ('D6',   [1,1,1,1,1,0]),

        #('E6',   [0,1,1,1,1,1]),
        #('F6',   [1,0,1,1,1,1]),
        #('G6',   [1,0,0,1,1,1]),
        #('A6',   [0,1,1,1,1,0]), #?        
    ],

    'minor' : [
        ('D4',   [1,1,1,1,1,1]),
        ('E4',   [0,1,1,1,1,1]),
        ('F4',   [0,0,1,1,1,1]),
        ('G4',   [0,0,0,1,1,1]),
        ('A4',   [0,0,0,0,1,1]),
        ('Bb4',  [0,0,0,0,0,1]),
        ('C5',   [0,0,0,0,0,0]),
        ('D5',   [1,1,1,1,1,1]),
        ('E5',   [0,1,1,1,1,1]),
        ('F5',   [0,0,1,1,1,1]),
        ('G5',   [0,0,0,1,1,1]),
        ('A5',   [0,0,0,0,1,1]),
        ('Bb5',  [0,0,0,0,0,1]),
        ('C6',   [0,0,0,0,0,0]),
        ('D6',   [1,1,1,1,1,1]),
    ],
    
    'dorian' : [
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
    ],
}

@config.Float_flag('embextra', 
    'Constant controlling extra effective height of the embouchure hole due to lips, etc. '
    'Small adjustments of this value will change the angle at which the flute needs to be blown '
    'in order to be in tune.')
class Flute_designer(design.Instrument_designer):
    closed_top = True
    
    fingering_system = 'pflute'
    
    @property
    def fingerings(self):
        return [
           (note, fingering+[0])
           for note, fingering in fingerings[self.fingering_system]
           ]
    
    # 2.5/8 = 0.3    ~ 20 cents flat
    # 5/8 = 0.6      ~ too high
    # 0.45 (sop_flute_5)   ~ a tiny bit low
    # 0.53 (sop_flute_8)   ~ a tiny biy low?, needed to push cork in 1.5mm
    #                        + perfect, printed plastic sop flute
    # 0.56                 ~ definitely high, printed plastic sop flute
    
    embextra = 0.53
    
    @property
    def hole_extra_height_by_diameter(self):
        return [ 0.0 ] * 6 + [ self.embextra ]
    
    #hole_extra_height_by_diameter = [ 0.0 ] * 6 + [ 0.53 ]
    
    initial_length = design.wavelength('D4') * 0.5
    
    initial_hole_fractions = [ 0.175 + 0.5*i/6 for i in range(6) ] + [ 0.97 ]

    
    min_hole_diameters = design.sqrt_scaler([ 6.5 ] * 6  + [ 12.2 ])
    max_hole_diameters = design.sqrt_scaler([ 11.4 ] * 6 + [ 13.9 ])


class Tapered_flute(Flute_designer):
    inner_diameters = design.sqrt_scaler([ 14.0, 14.0, 18.4, 21.0, 18.4, 18.4 ])
    initial_inner_fractions = [ 0.25, 0.7, 0.8, 0.9 ]
    min_inner_fraction_sep = [ 0.0, 0.0, 0.03, 0.0, 0.0 ]

    outer_diameters = design.sqrt_scaler([ 22.1, 32.0, 26.1 ])

    initial_outer_fractions = [ 0.666 ]
    min_outer_fraction_sep = [ 0.666, 0.0 ] #Looks and feels nicer


class Straight_flute(Flute_designer):
    inner_diameters = design.sqrt_scaler([ 18.4, 18.4, 21.0, 18.4, 18.4 ])
    initial_inner_fractions = [ 0.7, 0.8, 0.9 ]
    
    min_inner_fraction_sep = [ 0.5, 0.03, 0.0, 0.0 ]
    # Note constraint of bulge to upper half of tube.
    # There seems to be an alternate solution for the folk flute
    #   where it's stretched out over 3/4 of the flute's length.

    outer_diameters = design.sqrt_scaler([ 28.0, 28.0 ])

    #initial_outer_fractions = [ 0.666 ]
    #min_outer_fraction_sep = [ 0.666, 0.0 ] #Looks and feels nicer



class Pflute(Flute_designer):
    fingering_system = 'pflute'
    balance = [ 0.05, None, None, 0.05 ]    
    hole_angles = [ -30.0, -30.0, 30.0, -30.0, 30.0, -30.0, 0.0 ]

@config.help("""\
Design a flute with a tapered bore and recorder-like fingering system.
""")
class Design_tapered_pflute(Tapered_flute, Pflute): pass

@config.help("""\
Design a flute with a straight bore and recorder-like fingering system.
""")
class Design_straight_pflute(Straight_flute, Pflute): pass

class Folk_flute(Flute_designer):
    fingering_system = 'folk'
    balance = [ 0.05, None, None, 0.05 ]    
    hole_angles = [ -30.0, 30.0, 0.0,  0.0, 0.0, 0.0, 0.0 ]
    min_hole_diameters = design.sqrt_scaler([ 7.5 ] * 6  + [ 12.2 ])
    max_hole_diameters = design.sqrt_scaler([ 11.4 ] * 6 + [ 13.9 ])

@config.help("""\
Design a flute with a tapered bore and pennywhistle-like fingering system.
""")
class Design_tapered_folk_flute(Tapered_flute, Folk_flute): pass

@config.help("""\
Design a flute with a straight bore and pennywhistle-like fingering system.
""")
class Design_straight_folk_flute(Straight_flute, Folk_flute): pass



