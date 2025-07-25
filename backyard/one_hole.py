#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "polars",
#     "altair[all]",
#     "demakein"
# ]
#
# [tool.uv.sources]
# demakein = { path = ".." }
#
# ///

"""
Some parameter scanning with a simple instrument.
"""


import math, copy

import polars as pl
import altair as alt

from demakein import design, profile

inst = design.Instrument()
inst.length = design.wavelength("C4")
inst.closed_top = False
inst.inner = profile.Profile([0,inst.length], [6,6])
inst.outer = profile.Profile([0,inst.length], [10,10])

inst.inner_hole_positions = [ inst.length * 2/3 ]
inst.hole_lengths = [ 0.0 ]
inst.hole_diameters = [ 0.1 ]

inst.cone_step = 0.125

inst.prepare_phase()

def interpret(w):
    desc = design.describe(w)
    error = design.wavelength(desc) / w
    cents = math.log(error) / math.log(2) * 1200.0
    return f"{desc} {cents} {w}"

print( interpret( inst.length ) )
print( interpret( inst.true_nth_wavelength_near(inst.length * 0.5, [ 1 ], 2 ) ) )
print( interpret( inst.true_nth_wavelength_near(inst.length * 0.5, [ 0 ], 2 ) ) )
print( interpret( inst.true_nth_wavelength_near(inst.length * 0.5, [ 1 ], 3 ) ) )
print( interpret( inst.true_nth_wavelength_near(inst.length * 0.5, [ 0 ], 3 ) ) )


df = [ {"nth":nth, "finger":finger, "diam":diam}
    for diam in [0.1,0.5,1,2,3,4,5,6,12]
    for nth in [2,3,4,5,6]
    for finger in [0,1] ]

for row in df:
    inst2 = copy.copy(inst)
    inst2.hole_diameters = [ row["diam"] ]
    inst2.prepare_phase()
    row["w"] = inst2.true_nth_wavelength_near(inst2.length*0.5, [row["finger"]], row["nth"])
    row["desc"] = interpret(row["w"])

cols = {k: [d[k] for d in df] for k in df[0]}

chart = alt.Chart(pl.DataFrame(cols)).mark_point().encode(x="diam",y="w",color="nth",column="finger")
chart.save("output/chart.html")

print(pl.DataFrame(cols))


# Even simpler would be to look at what a stepped bore does

