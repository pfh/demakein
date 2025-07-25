#!/bin/sh

# Test demakein on the command line

## To clean-up first:
#
# rm -rf output
#

set -xeu

mkdir -p output

demakein make-cork: output/cork

DEMAKEIN_DRAFT=1 demakein make-cork: output/cork-draft

demakein make-panpipe: output/panpipes

demakein make-bauble: output/bauble


# Test example scripts


python examples/simple_flute.py output/simple-flute

python examples/simple_reedpipe.py output/simple-reedpipe

python examples/simple_shawm.py output/simple-shawm

python examples/stepped_shawm.py output/stepped-shawm

python examples/drinking_straw.py pentatonic: output/drinking-straw-pentatonic
python examples/drinking_straw.py diatonic: output/drinking-straw-diatatonic

python examples/mywhistle.py design-my-whistle: output/mywhistle
python examples/mywhistle.py make-whistle: output/mywhistle

python examples/pentatonic_flute.py design-pentatonic-flute: output/pentatonic-flute
python examples/pentatonic_flute.py make-flute: output/pentatonic-flute


# Test tools

demakein design-folk-flute: output/folk-flute
demakein make-flute: output/folk-flute
demakein make-flute: output/folk-flute --mill yes

demakein design-pflute: output/pflute
demakein make-flute: output/pflute
demakein make-flute: output/pflute --mill yes

demakein design-folk-whistle: output/folk-whistle
demakein make-whistle: output/folk-whistle
demakein make-whistle: output/folk-whistle --mill yes

demakein design-dorian-whistle: output/dorian-whistle
demakein make-whistle: output/dorian-whistle
demakein make-whistle: output/dorian-whistle --mill yes

demakein design-recorder: output/recorder
demakein make-whistle: output/recorder
demakein make-whistle: output/recorder --mill yes

demakein design-three-hole-whistle: output/three-hole-whistle
demakein make-whistle: output/three-hole-whistle
demakein make-whistle: output/three-hole-whistle --mill yes


# Currently broken
#demakein design-reedpipe: output/reedpipe
#demakein make-reed-instrument: output/reedpipe
#demakein make-reed-instrument: output/reedpipe --mill yes

demakein design-shawm: output/shawm
demakein make-reed-instrument: output/shawm
demakein make-reed-instrument: output/shawm --mill yes

demakein design-folk-shawm: output/folk-shawm
demakein make-reed-instrument: output/folk-shawm
demakein make-reed-instrument: output/folk-shawm --mill yes

demakein design-reed-drone: output/drone
demakein make-reed-instrument: output/drone

demakein make-dock-extender: output/dock-extender

demakein make-mouthpiece: output/mouthpiece

# Currently broken. Not sure what this was for.
#demakein make-reed-shaper: output/reed-shaper


# Omnibus collection

demakein all: output/all
