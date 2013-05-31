VERSION = '0.10'

from .design_flute import Design_tapered_pflute, Design_straight_pflute, Design_tapered_folk_flute, Design_straight_folk_flute
from .make_flute import Make_flute
from .make_cork import Make_cork

from .design_shawm import Design_shawm, Design_folk_shawm
from .make_shawm import Make_shawm
from .make_mouthpiece import Make_mouthpiece
from .make_bauble import Make_bauble

from .design_whistle import Design_folk_whistle, Design_recorder, Design_three_hole_whistle
from .make_whistle import Make_whistle

from .make_panpipe import Make_panpipe

from .make_reed import Make_reed

from .tune import Tune

from .all import All

def main():
    """ Command line interface. """
    import nesoni    
    nesoni.run_toolbox([
            'Demakein '+VERSION,
            'Flutes',
            Design_tapered_pflute, 
            Design_straight_pflute, 
            Design_tapered_folk_flute, 
            Design_straight_folk_flute,
            Make_flute,
            Make_cork,
            
            'Whistles',
            Design_folk_whistle,
            Design_recorder,
            Design_three_hole_whistle,
            Make_whistle,
            
            'Shawms',
            Design_shawm,
            Design_folk_shawm,
            Make_shawm,
            Make_mouthpiece,
            Make_bauble,
            #Make_reed,
            
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

