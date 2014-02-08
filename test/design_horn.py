
import nesoni, demakein
from demakein import design

class Design_horn(demakein.design.Instrument_designer):
    closed_top = True
    
#    inner_diameters = [ 70.0, 50.0, 30.0, 10.0, 3.0, 3.0, 15.0 ]
    inner_diameters = [ 50.0, 40.0, 30.0, 20.0, 10.0, 5.0, 2.5, 2.5, 15.0 ]
    
    min_inner_fraction_sep = [ 0.001 ] * (len(inner_diameters)-2) + [ 0.01 ]
    
    initial_inner_fractions = [ 
        1.0 - item / inner_diameters[0]
        for item in inner_diameters[1:-1]
        ]
    
    outer_diameters = [ 8.0, 8.0 ]
    outer_add = True
    
    initial_length = demakein.design.wavelength('C4') * 0.5
    fingerings = [
        ('C4',    []),
        ('C4*2',  []),
        ('C4*3',  []),
        ('C4*4',  []),
        ('C4*5',  []),
        ('C4*6',  []),
        ('C4*7',  []),
        ('C4*8',  []),
        ('C4*9',  []),
        #('C4*10', []),
        #('C4*11', []),
        #('C4*12', []),
        ]
    
    divisions = [
        #[(-1,0.333),(-1,0.6666)],
        #[(-1,0.25),(-1,0.5),(-1,0.75)],
        [(-1,i/8.0) for i in xrange(1,8) ],
        ]

if __name__ == '__main__': 
    nesoni.run_tool(Design_horn)