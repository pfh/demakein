
import os

import profile, shape

def plan_segments(cuts, length_ratio):
    plans = [ ]
    for i in xrange(1<<len(cuts)):
        values = [ (i>>j)&1 for j in xrange(len(cuts)) ]
        upper = [0.0] + [ cuts[j] for j,k in enumerate(values) if k == 1] + [ 1.0 ]
        #lower = [0.0] + [ cuts[j] for j,k in enumerate(values) if k == 2] + [ 1.0 ]
        
        lower = [0.0] + [ (upper[j]+upper[j+1])*0.5 for j in xrange(len(upper)-1) ] + [1.0]
        j = 0
        while j < len(lower)-2:
            if lower[j+2]-lower[j] <= length_ratio:
                del lower[j+1]
            else:
                j += 1
        
        good = True
        for seg in (upper,lower):
            for j in xrange(len(seg)-1):
                if seg[j+1]-seg[j] > length_ratio:
                    good = False
                    break
            if not good: break
        if not good: continue
        plans.append(( upper, lower ))
    
    assert plans, 'Couldn\'t find a way to segment for milling.'    
    
    def scorer((upper,lower)):
        worst = 1e30
        for a in upper[1:-1]:
            for b in lower[1:-1]:
                worst = min(worst, abs(a-b))
        return len(upper)+len(lower),len(upper),-worst
    
    best = min(plans, key=scorer)
    print 'Segmentation:'
    print ' '.join('%3.2f' % i for i in best[0])
    print ' '.join('%3.2f' % i for i in best[1])
    print
    
    return best
                


class Packable(object):
    def __init__(self, shapes, rotation, dilation, use_upper=True):
        if not rotation:
            self.shapes = shapes
        else:
            self.shapes = [ item.copy() for item in shapes ]
            for item in self.shapes:
                item.rotate(0,0,1, rotation)
        
        extent = self.shapes[0].extent()
        for item in self.shapes:
            item.move(-extent.xmin,-extent.ymin,0)
        self.extent = self.shapes[0].extent()
        
        mask = self.shapes[0].polygon_mask()
        loop = mask.loop(holes=False)
        self.mask = shape.create_polygon_2(loop)
        self.centroid = loop.centroid

        self.dilated_mask = self.mask.offset_curve(dilation, 16)
        self.dilated_mask = shape.create_polygon_2(self.dilated_mask.loop(holes=False))

        self.dilated_extent = self.dilated_mask.extent()
        self.use_upper = use_upper


class Pack(object):
    def __init__(self, xsize, ysize, zsize, masks=[], items=[]):
        self.xsize = xsize
        self.ysize = ysize
        self.zsize = zsize
        self.masks = masks[:]
        self.items = items[:] #(x,y,packable)

    def copy(self):
        return Pack(self.xsize, self.ysize, self.zsize, self.masks, self.items)

    def put(self, x,y,packable):
        self.items.append((x,y,packable))
        shifted = packable.mask.copy()
        shifted.move(x,y)
        self.masks.append(shifted)
    
    def valid(self, x,y,packable):
        if (packable.extent.zmax > self.zsize or 
            x+packable.dilated_extent.xmin < 0.0 or
            y+packable.dilated_extent.ymin < 0.0 or
            x+packable.dilated_extent.xmax > self.xsize or
            y+packable.dilated_extent.ymax > self.ysize):
            return False
        shifted = packable.dilated_mask.copy()
        shifted.move(x,y)
        for mask in self.masks:
            if mask.intersects(shifted):
                return False
        return True

    def render(self, bit_diameter, bit_pad):
        xsize = self.xsize
        ysize = self.ysize
        
        a = bit_pad
        b = bit_pad + self.zsize/10.0
        pad_cone = shape.extrude_profile(profile.Profile([0,self.zsize],[a*2,b*2],[a*2,b*2]), cross_section=lambda d: shape.circle(d,16))
        pad_cylinder = shape.extrude_profile(profile.Profile([0,self.zsize+bit_diameter],[a*2,a*2],[a*2,a*2]), cross_section=lambda d: shape.circle(d,16))
        
        pad = 0.5 + self.zsize/10.0
        
        upper = shape.block(-pad,xsize+pad,-pad,ysize+pad,0,self.zsize)
        
        print 'Cut holes'

        for i,(x,y,packable) in enumerate(self.items):
            if packable.use_upper:
                flat = packable.mask.to_3()
                flat.move(x,y,0)
                minsum = flat.minkowski_sum(pad_cone)
                upper.remove( minsum )

        print 'Put things in them'

        for x,y,packable in self.items:
            if packable.use_upper:
                temp = packable.shapes[0].copy()
                temp.move(x,y,0)
                upper.add(temp)
            
        bol = int(self.xsize / 10.0)
        bol_width = 1.0
            # 0.5 seemed to allow shifting on a sop flute
        bol_height = 1.0 
            # 0.5 was too low, middle piece tore loose in final pass of
            # contour finishing (x-scan of horizontal-like surfaces)
        xmins = [ x for x,y,packable in self.items ]
        xmaxs = [ x+packable.extent.xmax for x,y,packable in self.items ]
        margin = bol_width+bit_diameter+0.25
        
        potential_bols = [ ((i+0.5)*xsize/bol, 0,ysize) for i in xrange(bol) ]
        bols = [ ]
        while potential_bols:
            pos, y_low, y_high = potential_bols.pop()
            for i, (x,y,packable) in enumerate(self.items):
                if pos-margin <= xmins[i] <= pos+margin or \
                   pos-margin <= xmaxs[i] <= pos+margin:
                   low = y-bit_diameter
                   high = y+packable.extent.ymax+bit_diameter
                   if low <= y_low and y_high <= high:
                       break
                   elif y_low < low and high < y_high:
                       potential_bols.append((pos, y_low, low))
                       potential_bols.append((pos, high, y_high))
                       break
                   elif y_low < low < y_high <= high:
                       potential_bols.append((pos, y_low, low))
                       break
                   elif low < y_low < high <= y_high:
                       potential_bols.append((pos, high, y_high))
                       break
            else:
                bols.append((pos,y_low,y_high))
                
        for pos, y_low, y_high in bols:    
            upper.add(shape.block(
                pos-bol_width*0.5, pos+bol_width*0.5,
                y_low, y_high,
                #0,ysize,
                #-bit_diameter*0.6, bol_height,
                0,bol_height,
            ))     
        
        
        print 'Underside'
        
        # Cut the bottom of upper with lower, to depth    bit_diameter
        lower = shape.block(-pad,xsize+pad,-pad,ysize+pad,bit_diameter,self.zsize)
        lower.add(upper)
        
        print 'Remove bores'

        for x,y,packable in self.items:
            temp = packable.shapes[1].copy()
            temp.move(x,y,0)

            flat = packable.mask.to_3()
            flat.move(x,y,0)
            minsum = flat.minkowski_sum(pad_cylinder)
            temp.clip(minsum)

            lower.remove(temp)
        
        lower.rotate(0,1,0, 180)
        
        return lower, upper
    
    def render_print(self):
        result = None
        for x,y,packable in self.items:
            temp = packable.shapes[0].copy()
            temp.move(x,y,0)
            if result is None:
                result = temp
            else:
                result.add(temp)
        return result


