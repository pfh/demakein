
import nesoni
from demakein import make

from design_horn import Design_horn

class Make_horn(make.Make_millable_instrument):
    def run(self):
        spec = self.working.spec
        
        self.make_instrument(
            inner_profile=spec.inner,
            outer_profile=spec.outer,
            hole_positions=[],
            hole_diameters=[],
            hole_vert_angles=[],
            hole_horiz_angles=[],
            xpad=[],
            ypad=[],
            with_fingerpad=[]
            )
        
        self.make_parts(up=True, flip_top=True)
        #l = spec.length
        #self.segment([l*0.333,l*0.666], spec.length, up=True)

if __name__ == '__main__':
    nesoni.run_tool(Make_horn)