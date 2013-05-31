

from nesoni import config

from . import shape, profile, make

@config.help(
'Make a cork.',
"""\
The cork will taper from a diameter of diameter - taper-in to a diamter of diameter + taper-out.
""")
@config.Float_flag('length')
@config.Float_flag('diameter')
@config.Float_flag('taper_in')
@config.Float_flag('taper_out')
class Make_cork(make.Make, make.Miller):
    diameter = 10.0
    length = 10.0
    taper_in = 0.25
    taper_out = 0.125

    def run(self):
        d1 = self.diameter + self.taper_out
        d2 = self.diameter - self.taper_in
        l = self.length        
        cork = shape.extrude_profile(profile.make_profile([(0.0,d1),(l,d2)]))
        
        self.save(cork, 'cork')
        
        mill = self.miller(cork)
        self.save(mill, 'mill-cork')
