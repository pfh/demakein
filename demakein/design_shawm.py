
import copy

from . import design, profile

from nesoni import config

def inrange(low,high,n):
    return [ (i+1)*(high-low)/(n+2)+low for i in range(1,n+1) ]

def fullrange(low,high,n):
    return [ i*(high-low)/(n-1.0)+low for i in range(n) ]


def bore_scaler(value):
    """ Scale to bore """
    @property
    def func(self):
        scale = self.bore/self._bore_baseline
        return [ item*scale for item in value ]
    return func

#@config.Float_flag('bore', 'Bore diameter at top. (ie reed diameter)')
#class Shawm_designer(design.Instrument_designer):
#    transposition = 0    
#    bore = 5.0
#    
#    closed_top = True
#    
#    #Note: The flared end is not necessary, merely decorative!
#    #      min_inner_fraction_sep is rigged to produce a nice flare.
#    
#    #inner_diameters = bore_scaler([ 35.0, 30.0, 25.0, 20.0, 15.0, 10.0, 6.0, 6.0 ])
#    inner_diameters = bore_scaler([ 75.0, 70.0, 65.0, 60.0, 55.0, 50.0, 45.0, 40.0, 35.0, 30.0, 25.0, 20.0, 15.0, 10.0, 6.0, 6.0 ])
#
#    #@property
#    #def initial_inner_fractions(self):
#    #    #return [ 0.02 ] * (len(self.inner_diameters)-2) + [ 0.1 ] #0.125
#    #    d = [ (1.0-(item/self.inner_diameters[0]))**2 for item in self.inner_diameters ]
#    #    return d[1:-1]
#    #
#    ##min_inner_fraction_sep = [ 0.001 ] * 14 + [ 0.1 ]
#    #min_inner_fraction_sep = [ 0.001 ] * 9 + [ 0.05 ] * 5 + [ 0.1 ]
#        
#    @property
#    def min_inner_fraction_sep(self):
#        #return [ 0.02 ] * (len(self.inner_diameters)-2) + [ 0.1 ] #0.125
#        d = [ 0.5* (1.0-(item/(self.inner_diameters[0]* 1.5 )))**2 for item in self.inner_diameters ]
#        return [ min(0.05, (d[i]+d[i+1])*(d[i+1]-d[i])) for i in xrange(len(self.inner_diameters)-2) ] \
#               + [0.16]
#    
#    @property
#    def initial_inner_fractions(self):
#        diams = self.inner_diameters
#        mins = [ i+0.05 for i in self.min_inner_fraction_sep ]
#        for i in xrange(1,len(mins)): mins[i] = mins[i] + mins[i-1]
#        #return [ ( i * 1.0 / len(diams) )**1.5 for i in range(1,len(diams)-1) ]
#        return [
#            #max(mins[i-1], 1.0 - 2.0*diams[i]/diams[0])
#            mins[i-1] + 1.0 - mins[-1]
#            for i in range(1,len(diams)-1)
#        ]
#
#    outer_add = True
#    outer_diameters = bore_scaler([ 16.0, 10.0 ])
#    
#    max_grad = 10.0




@config.Float_flag('bore', 'Bore diameter at top. (ie reed diameter)')
@config.Float_flag('reed_virtual_length', 'Virtual length of reed, as a multiple of bore diameter.')
@config.Float_flag('reed_virtual_top', 'Virtual diameter of top of reed, proportion of bore diameter.')
class Reed_instrument_designer(design.Instrument_designer):
    _bore_baseline = 4.0
    bore = 4.0
    
    #reed_virtual_length = 25.0
    #reed_virtual_top = 1.0
    #reed_virtual_length = 50.0
    #reed_virtual_top = 0.125
    
    #From c5 drone
    reed_virtual_length = 34.0
    reed_virtual_top = 1.0

    transposition = 0    
    closed_top = True

    def patch_instrument(self, inst):
        inst = copy.copy(inst)
        inst.true_length = inst.length
        inst.true_inner = inst.inner
        
        reed_length = self.bore * self.reed_virtual_length
        reed_top = self.bore * self.reed_virtual_top
        reed = profile.make_profile([
            (0.0, self.bore),
            (reed_length, reed_top),
            ])
        
        inst.inner = inst.inner.appended_with(reed)
        inst.length += reed_length
        return inst


