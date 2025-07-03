
import sys, os

sys.path.insert(0, os.path.normpath(os.path.join(__file__,'..','..')))

import demakein
from demakein import shape, geom, make, profile

import nesoni

class Tentacle(make.Make):
    def run(self):
        path = geom.path(
            geom.XYZ(0.0,0.0,0.0),
            geom.XYZ(0.0,1.0,0.0),
            geom.XYZ(1.0,0.0,0.0),
            geom.XYZ(0.0,0.0,100.0),
            geom.XYZ(0.0,0.0,1.0),
            geom.XYZ(1.0,0.0,0.0),
            )
        
        #geom.plot(path.position)
        
        print(path.get_length())
        print(path.find(90.0))
        print(path.get_point(90.0))
        
        l = path.get_length()
        
        prof = profile.make_profile([(0.0,20.0),(l,0.0)])
        
        tentacle = shape.path_extrusion(path,shape.circle,prof)
        self.save(tentacle, 'tentacle')
    
if __name__ == '__main__':
    nesoni.run_tool(Tentacle)