def make_segment(instrument, top, low, high, radius, clip=True):
    #if not clip_half:
    #   y1,y2 = -radius,radius
    segment = instrument.copy()
    
    if clip:
        if top:
           y1,y2 = 0,radius
        else:
           y1,y2 = -radius,0
        clipper = shape.block(-radius,radius, y1,y2, low,high)
        segment.clip(clipper)
    #Closed flute is meant to be like this
    #assert abs(segment.size()[2] - (high-low+pad*2)) < 1e-3, 'Need more padding for construction'
    segment.move(0,0,-low)
    if top:
       segment.rotate(0,0,1, 180)

    segment.rotate(1,0,0,-90)
    segment.rotate(0,0,1,90)
    segment.move(high-low,0,0)
    return segment


def make_segments(instrument, length, radius, top_fractions, bottom_fractions, clip=True):
    parts = [ ]
    z = [ item*length for item in top_fractions ]
    for i in range(len(top_fractions)-1):
        parts.append(make_segment(instrument, True, 
                     z[i],z[i+1], 
                     radius, clip))

    z = [ item*length for item in bottom_fractions ]
    for i in range(len(bottom_fractions)-1):    
        parts.append(make_segment(instrument, False, 
                     z[i],z[i+1], 
                     radius, clip))

    return parts


def deconstruct(outer, bore, top_fractions, bottom_fractions, 
                bit_diameter, dilation, block_zsize):
    """ Object must be large enough to include end padding """
    xsize,ysize,zsize = outer.size()
    radius = max(xsize,ysize)*2
    
    length = zsize
    
    outers = make_segments(outer, length, radius, top_fractions, bottom_fractions)
    bores  = make_segments(bore, length, radius, top_fractions, bottom_fractions, False)

    result = [ ]
    for outer, bore in zip(outers, bores):
        extent = outer.extent()
        
        b = bit_diameter
        clipper = shape.block(extent.xmin-b,extent.xmax+b,
                              extent.ymin-b,extent.ymax+b,
                              extent.zmin,extent.zmax+b)
        bore.clip(clipper)
        
        n = 1
        while extent.zmax > block_zsize*n:
            n += 1
        #thickness = extent.zmax/n
        thickness = block_zsize
        
        block = shape.block(extent.xmin-1,extent.xmax+1,extent.ymin-1,extent.ymax+1,0,thickness)
        for i in xrange(n):
            temp_outer = outer.copy()
            temp_bore = bore.copy()
            temp_outer.move(0,0,-i*thickness)
            temp_bore.move(0,0,-i*thickness)
            temp_outer.clip(block)
            #temp_bore.clip(block)
            result.append([
                Packable([temp_outer,temp_bore], 0, dilation),
                Packable([temp_outer,temp_bore], 180, dilation),
                ])
    return result

    #return [ [ Packable([outer, bore], 0, dilation),
    #            Packable([outer, bore], 180, dilation) ]
    #          for outer, bore in zip(outers, bores) ]