class Design_reed_drone(Reed_instrument_designer):
    inner_diameters = bore_scaler([4.0, 4.0])
    outer_diameters = bore_scaler([24.0, 12.0])
    
    hole_horiz_angles = [ ]
    with_fingerpad = [ ]
    
    initial_length = design.wavelength('C4') * 0.25
    fingerings = [ ('C4', [], 1) ]
    
    divisions = [ () ]


class Design_reedpipe(Reed_instrument_designer):
    inner_diameters = bore_scaler([4.0, 4.0])
    outer_diameters = bore_scaler([12.0, 12.0])
    
    min_hole_diameters = bore_scaler([ 2.5 ] * 8)
    max_hole_diameters = bore_scaler([ 4.0 ] * 8)

    #max_hole_spacing = design.scaler([ 80, 40,40,40,None,40,40, 20 ])
    
    balance = [ 0.2, 0.075, 0.3, 0.3, 0.075, None ]
    #balance = [ None, 0.1, 0.1, 0.3, 0.3, 0.1, None ]
    #balance = [ 0.2, 0.1, None, None, 0.1, None ]
    hole_angles = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]
    hole_horiz_angles = [ -25.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 180.0 ]

    with_fingerpad = [1,1,1,1,1,1,1,1]
        
    initial_length = design.wavelength('C4') * 0.25

    fingerings = [
        ('C4',  [1,1,1,1,1,1,1,1], 1),
        ('D4',  [0,1,1,1,1,1,1,1], 1),
        ('E4',  [0,0,1,1,1,1,1,1], 1),
        ('F4',  [0,0,0,1,1,1,1,1], 1),
        ('G4',  [0,0,0,0,1,1,1,1], 1),
        ('A4',  [0,0,0,0,0,1,1,1], 1),
        #('Bb4', [0,0,0,1,1,0,1,1], 1),
        ('B4',  [0,0,0,0,0,0,1,1], 1),
        ('C5',  [0,0,0,0,0,1,0,1], 1),
        #('C#5', [0,0,0,0,0,1,1,0], 1),
        ('D5',  [0,0,0,0,0,1,0,0], 1),        
        ]

    divisions = [
        #[ (3, 0.5) ],
        #[ (3, 0.5), (7, 0.1) ],
        [ (0, 0.5), (3, 0.5), (7, 0.1) ],
        ]

class Shawm_designer(Reed_instrument_designer):
    inner_diameters = bore_scaler(
        fullrange(16.0, 4.0, 10)
        #[ 16.0, 14.0, 12.0, 10.0, 8.0, 6.0, 4.0, 1.5 ]
        ) 
    initial_inner_fractions = fullrange(0.2, 0.9, 8)
    min_inner_fraction_sep = [ 0.02 ] * 9

    outer_diameters = bore_scaler([ 70.0, 25.0, 25.0 ])
    min_outer_fraction_sep = [ 0.19, 0.8 ]
    initial_outer_fractions = [ 0.19 ]
    outer_angles = [ -35.0, 'up', 'down' ]



#@config.Float_flag('bore', 'Bore diameter at top. (ie reed diameter)')
#@config.Float_flag('tweak_reed_length', 'Reed length, in units of bore diameter.')
#@config.Float_flag('tweak_reed_tip', 'Reed constricts to this proportion of bore.')
#class Shawm_designer(design.Instrument_designer):
#    do_trim = False
#    
#    tweak_reed_length = 20.0
#    tweak_reed_tip = 0.5
#    
#
#    transposition = 0    
#    bore = 5.0
#    
#    closed_top = True
#    
##    inner_diameters = bore_scaler([ 35.0, 30.0, 25.0, 20.0, 15.0, 12.0, 9.0, 6.0, 6.0 ])
#    inner_diameters = bore_scaler([ 35.0, 25.0, 20.0, 15.0, 12.0, 9.0, 6.0, 6.0 ])
#    min_inner_fraction_sep = [ 0.05 ] * 6 + [ 0.025 ]
#
#    @property
#    def initial_inner_fractions(self):
#        d = self.inner_diameters
#        return [ (1.0 - item / d[0])**1.0 for item in d[1:-1] ]
#
#
##    outer_diameters = bore_scaler([ 75.0, 40.0, 30.0 ])
##    outer_diameters = bore_scaler([ 100.0, 60.0, 30.0 ])
#    outer_diameters = bore_scaler([ 90.0, 40.0, 20.0 ])
#    min_outer_fraction_sep = [ 0.2, 0.75 ]
#    initial_outer_fractions = [ 0.225 ]
#    outer_angles = [ -30.0, 'up', 'down' ]
#    
#    #max_grad = 10.0
#    
#    def patch_instrument(self, inst):
#        inst = copy.copy(inst)
#        
#        extra_length = self.bore * self.tweak_reed_length
#        extra_inner = profile.make_profile([
#            (0.0, self.bore),
#            (extra_length, self.bore * self.tweak_reed_tip),
#            ])
#        
#        inst.length += extra_length
#        inst.inner = inst.inner.appended_with(extra_inner)
#        inst.outer = inst.outer.clipped(0.0, inst.length)
#        return inst



