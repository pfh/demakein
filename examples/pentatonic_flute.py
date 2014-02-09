"""

This example demonstrates subclassing of Design_flute.

The resultant design can be used with Make_flute.

Note that Make_flute must be executed using this script,
so that it can unpickle the flute design.


Small warning:
The class hierarchy of instruments may change in future,
meaning you might need to inherit from a class with a slightly different name.

"""

import demakein, nesoni
from demakein import design, design_flute

class Design_pentatonic_flute(design_flute.Tapered_flute):
    n_holes = 5 # including embouchure hole
    
    # The fingerings need to include the open embouchure hole.
    fingerings = [
        ('D4', [1,1,1,1, 0]),
        ('E4', [0,1,1,1, 0]),
        ('G4', [0,0,1,1, 0]),
        ('A4', [0,0,0,1, 0]),
        ('B4', [0,0,0,0, 0]),
        ('D5', [1,1,1,1, 0]),
        ('E5', [0,1,1,1, 0]),
        ('G5', [0,0,1,1, 0]),
        ('A5', [0,0,0,1, 0]),
        ('B5', [0,0,0,0, 0]),
        ]

    initial_length = design.wavelength('D4') * 0.5

    hole_horiz_angles = [ 0.0, 5.0, 0.0, 0.0,  0.0 ]    


if __name__ == '__main__':
    nesoni.run_toolbox(
        [ Design_pentatonic_flute, demakein.Make_flute ],
        show_make_flags=False)