#!/usr/bin/env python

import demakein, nesoni

class Design_my_whistle(demakein.Design_folk_whistle):
    transpose = 12    
    
    # ... and any other things you want to change ...


if __name__ == '__main__':
    nesoni.run_toolbox(
        [ Design_my_whistle, demakein.Make_whistle ],
        show_make_flags=False)