@config.help("""\
Design a shawm / haut-bois / oboe / bombard. Fingering system similar to recorder.
""",
"""\
The flare at the end is purely decorative.
""")
class Design_shawm(Shawm_designer):        
    min_hole_diameters = bore_scaler([ 2.0 ] * 9)
#    max_hole_diameters = bore_scaler([ 12.0 ] * 8)
    max_hole_diameters = bore_scaler([ 6.0 ] * 9)
    
    initial_hole_diameter_fractions = [0.5]*9    
    initial_hole_fractions = [ 0.5-0.06*i for i in [7,6,5,4,3,2,1,0,0] ]

    max_hole_spacing = design.scaler([ 80, 40,40,40,None,40,40, 20 ])
    
    #balance = [ 0.2, 0.1, 0.3, 0.3, 0.1, None ]
    balance = [ None, 0.1, 0.1, 0.3, 0.3, 0.1, None ]
    #balance = [ 0.2, 0.1, None, None, 0.1, None ]
    hole_angles = [ 0.0, -30.0, -30.0, -30.0, 30.0,  0.0, 0.0, 0.0, 0.0 ]
    hole_horiz_angles = [ 30.0, -25.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 180.0 ]

    with_fingerpad = [0,1,1,1,1,1,1,1,1]
        
    initial_length = design.wavelength('B3') * 0.35

    fingerings = [
        ('B3',  [1, 1,1,1,1,1,1,1,1], 1),
        ('B4',  [1, 1,1,1,1,1,1,1,1], 2),


        ('C4',  [0, 1,1,1,1,1,1,1,1], 1),
        ('D4',  [0, 0,1,1,1,1,1,1,1], 1),
        ('E4',  [0, 0,0,1,1,1,1,1,1], 1),
        ('F4',  [0, 1,1,0,1,1,1,1,1], 1),
        ('F#4', [0, 0,1,1,0,1,1,1,1], 1),
        ('G4',  [0, 0,0,0,0,1,1,1,1], 1),
        #('G#4', [0, 0,1,1,1,0,1,1,1], 1),
        ('A4',  [0, 0,0,0,0,0,1,1,1], 1),
        ('Bb4', [0, 0,0,0,1,1,0,1,1], 1),
        ('B4',  [0, 0,0,0,0,0,0,1,1], 1),
        ('C5',  [0, 0,0,0,0,0,1,0,1], 1),
        ('C#5', [0, 0,0,0,0,0,1,1,0], 1),
        ('D5',  [0, 0,0,0,0,0,1,0,0], 1), #?
        
        ('C5',  [0, 1,1,1,1,1,1,1,1], 2),
        ('D5',  [0, 0,1,1,1,1,1,1,1], 2),

        ('E5',  [0, 0,0,1,1,1,1,1,1], 2),
        ('E5',  [0, 0,0,1,1,1,1,1,0], 2), #Register hole exactly at node for E

        ('F5',  [0, 0,1,0,1,1,1,1,1], 2),
        ('F#5', [0, 0,0,1,0,1,1,1,1], 2),
        ('G5',  [0, 0,0,0,0,1,1,1,1], 2),
        #('G#5', [0,0,0,1,0,1,1,1], 2),
        ('A5',  [0, 0,0,0,0,0,1,1,1], 2),
        #('B5',  [0,0,1,1,0,1,1,1], 2),
        #('C5',  [0,0,1,1,0,0,1,1], 2),
        #('B5',  [0,0,0,0,0,0,1,1]),
        #('C6',  [0,0,0,0,0,1,0,1]),
    ]

    divisions = [
        [ (4,0.5) ],
        [ (1,0.25), (4,0.5) ],
        [ (0,0.25), (2,0.5), (5,0.0) ],        
        ]


