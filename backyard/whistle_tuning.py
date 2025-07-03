"""

pypy demakein-script design-folk-whistle: --transpose 12 /tmp/fwhistle  --tweak-gapextra 0.0

"""

import sys, copy, os

sys.path.insert(0, os.path.normpath(os.path.join(__file__,'..','..')))

from demakein import design, design_whistle

notes =    [ 'D5',  'E5',  'F#5', 'G5',  'A5',  'B5',  'C6',  'C#6',  'D6',   'E6',   'F#6',  'G6',   'A6',   'B6']

#Small hole
#obtained = [ 555.0, 623.0, 694.0, 734.0, 824.0, 930.0, 995.0, 1045.0, 1136.0, 1275.0, 1433.0, 1511.0, 1696.0, 1899.0]

obtained = [ 594.0, 682.0, 774.0, 821.5, 928.0, 1045.0, 1109.0, 1169.0, 1224.0, 1366.0, 1533.0, 1632.0, 1830.0, 2060.0 ]

designer = design.load('/tmp/bigwhistle') #Whistle with embextra 0

designer.tweak_gapextra = 0.0
base = designer.patch_instrument(designer.instrument)
designer.tweak_gapextra = 0.00 #0.37
#designer.tweak_gapheight = 
mod = designer.patch_instrument(designer.instrument)

base.prepare()
mod.prepare()

#unpatched = designer.instrument
#patched = designer.patch_instrument(unpatched)
#unpatched.prepare()
#patched.prepare()
#
#edesigner = design.load('/tmp/fwhistle2') #Whistle with candidate embextra
#eunpatched = edesigner.instrument
#epatched = edesigner.patch_instrument(eunpatched)
#eunpatched.prepare()
#epatched.prepare()

e = 0.0
for note, obtained in zip(notes, obtained):
    for note2, fingers in designer.fingerings:
        if abs(design.wavelength(note2,designer.transpose) - design.wavelength(note)) < 1e-3: break
    else:
        assert False, note2
    print(fingers, end=' ')
    w = design.wavelength(note)
    w_real = design.SPEED_OF_SOUND / obtained
    w_base = base.true_wavelength_near(w, fingers, designer.max_grad)[0]
    w_mod = mod.true_wavelength_near(w, fingers, designer.max_grad)[0]
    #print w, w_real, unmod, mod
    print(w_real, w_mod, w_mod/w_real) #w, w_base, w_mod, w_real/w_base, w_base/w_mod, (w_real/w_base) / (w_mod/w_base)
    e += abs(1.0-w_mod/w_real)
print(e)
    
    