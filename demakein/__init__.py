VERSION = '0.17'

from .design_flute import Design_pflute, Design_folk_flute
from .make_flute import Make_flute
from .make_cork import Make_cork

from .design_shawm import Design_reed_drone, Design_reedpipe, Design_shawm, Design_folk_shawm
from .make_shawm import Make_reed_instrument, Make_dock_extender
from .make_mouthpiece import Make_mouthpiece
from .make_bauble import Make_bauble
from .make_windcap import Make_windcap

from .design_whistle import \
    Design_folk_whistle, Design_dorian_whistle, Design_recorder, Design_three_hole_whistle
from .make_whistle import Make_whistle

from .make_panpipe import Make_panpipe

from .make_reed import Make_reed, Make_reed_shaper

from .tune import Tune

from .all import All

def main():
    """ Command line interface. """
    import nesoni    
    nesoni.run_toolbox([
            'Demakein '+VERSION,
            'Flutes',
            Design_pflute, 
            Design_folk_flute, 
            Make_flute,
            Make_cork,
            
            'Whistles',
            Design_folk_whistle,
            Design_dorian_whistle,
            Design_recorder,
            Design_three_hole_whistle,
            Make_whistle,
            
            'Reed instruments',
            Design_reed_drone,
            Design_reedpipe,
            Design_shawm,
            Design_folk_shawm,
            Make_reed_instrument,
            Make_dock_extender,
            Make_mouthpiece,
            Make_windcap,
            Make_bauble,            
            #Make_reed,
            Make_reed_shaper,
            
            'Panpipes',        
            Make_panpipe,
            
            'Utilities',
            Tune,
            
            #'Everything',        
            #All,
            #'"demakein all:" uses the nesoni make system, see flags below.',
        ],
        show_make_flags=False,
        )