def mill_template(xsize, ysize, zsize, dilation):
    template = Pack(xsize, ysize, zsize)
    
    peg_diameter = 6.0
    block_radius = 4.0
    hole = shape.prism(min(zsize,peg_diameter*1.5), peg_diameter)   # *3 is too deep
    hole_block = shape.block(-block_radius,block_radius,-block_radius,block_radius,0,zsize)
    hole_packable = Packable([hole_block,hole], 0, 0.0, use_upper=False)
    
    shift = 4
    template.put(shift, block_radius,hole_packable)
    template.put(xsize-block_radius*2-shift, block_radius,hole_packable)

    #template.put(0,ysize-block_radius*3,hole_packable)
    #template.put(xsize-block_radius*2,ysize-block_radius*3,hole_packable)
    
    return template

#def mill_squish(pack):
#    x1, y, hole1 = pack.items.pop(2)
#    x2, y, hole2 = pack.items.pop(2)
#    del pack.masks[2:4]
#    y_new = y
#    step = 1.0
#        
#    y_min = max( item[1]+item[2].extent.ymax for item in pack.items )
#    
#    while y_new-step >= y_min and pack.valid(x1,y_new-step,hole1) and pack.valid(x2,y_new-step,hole2):
#        y_new -= step
#        
#    pack.put(x1,y_new,hole1)
#    pack.put(x2,y_new,hole2)
#    pack.ysize -= y-y_new


def pack(template, packables, aspect_goal=1.0):    
    packs = [ template.copy() ]
    pack = packs[-1]
    
    step = 2.0
    step_back = 0.1

    points = [ ]
    for y in xrange(int(template.ysize/step)):
        for x in xrange(int(template.xsize/step)):
            points.append((x*step,y*step))
    
    todo = list(packables)
    while todo:
        try:
            queue = [
                (i,j,x,y)
                for x,y in points
                for i in xrange(len(todo))
                for j in xrange(len(todo[i]))
            ]
        
            #for i in range(len(todo)):
            #    for x,y in points:
            
            def sorter(item):
                i,j,x,y = item
                xm = todo[i][j].extent.xmax
                ym = todo[i][j].extent.ymax
                xc, yc = todo[i][j].centroid
                return (((aspect_goal*(x+xc))**2+(y+yc)**2) - ((aspect_goal*xm)**2+(ym)**2), y, x)
                #return (max(aspect_goal*(x+xc),(y+yc)) -max(aspect_goal*xc,yc), y, x)
                #return (
                #    y > 0,
                #    -todo[i][0].extent.xmax,
                #    y,
                #    x,
                #)
            queue.sort(key=sorter)
            
            for i,j,x,y in queue:
                if pack.valid(x,y,todo[i][j]):
                    raise StopIteration()

            assert len(pack.items) > len(template.items), 'This is never going to work'
            pack = template.copy()
            packs.append(pack)
            
        except StopIteration:
            while True:
                if pack.valid(x-step_back,y,todo[i][j]):
                    x -= step_back
                elif pack.valid(x,y-step_back,todo[i][j]):
                    y -= step_back
                else:
                    break
            
            print len(todo),'put',len(packs),x,y
            
            pack.put(x,y,todo[i][j])
            del todo[i]

    return packs


def save_packs(packs, save, bit_diameter, pad):
    shapes = [ ]
    for i, item in enumerate(packs):
        lower, upper = item.render(bit_diameter, pad)
        shapes.extend([lower,upper])
        save(lower, 'lower-%d-of-%d' % (i+1,len(packs)))
        save(upper, 'upper-%d-of-%d' % (i+1,len(packs)))

    return shapes


def cut_and_pack(outer, bore, top_fractions, bottom_fractions, xsize, ysize, zsize, bit_diameter, save, extra_packables=[]):
    pad = bit_diameter*1.2
    dilation = pad
    
    packables = deconstruct(outer, bore, top_fractions, bottom_fractions, bit_diameter, dilation, zsize)
    packables.extend(extra_packables)

    for item in packables:
        print '%.1fmm x %.1fmm x %.1fmm' % (item[0].extent.xmax,item[0].extent.ymax,item[0].extent.zmax)

    print 'Packing'

    template = mill_template(xsize + pad*2, ysize + pad*2, zsize, dilation)
    packs = pack(template, packables, 0.5*float(ysize)/xsize)
    #for item in packs:
    #    mill_squish(item)
    
    print 'Rendering'
    
    return save_packs(packs, save, bit_diameter, pad)



