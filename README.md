
# Demakein

https://www.logarithmic.net/pfh/design

Paul Harrison - paul.francis.harrison@gmail.com


Demakein is a set of Python 3 tools for designing and making woodwind instruments.

This generally consists of two stages:

- The "design" stage is a numerical optimization that chooses the bore shape and the finger hole placement, size, and depth necessary for the instrument to produce the correct notes for a given set of fingerings.

- The "make" stage takes a design and turns it into a 3D object, then then cuts the object into pieces that can be CNC-milled or 3D-printed.

Demakein can either be used via the command "demakein" or as a library in Python. Demakein has been designed to be extensible, and I hope you will find it relatively easy to write code to create your own novel instruments. You can either create subclasses of existing classes in order to tweak a few parameters, or create wholly new classes using existing examples as a template.




## Installing Demakein

You will need Python 3. Ideally install in a virtual environment:

```
pip install demakein
```

Hopefully the necessary dependencies install without problems. Please email me if you run into trouble.

You can then run program by typing:

```
demakein
```

or:

```
python3 -m demakein
```


## Using PyPy

Using PyPy is your Python interpreter will let Demakein run considerably faster.



## Development version

I develop Demakein using "hatch". Install hatch using one of the methods listed [here](https://hatch.pypa.io/latest/install/).

```
git clone https://github.com/pfh/demakein.git
cd demakein

# To enter a virtual environment using pypy
hatch shell pypy

# To enter a virtual environment using your system python
hatch shell

# To build source distribution and wheel
hatch build
# or
python3 -m build
```


## Examples

Create a small flute:

```
demakein design-folk-flute: myflute --transpose 12

demakein make-flute: myflute
```

Files are created in a directory called myflute.

We've just made STL files for 3D printing. How about if we want to CNC-mill the flute?

```
demakein make-flute: myflute --mill yes --open yes --prefix milling
```


## Adding new types of instrument

If you want to create your own custom instruments, you can create subclasses of the instruments provided. Some examples of how to do this can be found in the "examples" directory. Use these as a starting point.

Instrument design tools are subclasses of demakein.design.Instrument_designer. These tools define a set of class attributes that constrain the instrument design, listed below:

```
closed_top 
- bool
  Is the top of the instrument closed? 
  Reeds and brass-style mouthpieces are effectively closed.
  A ney has an open end.
  A flute might be approximated as an open end, or the embouchure
  hole treated as a hole and the end set to closed.
  See examples/simple_reedpipe.py for an example with closed_top=True.
  See examples/simple_flute.py for an example with closed_top=False.

inital_length
- float
  Length of the instrument at the start of the optimization.
  Automatically adjusted based on --transpose parameter.
  Just provide a roughly reasonable value, 
  eg using demakein.design.wavelength function

n_holes
- int
  Number of finger holes.
  
fingerings
- list of tuples (note, [ 0/1,... ])
  Desired fingering patterns to produce each desired note.
  <note> is automatically adjusted by --transpose parameter.
  The list starts from the bottom of the instrument.
  Not all fingering schemes are physically possible,
  this may require some experimentation.

max_hole_diameters
- list of n_holes floats
  Maximum allowed finger hole diameters.

min_hole_diameters
- list of n_holes floats
  Minimum allowed finger hole diameters.

min_hole_spacing
- list of n_holes-1 floats
  Minimum space between finger holes in mm.

top_clearance_fraction
bottom_clearance_fraction
- Minimum distance of top/bottom hole from top/bottom of instrument,
  as a fraction of the instrument length.

balance
- list of n_holes-2 floats or Nones
  Values should be in the range zero to one.
  Smaller values force the spacing between successive holes to be more similar.

hole_angles
- list of n_holes floats
  Vertical angle of each hole.
  Angled holes may allow more comfortable hole spacing.

inner_diameters
- list of floats [advanced: or tuples (low,high)]
  The first element is the bore diameter at the base of the instrument.
  The last element is the bore diameter at the top of the instrument.
  The bore is piecewise linear,
  intervening elements are bore diameters boundaries between pieces (kinks).
  Exact placement is subject to numerical optimization.
  
  Advanced: 
  Instead of a single diameter, you can give a tuple (low,high)
  to create a step in the diameter of the bore.
  See the examples/stepped_shawm.py for an example of this.
  
initial_inner_fractions
- list of len(inner_diameters)-2 floats
  Initial positions of kinks in the bore.

min_inner_fraction_sep
- list of len(inner_diameters)-1 floats
  Minimum size of each linear segment of the bore,
  as a fraction of the overall length.

outer_diameters
initial_outer_fractions
min_outer_fraction_sep
- As for inner_diameters, 
  but defining the shape of the outside of the instrument
  (hence the depth of each finger hole).

outer_add
- bool, default False
  Optionally the outside diameters of the instrument can be defined
  as being in addition to the bore diameters rather than
  independent of them.
  See examples/simple_shawm.py for an example of this.
```



