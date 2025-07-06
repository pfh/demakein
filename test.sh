#!/bin/sh

set -xeu

# Test demakein on the command line

mkdir -p output

demakein make-cork: output/cork

DEMAKEIN_DRAFT=1 demakein make-cork: output/cork-draft

demakein make-panpipe: output/panpipes


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

