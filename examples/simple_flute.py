"""

A basic flute or ney.

The embouchure hole is not modelled.
To use the design produced:
- make a flute without finger holes, just embouchure hole and end stopper.
- trim so that bottom note is in tune.
- drill finger holes.

The flute is a simple cylinder,
so the tuning is not perfect over the two registers
unless the finger holes are very large.

"""

import demakein, nesoni

class Flute(demakein.design.Instrument_designer):
    closed_top = False

    inner_diameters = [ 10.0, 10.0 ]
    outer_diameters = [ 14.0, 14.0 ]
    
    min_hole_diameters = [ 3.0 ]*6
    max_hole_diameters = [ 8.0 ]*6
    
    #min_hole_spacing = [ 15.0 ]*5
    #and/or
    balance = [ 0.05, None, None, 0.05 ]
    
    initial_length = demakein.design.wavelength('D5') * 0.5
    
    fingerings = [
        ('D5',  [1,1,1,1,1,1]),
        ('E5',  [0,1,1,1,1,1]),
        ('F#5', [0,0,1,1,1,1]),
        ('G5',  [0,0,0,1,1,1]),
        ('A5',  [0,0,0,0,1,1]),
        ('B5',  [0,0,0,0,0,1]),
        ('C#6', [0,0,0,0,0,0]),
        ('D6',  [1,1,1,1,1,1]),
        ('E6',  [0,1,1,1,1,1]),
        ('F#6', [0,0,1,1,1,1]),
        ('G6',  [0,0,0,1,1,1]),
        ('A6',  [0,0,0,0,1,1]),
        ('B6',  [0,0,0,0,0,1]),
        ('C#7', [0,0,0,0,0,0]),
        ('D8',  [1,1,1,1,1,1]),
        ]    

if __name__ == '__main__': 
    nesoni.run_tool(Flute)

