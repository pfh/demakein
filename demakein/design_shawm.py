

import design

from nesoni import config

def inrange(low,high,n):
    return [ (i+1)*(high-low)/(n+2)+low for i in range(1,n+1) ]


def bore_scaler(value):
    """ Scale to bore, 6mm as baseline """
    @property
    def func(self):
        scale = self.bore/6.0
        return [ item*scale for item in value ]
    return func

@config.Float_flag('bore', 'Bore diameter at top. (ie reed diameter)')
class Shawm_designer(design.Instrument_designer):
    transposition = 0    
    bore = 4.0
    
    closed_top = True
    
    #Note: The flared end is not necessary, merely decorative!
    #      min_inner_fraction_sep is rigged to produce a nice flare.
    
    #inner_diameters = bore_scaler([ 35.0, 30.0, 25.0, 20.0, 15.0, 10.0, 6.0, 6.0 ])
    inner_diameters = bore_scaler([ 75.0, 70.0, 65.0, 60.0, 55.0, 50.0, 45.0, 40.0, 35.0, 30.0, 25.0, 20.0, 15.0, 10.0, 6.0, 6.0 ])
    
    @property
    def min_inner_fraction_sep(self):
        #return [ 0.02 ] * (len(self.inner_diameters)-2) + [ 0.1 ] #0.125
        d = [ (1.0-(item/self.inner_diameters[0]))**2 for item in self.inner_diameters ]
        return [ min(0.05, (d[i]+d[i+1])*(d[i+1]-d[i])) for i in xrange(len(self.inner_diameters)-2) ] + [0.1] #Cheat

    @property
    def initial_inner_fractions(self):
        diams = self.inner_diameters
        mins = [ i+0.01 for i in self.min_inner_fraction_sep ]
        for i in xrange(1,len(mins)): mins[i] = mins[i] + mins[i-1]
        #return [ ( i * 1.0 / len(diams) )**1.5 for i in range(1,len(diams)-1) ]
        return [
            max(mins[i-1], 1.0 - 2.0*diams[i]/diams[0])
            for i in range(1,len(diams)-1)
        ]

    outer_add = True
    outer_diameters = bore_scaler([ 16.0, 10.0 ])
    
    max_grad = 10.0


@config.help("""\
Design a shawm / haut-bois / oboe / bombard. Fingering system similar to recorder.
""",
"""\
The flare at the end is purely decorative.
""")
class Design_shawm(Shawm_designer):    
    min_hole_diameters = bore_scaler([ 4.5 ] * 8)
    max_hole_diameters = bore_scaler([ 12.0 ] * 8)
    
    initial_hole_diameter_fractions = [0.25]*8    
    initial_hole_fractions = [ 0.5-0.06*i for i in [6,5,4,3,2,1,0,0] ]

    max_hole_spacing = design.scaler([ 40,40,40,None,40,40, 20 ])
    
    balance = [ 0.2, 0.1, 0.3, 0.3, 0.1, None ]
    #balance = [ 0.2, 0.1, None, None, 0.1, None ]
    hole_angles = [ -30.0, -30.0, -30.0, 30.0,  0.0, 0.0, 0.0, 0.0 ]
    hole_horiz_angles = [ -20.0 ] + [ 0.0 ] * 6 + [ 180.0 ]
    
    initial_length = design.wavelength('C4') * 0.4

    fingerings = [
        ('C4',  [1,1,1,1,1,1,1,1]),
        ('D4',  [0,1,1,1,1,1,1,1]),
        ('E4',  [0,0,1,1,1,1,1,1]),
        ('F4',  [1,1,0,1,1,1,1,1]),
        ('F#4', [0,1,1,0,1,1,1,1]),
        ('G4',  [0,0,0,0,1,1,1,1]),
        ('G#4', [0,1,1,1,0,1,1,1]),
        ('A4',  [0,0,0,0,0,1,1,1]),
        ('Bb4', [0,0,0,1,1,0,1,1]),
        ('B4',  [0,0,0,0,0,0,1,1]),
        ('C5',  [0,0,0,0,0,1,0,1]),
        ('C#5', [0,0,0,0,0,1,1,0]),
        ('D5',  [0,0,0,0,0,1,0,0]),
        
        ('C5',  [1,1,1,1,1,1,1,1]),
        ('D5',  [0,1,1,1,1,1,1,1]),

        ('E5',  [0,0,1,1,1,1,1,1]),
        ('E5',  [0,0,1,1,1,1,1,0]), #Register hole exactly at node for E

        ('F5',  [0,1,0,1,1,1,1,1]),
        ('F#5', [0,0,1,0,1,1,1,1]),
        ('G5',  [0,0,0,0,1,1,1,1]),
        #('G#5', [0,0,0,1,0,1,1,1]),
        ('A5',  [0,0,0,0,0,1,1,1]),
        #('B5',  [0,0,1,1,0,1,1,1]),
        #('C5',  [0,0,1,1,0,0,1,1]),
        #('B5',  [0,0,0,0,0,0,1,1]),
        #('C6',  [0,0,0,0,0,1,0,1]),
        
        #More harmonics of basic horn
        
        ('C4*3',  [1,1,1,1,1,1,1,1]),
        ('C4*4',  [1,1,1,1,1,1,1,1]),
        
        #('C4*5',  [1,1,1,1,1,1,1,1]),
        #('C4*6',  [1,1,1,1,1,1,1,1]),
        #('C4*7',  [1,1,1,1,1,1,1,1]),
        #('C4*8',  [1,1,1,1,1,1,1,1]),
        #
        #('C4*9',  [1,1,1,1,1,1,1,1]),
        #('C4*10', [1,1,1,1,1,1,1,1]),
        #('C4*11', [1,1,1,1,1,1,1,1]),
        #('C4*12', [1,1,1,1,1,1,1,1]),
    ]

    divisions = [
        [ (3,0.5) ],
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

    min_hole_diameters = bore_scaler([ 3.0 ] * 6)
    max_hole_diameters = bore_scaler([ 12.0 ] * 6)
    
    #initial_hole_diameter_fractions = inrange(0.5,0.0,6)    
    initial_hole_fractions = [ 0.5-0.06*i for i in range(5,-1,-1) ]

    balance = [ 0.05, None, None, 0.05 ]
    #hole_angles = [ -30.0, 30.0, 30.0, -30.0, 0.0, 30.0, 0.0 ]
    hole_angles = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]

    hole_horiz_angles = [ -5.0, 0.0, 0.0,  5.0, 0.0, 0.0 ]

