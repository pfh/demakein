"""

Note:

The "reed" has some virtual length.

Drinking straw needs to be 0.85 of simulated length.

"""

import copy

import demakein, nesoni

class Reedpipe(demakein.design.Instrument_designer):
    def patch_instrument(self, inst):
        inst = copy.copy(inst)
        inst.length /= 0.85
        return inst


class Diatonic(Reedpipe):
    closed_top = True

    inner_diameters = [ 6.0, 6.0 ]
    outer_diameters = [ 6.0, 6.0 ]
    
    min_hole_diameters = [ 4.0 ]*7
    max_hole_diameters = [ 4.0 ]*7
    
    initial_length = demakein.design.wavelength('C4') * 0.25 * 0.85
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

    
class Pentatonic(Reedpipe):
    closed_top = True

    inner_diameters = [ 6.0, 6.0 ]
    outer_diameters = [ 6.0, 6.0 ]
    
    min_hole_diameters = [ 4.0 ]*5
    max_hole_diameters = [ 4.0 ]*5
    
    initial_length = demakein.design.wavelength('C4') * 0.25 * 0.85
    fingerings = [
        ('C4',  [1,1,1,1,1]),
        ('D4',  [0,1,1,1,1]),
        ('E4',  [0,0,1,1,1]),
        ('G4',  [0,0,0,1,1]),
        ('A4',  [0,0,0,0,1]),
        ('C5',  [0,0,0,0,0]),
    ]    
    

if __name__ == '__main__': 
    nesoni.run_toolbox([ Diatonic, Pentatonic ])