#@config.help("""\
#Design a shawm / haut-bois / oboe / bombard. Simple fingering system with compact hole placement.
#""",
#"""\
#The flare at the end is purely decorative.
#""")
#class Design_folk_shawm(Shawm_designer):
#    # Don't need thickness for cross fingerings, so may as well make wall thinner
##    outer_add = True
##    outer_diameters = bore_scaler([ 10.0, 8.0 ])
#
#    min_hole_diameters = bore_scaler([ 5.0 ] * 6)
#    max_hole_diameters = bore_scaler([ 12.0 ] * 6)
#    
#    #initial_hole_diameter_fractions = inrange(0.5,0.0,6)    
#    initial_hole_fractions = [ 0.5-0.06*i for i in range(5,-1,-1) ]
#
#    balance = [ 0.05, None, None, 0.05 ]
#    hole_angles = [ -30.0, 30.0, 30.0, -30.0, 0.0, 30.0 ]
#
#    max_hole_spacing = design.scaler([ 32,32,None,32,32 ])
#    
#    initial_length = design.wavelength('D4') * 0.4
#
#    fingerings = [
#        ('D4',  [1,1,1,1,1,1]),
#        ('E4',  [0,1,1,1,1,1]),
#        ('F#4', [0,0,1,1,1,1]),
#        ('G4',  [0,0,0,1,1,1]),
#        ('A4',  [0,0,0,0,1,1]),
#        ('B4',  [0,0,0,0,0,1]),
#        ('C5',  [0,0,0,1,1,0]),
#        ('C#5', [0,0,0,0,0,0]),
#        
#        ('D5',  [1,1,1,1,1,1]),
#        ('D5',  [1,1,1,1,1,0]),
#
#        ('E5',  [0,1,1,1,1,1]),
#        #('E5',  [0,1,1,1,1,0]),
#
#        ('F#5', [0,0,1,1,1,1]),
#        ('G5',  [0,0,0,1,1,1]),
#        ('A5',  [0,0,0,0,1,1]),
#        ('B5',  [0,0,0,0,0,1]),
#        #('C#6', [0,0,0,0,0,0]),
#        
#        #More harmonics of basic horn
#        ('D4*3',  [1,1,1,1,1,1]),
#        ('D4*4',  [1,1,1,1,1,1]),
#
#        #('D4*5',  [1,1,1,1,1,1]),
#        #('D4*6',  [1,1,1,1,1,1]),
#        #('D4*7',  [1,1,1,1,1,1]),
#        #('D4*8',  [1,1,1,1,1,1]),
#        
#        #('D4*9',  [1,1,1,1,1,1]),
#        #('D4*10', [1,1,1,1,1,1]),
#        #('D4*11', [1,1,1,1,1,1]),
#        #('D4*12', [1,1,1,1,1,1]),
#    ]    


@config.help("""\
Design a shawm / haut-bois / oboe / bombard. Simple fingering system with compact hole placement.
""",
"""\
The flare at the end is purely decorative.
""")
class Design_folk_shawm(Shawm_designer):
    # Don't need thickness for cross fingerings, so may as well make wall thinner
#    outer_add = True
#    outer_diameters = bore_scaler([ 10.0, 8.0 ])