#    max_hole_spacing = design.scaler([ 32,32,None,32,32, None ])
    max_hole_spacing = design.scaler([ 28,28,None,28,28 ])
    
    initial_length = design.wavelength('D4') * 0.4

    fingerings = [
        ('D4',  [1,1,1,1,1,1]),
        ('E4',  [0,1,1,1,1,1]),
        ('F#4', [0,0,1,1,1,1]),
        ('G4',  [0,0,0,1,1,1]),
        ('A4',  [0,0,0,0,1,1]),
        ('B4',  [0,0,0,0,0,1]),
        ('C5',  [0,0,0,1,1,0]),
        ('C#5', [0,0,0,0,0,0]),
        
        ('D5',  [1,1,1,1,1,0]),
        ('D5',  [1,1,1,1,1,1]),

        ('E5',  [0,1,1,1,1,1]),
        #('E5',  [0,1,1,1,1,0]),

        ('F#5', [0,0,1,1,1,1]),
        ('G5',  [0,0,0,1,1,1]),
        ('A5',  [0,0,0,0,1,1]),
        ('B5',  [0,0,0,0,0,1]),
        #('C#6', [0,0,0,0,0,0, 0]),
        ('D6',  [1,1,1,1,1,1]),
        
        #More harmonics of basic horn
      #  ('D4*3',  [1,1,1,1,1,1]),
      #  ('D4*4',  [1,1,1,1,1,1]),

        #('D4*5',  [1,1,1,1,1,1]),
        #('D4*6',  [1,1,1,1,1,1]),
        #('D4*7',  [1,1,1,1,1,1]),
        #('D4*8',  [1,1,1,1,1,1]),
        
        #('D4*9',  [1,1,1,1,1,1]),
        #('D4*10', [1,1,1,1,1,1]),
        #('D4*11', [1,1,1,1,1,1]),
        #('D4*12', [1,1,1,1,1,1]),
    ]   
    
    divisions = [
        [ (2,0.5) ],
        [ (-1,0.9), (5,0.0) ],
        [ (-1,0.9), (2,0.5), (5,0.0) ],
        [ (-1,0.45), (-1,0.9), (2,0.0), (2,0.9), (5,0.0), (5,0.5) ],
        ] 


