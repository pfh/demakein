"""

A basic reedpipe.

Note that the finger holes are underconstrained
by the fingering system.
Constraints such as balance and min_hole_spacing
can be added to produce a comfortable instrument.

Note also the reed has some virtual length, 
so the real instrument length will be shorter than designed.

"""

import demakein, nesoni

class Reedpipe(demakein.design.Instrument_designer):
    closed_top = True

    inner_diameters = [ 6.0, 6.0 ]
    outer_diameters = [ 10.0, 10.0 ]
    
    min_hole_diameters = [ 3.0 ]*7
    max_hole_diameters = [ 5.0 ]*7
    
    #min_hole_spacing = [ 15.0 ]*6
    #and/or
    balance = [ 0.07 ]*5
    
    initial_length = demakein.design.wavelength('C4') * 0.25
    
    fingerings = [
        ('C4',  [1,1,1,1,1,1,1]),
        ('D4',  [0,1,1,1,1,1,1]),
        ('E4',  [0,0,1,1,1,1,1]),
        ('F4',  [0,0,0,1,1,1,1]),
        ('G4',  [0,0,0,0,1,1,1]),
        ('A4',  [0,0,0,0,0,1,1]),
        ('B4',  [0,0,0,0,0,0,1]),
        ('C5',  [0,0,0,0,0,1,0]),
        ]    
    
if __name__ == '__main__': 
    nesoni.run_tool(Reedpipe)