##    min_hole_diameters = bore_scaler([ 3.0 ] * 6)
#    min_hole_diameters = bore_scaler([ 4.5 ] * 6)
##    max_hole_diameters = bore_scaler([ 12.0 ] * 6)
#    max_hole_diameters = bore_scaler([ 16.0 ] * 6)
#    initial_hole_fractions = [ 0.5-0.06*i for i in range(5,-1,-1) ]

    min_hole_diameters = bore_scaler([ 2.0 ] * 7)
    max_hole_diameters = bore_scaler([ 12.0 ] * 7)
    
    initial_hole_diameter_fractions = inrange(1.0,0.5,7)   
    initial_hole_fractions = [ 0.75-0.1*i for i in range(6,-1,-1) ]

    balance = [ None, 0.05, None, None, 0.05 ]
    #hole_angles = [ -30.0, 30.0, 30.0, -30.0, 0.0, 30.0 ]
    #hole_angles = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]

    #hole_horiz_angles = [ -5.0, 0.0, 0.0,  5.0, 0.0, 0.0 ]
    hole_horiz_angles = [ 45.0, 0.0, 0.0, 0.0,  0.0, 0.0, 0.0 ]

#    max_hole_spacing = design.scaler([ 32,32,None,32,32, None ])
#    max_hole_spacing = design.scaler([ 28,28,None,28,28 ])
#    max_hole_spacing = design.scaler([ None,40,40,None,40,40 ])
    
    with_fingerpad = [0,1,1,1,1,1,1]
    
    initial_length = design.wavelength('C4') * 0.5
    #max_length     = design.wavelength('C4') * 0.6

    fingerings = [
        ('C4',  [1, 1,1,1,1,1,1], 1),
        ('C5',  [1, 1,1,1,1,1,1], 2),
        ('C4*3',  [1, 1,1,1,1,1,1], 3),
        ('C4*4',  [1, 1,1,1,1,1,1], 4),

        ('D4',  [0, 1,1,1,1,1,1], 1),
        ('E4',  [0, 0,1,1,1,1,1], 1),
        ('F#4', [0, 0,0,1,1,1,1], 1),
        ('G4',  [0, 0,0,0,1,1,1], 1),
        ('A4',  [0, 0,0,0,0,1,1], 1),
        ('B4',  [0, 0,0,0,0,0,1], 1),
#        ('C5',  [0, 0,0,0,1,1,0], 1),
        ('C#5', [0, 0,0,0,0,0,0], 1),

        ('D5',  [0, 1,1,1,1,1,0], 2),
        ('D5',  [0, 1,1,1,1,1,1], 2),

        ('E5',  [0, 0,1,1,1,1,1], 2),
        #('E5',  [0,1,1,1,1,0]),

        ('F#5', [0, 0,0,1,1,1,1], 2),
        ('G5',  [0, 0,0,0,1,1,1], 2),
        ('A5',  [0, 0,0,0,0,1,1], 2),
        ('B5',  [0, 0,0,0,0,0,1], 2),
        ('C#6', [0, 0,0,0,0,0,0], 2),
#        ('D6',  [0, 1,1,1,1,1,1], 4),
        


        #('D4*3',  [0, 1,1,1,1,1,1], 3),
        #('E4*3',  [0, 0,1,1,1,1,1], 3),
        #('F#4*3', [0, 0,0,1,1,1,1], 3),
        #('G4*3',  [0, 0,0,0,1,1,1], 3),
        #('A4*3',  [0, 0,0,0,0,1,1], 3),
        #('B4*3',  [0, 0,0,0,0,0,1], 3),
        #('C#5*3', [0, 0,0,0,0,0,0], 3),
        #
        #('D4*4',  [0, 1,1,1,1,1,1], 4),
        #('E4*4',  [0, 0,1,1,1,1,1], 4),
        #('F#4*4', [0, 0,0,1,1,1,1], 4),
        #('G4*4',  [0, 0,0,0,1,1,1], 4),
        #('A4*4',  [0, 0,0,0,0,1,1], 4),
        #('B4*4',  [0, 0,0,0,0,0,1], 4),
        #('C#5*4', [0, 0,0,0,0,0,0], 4),

    ]   
    
    divisions = [
        [ (3,0.5) ],
        [ (0,0.5), (3,0.0) ],
        [ (0,0.5), (3,0.25), (5,0.5) ],
        [ (-1,0.5), (0,0.5), (3,0.25), (5,0.5) ],
        #[ (-1,0.45), (-1,0.9), (2,0.0), (2,0.9), (5,0.0), (5,0.5) ],
        ] 


