
import demakein, nesoni

class Design_simple_shawm(demakein.design.Instrument_designer):
    closed_top = True

    # Bore will be 35mm at end, 4mm at top
    inner_diameters = [ 
        35.0, 
        (35.0, 30.0), 
        (30.0, 25.0),
        (25.0, 20.0),
        (20.0, 15.0),
        (15.0, 10.0),
        (10.0, 7.0),
        (7.0, 4.0),
        4.0 
        ]

    outer_diameters = [ 50.0, 15.0 ]
    
    # Limits on finger holes sizes
    min_hole_diameters = [ 2.0 ]*6
    max_hole_diameters = [ 15.0 ]*6
    
    # Limit how close successive holes can be to each other
    #min_hole_spacing = [ 5,5,5,20,20 ]
    # see also max_hole_spacing
    #          balance
        
    # Very simple fingering system
    initial_length = demakein.design.wavelength('D4') * 0.4
    fingerings = [
        ('D4',  [1,1,1,1,1,1]),
        ('E4',  [0,1,1,1,1,1]),
        ('F#4', [0,0,1,1,1,1]),
        ('G4',  [0,0,0,1,1,1]),
        ('A4',  [0,0,0,0,1,1]),
        ('B4',  [0,0,0,0,0,1]),
        ('C#5', [0,0,0,0,0,0]),
        ('D5',  [1,1,1,1,1,1]),
        ('E5',  [0,1,1,1,1,1]),
        ('F#5', [0,0,1,1,1,1]),
        ('G5',  [0,0,0,1,1,1]),
        ('A5',  [0,0,0,0,1,1]),
        ('B5',  [0,0,0,0,0,1]),
        ('C#6', [0,0,0,0,0,0]),
    ]    

if __name__ == '__main__':
    nesoni.run_tool(Design_simple_shawm)
    
    # or
    #nesoni.run_toolbox([ 
    #    Design_simple_shawm,
    #    #...
    #    ])