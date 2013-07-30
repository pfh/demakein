

from nesoni import config

from . import make, shape, profile

@config.help('Make a windcap for a reed instrument.')
@config.Float_flag('dock_diameter',
    'Diameter windcap should fit on top of.'
    )
@config.Float_flag('dock_length',
    'Length of socket.'
    )
class Make_windcap(make.Make):
    dock_diameter = 10.0
    dock_length = 15.0
    
    def run(self):
        wall = 2.0
        
        scale = self.dock_diameter
        
        z_dock_low   = 0.0
        z_dock_high  = self.dock_length
        z_top_low    = z_dock_high + scale * 2.5
        z_top_high   = z_top_low + wall
        z_pinch = z_top_low - scale*0.5
        z_mouth_high = z_top_high + scale * 0.75
        
        d_dock = self.dock_diameter
        d_inner = d_dock - wall
        d_outer = d_dock + wall
        d_dock_outer = d_outer + wall
        d_mouth_inner = wall
        d_mouth_outer = wall + wall*1.5
        
        outer_profile = profile.make_profile([
            (z_dock_low, d_dock_outer),
            (z_top_high-wall*0.5, d_outer),
            (z_top_high, d_outer-wall, d_mouth_outer+wall),
            (z_top_high+wall*0.5, d_mouth_outer),
            (z_mouth_high, d_mouth_outer),
            ])
        
        inner_profile = profile.make_profile([
            (z_dock_low, d_dock),
            (z_dock_high, d_dock, d_inner),
            (z_pinch, d_inner),
            (z_top_low, d_mouth_inner),
            (z_mouth_high, d_mouth_inner),
            ])
        
        stretch = (d_outer-d_mouth_outer)*0.5
        inner_stretch = profile.make_profile([
            (z_pinch, 0.0),
            (z_top_low, stretch)
            ])
        outer_stretch = profile.make_profile([
            (z_top_high, 0.0, stretch)
            ])
        
        cross_section = lambda d,s: shape.rounded_rectangle(-(d+s)*0.5,(d+s)*0.5,-d*0.5,d*0.5,d)
        
        outside = shape.extrude_profile(outer_profile, outer_stretch, cross_section=cross_section)
        inside = shape.extrude_profile(inner_profile, inner_stretch, cross_section=cross_section)
        
        thing = outside.copy()
        thing.remove(inside)
        self.save(thing, 'windcap')
        
        
        