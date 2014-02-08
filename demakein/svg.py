    
PREAMBLE = """\
<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" 
"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">

<svg 
    width="%(width)fmm" 
    height="%(height)fmm" 
    viewbox="0 0 %(width)fmm %(height)fmm" 
    version="1.1"
    xmlns="http://www.w3.org/2000/svg">
<g transform="scale(%(scale)f,%(scale)f) translate(%(trans_x)f,%(trans_y)f)">
<rect x="%(neg_trans_x)f" y="%(neg_trans_y)f" width="%(width)f" height="%(height)f" style="fill:#ffffff"/>
"""

POSTAMBLE = """\
</g></svg>
"""

class SVG:
    def __init__(self):
        self.min_x = None
        self.max_x = None
        self.min_y = None
        self.max_y = None
        self.commands = [ ]
    
    def save(self, filename):
        # Assume 90dpi (inkscape default
        scale = 90 / 25.4
        pad = max(self.max_x-self.min_x,self.max_y-self.min_y) * 0.1
        width = (self.max_x-self.min_x+pad*2)
        height = (self.max_y-self.min_y+pad*2)
        trans_x = -self.min_x+pad
        trans_y = -self.min_y+pad        
        neg_trans_x = -trans_x
        neg_trans_y = -trans_y
        
        with open(filename, 'w') as f:
            f.write(PREAMBLE % locals())
            for item in self.commands:
                f.write(item + '\n')
            f.write(POSTAMBLE)
    
    def require(self, x,y):
        if self.min_x is None:
            self.min_x = self.max_x = x
            self.min_y = self.max_y = y
        else:
            self.min_x = min(self.min_x,x)
            self.max_x = max(self.max_x,x)
            self.min_y = min(self.min_y,y)
            self.max_y = max(self.max_y,y)
   
    def circle(self, x,y,diameter, stroke='#000000'):
        radius = diameter * 0.5
        self.require(x-radius,y-radius)
        self.require(x+radius,y+radius)
        self.commands.append(
            '<circle cx="%(x)f" cy="%(y)f" r="%(radius)f" style="fill:none;stroke:%(stroke)s;stroke-width:0.25mm"/>' % locals()
        )

    def line(self, points, color='#000000', width=0.25):
        for x,y in points: self.require(x,y)
        self.commands.append(
            '<polyline points="%s" style="fill:none;stroke:%s;stroke-width:%fmm" />' % (
            ' '.join( '%f,%f'%item for item in points ),
                color,
                width
            )
        )

    def polygon(self, points, color='#000000', width=0.25):
        for x,y in points: self.require(x,y)
        self.commands.append(
            '<polygon points="%s" style="fill:none;stroke:%s;stroke-width:%fmm" />' % (
            ' '.join( '%f,%f'%item for item in points ),
                color,
                width
            )
        )
    
    def profile(self, profile, color='#000000'):
        points = [ ]
        for i, pos in enumerate(profile.pos):
            if i:
                points.append( (profile.low[i], pos) )
            if not i or (profile.low[i] != profile.high[i] and i < len(profile.pos)-1):
                points.append( (profile.high[i], pos) )
        self.line([ ( 0.5*x,-y) for x,y in points ], color)
        self.line([ (-0.5*x,-y) for x,y in points ], color)

    def text(self, x,y, text, color='#666666'):
        font_height = 8
        yy = y + font_height * 0.5
        self.require(x,yy-font_height)
        self.require(x+len(text)*font_height*0.8,yy)
        self.commands.append(
            '<text x="%(x)f" y="%(yy)f" fill="%(color)s" font-size="10" font-family="monospace" xml:space="preserve">%(text)s</text>' % locals()
        )
        return y-font_height

