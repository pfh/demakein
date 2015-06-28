"""

Units:

distance:  mm
time:      seconds
speed:     mm/s
frequency: Hz

Positions are measured from the end of the instrument,
the mouthpiece is at instrument.length

Fingerholes are enumerated from bottom (end-most) to top.

"""

import math, os, pickle, sys, random, collections

import profile, svg

from nesoni import config

# ===== Utility constants and functions =====

SPEED_OF_SOUND = 346100.0 # mm/sec at 25C
                          #           30C is 349000

semitone_name = [ 'C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B' ] 

semitone = {
   'C'  : 0,
   'D'  : 2,
   'E'  : 4,
   'F'  : 5,
   'G'  : 7,
   'A'  : 9,
   'B'  : 11,
}


def fqc(note):
    if note[-2:].lower() == "hz":
        return float(note[:-2])

    if '*' in note:
        note, mult = note.split('*')
        mult = float(mult)
    else:
        mult = 1.0

    s = semitone[note[0].upper()]
    note = note[1:]
    if note.startswith('b'):
        s -= 1
        note = note[1:]
    if note.startswith('#'):
        s += 1
        note = note[1:]
    
    s += 12 * int(note)
    
    return 440.0 * 2**((s-57)/12.0) * mult


def wavelength(w, transpose=0):
    if isinstance(w, str): 
        w = SPEED_OF_SOUND / fqc(w)
    return w / (2**(transpose/12.0))


def log2(x):
    return math.log(x) / math.log(2.0)


def describe(w):
    f = SPEED_OF_SOUND / w
    
    s = int(round( log2(f/440.0) * 12.0 + 57 ))
    octave = s // 12
    s = s % 12
    
    return semitone_name[s] + str(octave)



# ===== Frequency response of a tree of connected tubes ====

FOUR_PI = 4.0*math.pi

def circle_area(diameter):
    radius = diameter*0.5
    return math.pi * radius * radius



# ================================================
# Unit magnitude complex number to represent phase

def pipe_reply(reply_end, length_on_wavelength):
    angle = FOUR_PI*length_on_wavelength
    return complex(math.cos(angle),math.sin(angle)) * reply_end

def junction2_reply(a0, a1, r1):
    """ Relative phase reply for pipe 0 of two pipe junction
        with pipe cross section areas a0 and a1
        and pipe 1 relative phase reply r1.    
    """
    pjunc = 2.0*a0 / (a0-a1*((r1-1.0)/(r1+1.0)))
    mag1 = abs( pjunc / (r1+1.0) )    
    return pjunc-1.0, mag1

def junction3_reply(a0,a1,a2, r1,r2):
    """ Relative phase reply for pipe 0 of three pipe junction
        with pipe cross section areas a0, a1 and a2
        and relative phase replies r1 and r2.    
    """
    pjunc = 2.0*a0 / (a0-a1*((r1-1.0)/(r1+1.0))-a2*((r2-1.0)/(r2+1.0)))    
    mag1 = abs( pjunc / (r1+1.0) )
    mag2 = abs( pjunc / (r2+1.0) )
    return pjunc-1.0, mag1, mag2

# ===================================
# Phase in [0,1] plus number of nodes

def pipe_reply_phase(phase_end, length_on_wavelength):
    return phase_end + length_on_wavelength * 2.0

def tanner(phase):
    x = phase*math.pi
    return math.tan(x)
    
def untanner(x):
    return math.atan(x)/math.pi

def junction2_reply_phase(a0, a1, p1):
    shift = math.floor(p1+0.5)
    return untanner(a1/a0 * tanner(p1-shift)) + shift

def junction3_reply_phase(a0,a1,a2, p1,p2):
    shift1 = math.floor(p1+0.5)
    shift2 = math.floor(p2+0.5)
    return untanner(a1/a0*tanner(p1-shift1) + a2/a0*tanner(p2-shift2)) + shift1 + shift2




def end_flange_length_correction(outer_diameter, inner_diameter):
    a = inner_diameter / 2.0
    w = (outer_diameter - inner_diameter) / 2.0
    
    return a * (0.821 - 0.13*((0.42+w/a)**-0.54))


def hole_length_correction(hole_diameter, bore_diameter, closed):
    # No inner correction even, for closed holes.
    # Not sure why, but including an inner correction
    # for closed holes is wrong (I've tried this).
    
    # Maybe better to treat as bore deviation?
    
    if closed: 
       return 0.0
    
    # As per p.63-64 of Nederveen
    outer_correction = 0.7
    inner_correction = 1.3 - 0.9 * hole_diameter/bore_diameter
    a = hole_diameter / 2.0
    
    result = a * (inner_correction+outer_correction)

    return result



# ================ Instruments and classes of instruments =================

class Instrument:
    """
        Fill in:
            length - length
            inner  - inner profile, diameters
            outer  - outer profile, diameters
            hole_positions - hole positions on outside
            hole_angles - angle of hole in degrees, up positive, down negative
            inner_hole_positions - hole positions in bore
            hole_lengths - length of hole through instrument wall (perhaps plus an embouchure correction)
            hole_diameters - hole diameters
            closed_top - is the mouthpiece closed (eg reed) or open (eg ney)
            cone_step - inner profile step size for conical segments of inner profile
        
        Then call:
            .prepare()
               - prepare to handle queries
    
            .evaluate(wavelength)
    """
    
    def prepare(self):
        self.stepped_inner = self.inner.as_stepped(self.cone_step)
    
        events = [
            (self.length, 'end', None)
        ]
        
        for i, pos in enumerate(self.stepped_inner.pos):
            if 0.0 < pos < self.length:
                events.append((pos, 'step', i))
        
        for i, pos in enumerate(self.inner_hole_positions):
            events.append((pos,'hole', i))
        
        events.sort(key=lambda item: item[0])
    
        self.actions = [ ]
        
        position = -end_flange_length_correction(self.outer(0.0,True),self.stepped_inner(0.0,True))
        diameter = self.stepped_inner(0.0, True)
        self.initial_emission = [ circle_area(diameter) ]
        for pos, action, index in events:
            length = pos-position
            
            def func(reply_end, wavelength, fingers, emission, length=length):
                return pipe_reply(reply_end, length/wavelength)
            self.actions.append(func)
            
            position = pos
            
            if action == 'step':
                assert diameter == self.stepped_inner.low[index]
                area1 = circle_area(diameter)
                diameter = self.stepped_inner.high[index]
                area = circle_area(diameter)
                
                def func(reply, wavelength, fingers, emission, area=area, area1=area1):
                    new_reply, mag1 = junction2_reply(area, area1, reply)
                    if emission is not None:
                        for i in xrange(len(emission)):
                            emission[i] *= mag1
                    return new_reply
                self.actions.append(func)
                
            elif action == 'hole':
                area = circle_area(diameter)
                hole_diameter = self.hole_diameters[index]
                hole_area = circle_area(hole_diameter)
                
                #true_length = (self.outer(position) - diameter) * 0.5 
                #true_length += self.hole_extra_heights[index]
                #true_length += self.hole_extra_height_by_diameter[index] * hole_diameter                
                true_length = self.hole_lengths[index]
                
                open_length = true_length + hole_length_correction(hole_diameter, diameter, False) 
                closed_length = true_length + hole_length_correction(hole_diameter, diameter, True)

                def func(reply, wavelength, fingers, emission,
                         area=area,hole_area=hole_area,
                         open_length=open_length,closed_length=closed_length,
                         index=index):
                    if fingers[index]:
                        hole_reply = pipe_reply(1.0, closed_length/wavelength)
                    else:
                        hole_reply = pipe_reply(-1.0, open_length/wavelength)
                    new_reply, mag1, mag2 = junction3_reply(area, area, hole_area, reply, hole_reply)
                
                    if emission is not None:
                        for i in xrange(len(emission)):
                            emission[i] *= mag1
                        if not fingers[index]:
                            emission.append(hole_area*mag2)
                
                    return new_reply
                    
                self.actions.append(func)
    
        self.emission_divide = circle_area(diameter)
    
    
    def resonance_score(self, w, fingers, calc_emission=False):
        """ A score -1 <= score <= 1, zero if wavelength w resonantes """
        reply = -1.0 #Open end
        
        if not calc_emission:
            for action in self.actions:
                reply = action(reply, w, fingers, None)
        else:
            emission = list(self.initial_emission)
            for action in self.actions:
                reply = action(reply, w, fingers, emission)
        
            # Scale by top area
            for i in xrange(len(emission)):
                emission[i] /= self.emission_divide
        
        if not self.closed_top: reply *= -1.0
        
        angle = math.atan2(reply.imag, reply.real)
        
        angle1 = angle  %(math.pi*2.0)
        angle2 = angle1 - math.pi*2.0
        
        if angle1 < -angle2:
            result = angle1/math.pi
        else:
            result = angle2/math.pi
        
        if not calc_emission:
            return result
        else:
            return result, emission
    


    # phase version
    # =============
    def prepare_phase(self):
        self.stepped_inner = self.inner.as_stepped(self.cone_step)
    
        events = [
            (self.length, 'end', None)
        ]
        
        for i, pos in enumerate(self.stepped_inner.pos):
            if 0.0 < pos < self.length:
                events.append((pos, 'step', i))
        
        for i, pos in enumerate(self.inner_hole_positions):
            events.append((pos,'hole', i))
        
        events.sort(key=lambda item: item[0])
    
        self.actions_phase = [ ]
        
        position = -end_flange_length_correction(self.outer(0.0,True),self.stepped_inner(0.0,True))
        diameter = self.stepped_inner(0.0, True)
        for pos, action, index in events:
            length = pos-position
            
            def func(phase_end, wavelength, fingers, length=length):
                return pipe_reply_phase(phase_end, length/wavelength)
            self.actions_phase.append(func)
            
            position = pos
            
            if action == 'step':
                assert diameter == self.stepped_inner.low[index]
                area1 = circle_area(diameter)
                diameter = self.stepped_inner.high[index]
                area = circle_area(diameter)
                
                def func(phase, wavelength, fingers, area=area, area1=area1):
                    return junction2_reply_phase(area, area1, phase)
                self.actions_phase.append(func)
                
            elif action == 'hole':
                area = circle_area(diameter)
                hole_diameter = self.hole_diameters[index]
                hole_area = circle_area(hole_diameter)
                
                #true_length = (self.outer(position) - diameter) * 0.5 
                #true_length += self.hole_extra_heights[index]
                #true_length += self.hole_extra_height_by_diameter[index] * hole_diameter                
                true_length = self.hole_lengths[index]
                
                open_length = true_length + hole_length_correction(hole_diameter, diameter, False) 
                closed_length = true_length + hole_length_correction(hole_diameter, diameter, True)

                def func(phase, wavelength, fingers,
                         area=area,hole_area=hole_area,
                         open_length=open_length,closed_length=closed_length,
                         index=index):
                    if fingers[index]:
                        hole_phase = pipe_reply_phase(0.0, closed_length/wavelength)
                    else:
                        hole_phase = pipe_reply_phase(-0.5, open_length/wavelength)
                    return junction3_reply_phase(area, area, hole_area, phase, hole_phase)
                    
                self.actions_phase.append(func)

    def resonance_phase(self, w, fingers):
        """ score % 1 == 0 if wavelength w resonantes """
        phase = 0.5 #Open end
        
        for action in self.actions_phase:
            phase = action(phase, w, fingers)
        
        if not self.closed_top: phase += 0.5
        
        return phase

        
    def true_wavelength_near(self, w, fingers, step_cents = 1.0, step_increase = 1.05, max_steps = 100):
        #def scorer(probe):
        #    return self.resonance_score(probe,fingers)
        def scorer(probe):
            return (self.resonance_phase(probe,fingers)+0.5)%1.0-0.5
        
        step = pow(2.0, step_cents/1200.0)
        
        half_step = math.sqrt(step)
        probes = [ w/half_step, w*half_step ]
        scores = [ scorer(probe) for probe in probes ]
        
        def evaluate(i):
            y1 = scores[i]
            x1 = probes[i]
            y2 = scores[i+1]
            x2 = probes[i+1]
            
            m = (y2-y1)/(x2-x1)
            c = y1-m*x1
            intercept = -c/m
            
            #grad = -m*intercept
            #if grad > max_grad: return None
            
            #assert x1 <= intercept <= x2, '%f %f %f' % (x1,intercept,x2)
            return intercept
        
        for iteration in range(max_steps):
            if scores[-2] >= 0 and scores[-1] < 0:
                return evaluate(len(scores)-2)
            
            probes.insert(0, probes[0]/step)
            scores.insert(0, scorer(probes[0]))
            
            if scores[0] >= 0 and scores[1] < 0:
                return evaluate(0)

            probes.append(probes[-1]*step)
            scores.append(scorer(probes[-1]))
        
            step **= step_increase
        else:
            if abs(scores[-1]) < abs(scores[0]):
                return probes[-1]
            else:
                return probes[0]
        
        # y = mx + c
                
        #step = pow(2.0, max_cents/((n_probes-1)*0.5*1200.0))
        #low = w * pow(step, -(n_probes-1)/2.0)
        #probes = [ low * pow(step,i) for i in range(n_probes) ]
        #
        #scores = [ abs(self.resonance_score(probe, fingers)) for probe in probes ]
        #
        #best = min(range(n_probes), key=lambda i: scores[i])
        #
        #if best == 0 or best == n_probes-1:
        #    return probes[best]
        #    
        #c = scores[best]
        #b = 0.5*(scores[best+1]-scores[best-1])
        #a = scores[best+1]-c-b
        #return low*pow(step, best-b*0.5/a)


    #TODO: Make efficient
    def true_nth_wavelength_near(self, w, fingers, n, step_cents = 1.0, step_increase = 1.5, max_steps = 20):
        def scorer(probe):
            return self.resonance_phase(probe,fingers) - n

        step = pow(2.0, step_cents/1200.0)
        
        half_step = math.sqrt(step)
        probes = [ w/half_step, w*half_step ]
        scores = [ scorer(probe) for probe in probes ]
        
        def evaluate(i):
            y1 = scores[i]
            x1 = probes[i]
            y2 = scores[i+1]
            x2 = probes[i+1]
            
            m = (y2-y1)/(x2-x1)
            c = y1-m*x1
            intercept = -c/m
            return intercept
        
        for iteration in range(max_steps):
            if scores[-2] >= 0 and scores[-1] < 0:
                return evaluate(len(scores)-2)
            
            if scores[0] <= 0:
                probes.insert(0, probes[0]/step)
                scores.insert(0, scorer(probes[0]))
            
            if scores[0] >= 0 and scores[1] < 0:
                return evaluate(0)

            if scores[-1] >= 0:
                probes.append(probes[-1]*step)
                scores.append(scorer(probes[-1]))
        
            step **= step_increase
        else:
            if abs(scores[-1]) < abs(scores[0]):
                return probes[-1]
            else:
                return probes[0]
        


def low_high(vec):
    low = [ ]
    high = [ ]
    for item in vec:
        if isinstance(item, tuple) or isinstance(item, list):
           assert len(item) == 2
           low.append(item[0])
           high.append(item[1])
        else:
           low.append(item)
           high.append(item)
    return low, high

def describe_low_high(item):
    if isinstance(item, tuple) or isinstance(item, list):
       return '%.1f->%.1f' % item
    else:
       return '%.1f' % item


def scaler(value):
    @property
    def func(self):
        scale = self.scale
        return [ item*scale if item is not None else None for item in value ]
    return func


def sqrt_scaler(value):
    @property
    def func(self):
        scale = math.sqrt(self.scale)
        return [ item*scale if item is not None else None for item in value ]
    return func

def power_scaler(power, value):
    @property
    def func(self):
        scale = self.scale ** power
        return [ item*scale if item is not None else None for item in value ]
    return func


@config.Int_flag('transpose', 'Transpose instrument by this many semitones.')
@config.Float_flag('tweak_emission', 
    'Experimental. '
    'Add a term to the optimization '
    'to try to make instrument louder, '
    'possibly sacrificing being-in-tuneness.'
    )
class Instrument_designer(config.Action_with_output_dir):
    instrument_class = Instrument

    cone_step = 0.125  #diameter step size when approximating cones

    closed_top = False

    transpose = 0
    
    tweak_emission = 0.0
    
    initial_length = None
    max_length = None

    fingerings = [ ]
    
    inner_diameters = [ ]             #diameters of inner bore: first is diam at bottom, last is diam at top
    @property
    def inner_angles(self): return [ None ] * len(self.inner_diameters)
    
    outer_add = False
    
    outer_diameters = [ ]
    @property
    def outer_angles(self): return [ None ] * len(self.outer_diameters)
    
    max_hole_diameters = [ ]

    top_clearance_fraction = 0.0
    bottom_clearance_fraction = 0.0

    @property
    def scale(self):
        return 2.0**(-self.transpose/12.0)

    @property
    def n_holes(self):
        return len(self.max_hole_diameters)

    @property
    def min_hole_diameters(self):
        return [ 0.5 ] * self.n_holes
    
    @property
    def min_hole_spacing(self):
        return [ 0.0 ] * (self.n_holes-1)

    @property
    def max_hole_spacing(self):
        return [ self.initial_length ] * (self.n_holes-1)

    @property
    def balance(self):
        return [ None ] * (self.n_holes-2)
    
    # Angle in degrees up (positive) or down (negative) the tube
    @property
    def hole_angles(self):
        return [ 0.0 ] * self.n_holes

    #n-2 initial positions of bore kinks, as fraction of initial length
    @property
    def initial_inner_fractions(self):
        return [ (i+1.0)/(len(self.inner_diameters)-1) for i in xrange(len(self.inner_diameters)-2) ]

    @property
    def min_inner_fraction_sep(self):
        return [ 0.0 ] * (len(self.inner_diameters)-1)

    @property
    def max_inner_fraction_sep(self):
        return [ 1.0 ] * (len(self.inner_diameters)-1)

    @property
    def min_inner_sep(self):
        return [ None ] * (len(self.inner_diameters)-1)

    @property
    def max_inner_sep(self):
        return [ None ] * (len(self.inner_diameters)-1)



    @property
    def initial_outer_fractions(self):
        return [ (i+1.0)/(len(self.outer_diameters)-1) for i in xrange(len(self.outer_diameters)-2) ]

    @property
    def min_outer_fraction_sep(self):
        return [ 0.0 ] * (len(self.outer_diameters)-1)

    @property
    def max_outer_fraction_sep(self):
        return [ 1.0 ] * (len(self.outer_diameters)-1)

    @property
    def initial_hole_fractions(self):
        return [ (i+3.0)/(self.n_holes+2) * 0.5 for i in xrange(self.n_holes) ]

    @property
    def initial_hole_diameter_fractions(self):
        return [ 0.75 ] * self.n_holes

    #@property
    #def hole_extra_height_by_diameter(self):
    #    return [ 0.0 ] * self.n_holes


    #state_vars = [
    #    'length',
    #    'hole_fractions',
    #    'outer_fractions',
    #    'inner_fractions',
    #    'inner_diameters',
    #    'outer_diameters',
    #    ]
    #...
    #

    @property
    def initial_state_vec(self):
        assert len(self.initial_hole_fractions) == self.n_holes, 'initial_hole_fractions has wrong length'
        assert len(self.initial_hole_diameter_fractions) == self.n_holes, 'initial_hole_diameter_fractions has wrong length'
        assert len(self.initial_inner_fractions) == len(self.inner_diameters)-2, 'initial_inner_fractions has wrong length'
        assert len(self.initial_outer_fractions) == len(self.outer_diameters)-2, 'initial_outer_fractions has wrong length'
        return (
            [ 1.0 ] +
            self.initial_hole_fractions + 
            [ item*item for item in self.initial_hole_diameter_fractions ] +
            self.initial_inner_fractions +
            self.initial_outer_fractions
        )


    def unpack(self, state_vec):
        inner_low, inner_high = low_high(self.inner_diameters)
        outer_low, outer_high = low_high(self.outer_diameters)
        inner_angle_low, inner_angle_high = low_high(self.inner_angles)
        outer_angle_low, outer_angle_high = low_high(self.outer_angles)
    
        inst = self.instrument_class()
        
        scale = self.scale
        
        p = 0
        inst.length = state_vec[0] * self.initial_length * scale
        p += 1        
        inst.hole_positions = [ item*inst.length
                                for item in state_vec[p:p+self.n_holes] ]
        p += self.n_holes
        signed_sqrt = lambda x: math.sqrt(abs(x))*(1 if x >= 0 else -1)
        inst.hole_diameters = [ self.min_hole_diameters[i]+signed_sqrt(item)*(self.max_hole_diameters[i]-self.min_hole_diameters[i])
                                for i, item in enumerate(state_vec[p:p+self.n_holes]) ]
        p += self.n_holes
        
        inner_kinks = [ item*inst.length 
                        for item in state_vec[p:p+len(self.inner_diameters)-2] ]
        p += len(self.inner_diameters)-2
        outer_kinks = [ item*inst.length
                        for item in state_vec[p:p+len(self.outer_diameters)-2] ]
        p += len(self.outer_diameters)-2
        assert p == len(state_vec)
        
        inst.inner = profile.curved_profile(
            [0.0]+inner_kinks+[inst.length],
            inner_low,
            inner_high,
            inner_angle_low,
            inner_angle_high,
        )
        inst.outer = profile.curved_profile(
            [0.0]+outer_kinks+[inst.length],
            outer_low,
            outer_high,
            outer_angle_low,
            outer_angle_high,
        )
        
        if self.outer_add:
            inst.outer = inst.outer + inst.inner

        inst.hole_angles = self.hole_angles        
        inst.inner_hole_positions = [ None ] * self.n_holes
        inst.hole_lengths = [ None ] * self.n_holes
        for i in range(self.n_holes):
            #Note: approximates bore as cylindrical calculating shift, length
            radians = inst.hole_angles[i]*math.pi/180.0
            thickness = (inst.outer(inst.hole_positions[i])-inst.inner(inst.hole_positions[i])) * 0.5
            shift = math.sin(radians) * thickness
            inst.inner_hole_positions[i] = inst.hole_positions[i] + shift
            inst.hole_lengths[i] = (
                math.sqrt(thickness*thickness+shift*shift) 
                #+ self.hole_extra_height_by_diameter[i] * inst.hole_diameters[i]
            )
        
        inst.inner_kinks = inner_kinks
        inst.outer_kinks = outer_kinks
        
        inst.cone_step = self.cone_step
        inst.closed_top = self.closed_top
        return inst

    
    def constraint_score(self, inst):
        """ Return an amount of constraint dissatisfaction """
        scores = [ ]
        
        scores.append(inst.length)
        
        if self.max_length is not None:
            scores.append(self.max_length*self.scale - inst.length)
        
        inners = [0.0]+inst.inner_kinks+[inst.length]
        for i in range(len(inners)-1):
            sep = inners[i+1]-inners[i]
            check = sep - self.min_inner_fraction_sep[i]*inst.length
            scores.append(check)
            check = self.max_inner_fraction_sep[i]*inst.length - sep
            scores.append(check)
            
            if self.min_inner_sep[i] is not None:
                scores.append(sep - self.min_inner_sep[i]*self.scale)
            if self.max_inner_sep[i] is not None:
                scores.append(self.max_inner_sep[i]*self.scale - sep)
        
        outers = [0.0]+inst.outer_kinks+[inst.length]
        for i in range(len(outers)-1):
            sep = outers[i+1]-outers[i]
            check = sep - self.min_outer_fraction_sep[i]*inst.length
            scores.append(check)
            check = self.max_outer_fraction_sep[i]*inst.length - sep
            scores.append(check)
        
        if self.n_holes:
            check = inst.hole_positions[0] - self.bottom_clearance_fraction*inst.length
            scores.append(check)
            
            check = (1.0-self.top_clearance_fraction)*inst.length - inst.hole_positions[-1]
            scores.append(check)
            
            for i, value in enumerate(self.min_hole_spacing):
                if value is None: continue
                check = (inst.hole_positions[i+1]-inst.hole_positions[i]) - value
                scores.append(check)
            
            for i, value in enumerate(self.max_hole_spacing):
                if value is None: continue
                check = value - (inst.hole_positions[i+1]-inst.hole_positions[i])
                scores.append(check)                
            
            for i, value in enumerate(self.min_hole_diameters):
                check = inst.hole_diameters[i] - value
                scores.append(check)
            
            for i, value in enumerate(self.max_hole_diameters):
                if value is None: continue
                check = value - inst.hole_diameters[i]
                scores.append(check)
            
            for i, value in enumerate(self.balance):
                if value is None: continue
                check = value * 0.5*(inst.hole_positions[i+2]-inst.hole_positions[i]) - abs(
                    0.5*inst.hole_positions[i]+0.5*inst.hole_positions[i+2]-inst.hole_positions[i+1]
                )
                scores.append(check)

        negscores = [ -item for item in scores if item < 0.0 ]
        negscore = sum(negscores) if negscores else 0.0
        return negscore

    def patch_instrument(self, inst):
        """ Hook to modify instrument before scoring. """
        return inst
    
    def calc_emission(self, emission, fingers):
        """ Hook for how to calculate emission. 
        
            Lets Flute_designer rate emission relative to embouchure hole.
            """
        return math.sqrt(sum(item*item for item in emission))
    
    def score(self, inst):
        inst = self.patch_instrument(inst)
    
        score = 0.0
        div = 0.0

        emission_score = 0.0
        #emission_score2 = 0.0
        emission_div = 0.0
        
        if self.tweak_emission:
            inst.prepare()
        inst.prepare_phase()
        
        s = 1200.0/math.log(2)
        for item in self.fingerings:
            note = item[0]
            fingers = item[1]
        
            w1 = wavelength(note, self.transpose)
            
            if len(item) < 3:
                w2 = inst.true_wavelength_near(w1, fingers)
            else:
                w2 = inst.true_nth_wavelength_near(w1, fingers, item[2])
            
            diff = abs(math.log(w1)-math.log(w2))*s
                                              
            #weight = w1
            weight = 1.0
            #score += weight * diff**3 / (1.0 + (diff/20.0)**2)
            score += weight * diff**3
            div += weight

            #score += (max(0.0,inst.resonance_score(w2/2.0, fingers)) * 1000.0)**3
            #diff += max(0.0,inst.resonance_score(w2/3.0, fingers)) * 100.0
            #diff += max(0.0,inst.resonance_score(w2/4.0, fingers)) * 100.0
            #if inst.resonance_score(w2/3.0, fingers) < 0.0:
            #    diff += 100.0
            #if inst.resonance_score(w2/4.0, fingers) < 0.0:
            #    diff += 100.0
                        
            if self.tweak_emission:
                emission_weight = 1.0 #w1
                emission_div += emission_weight
                _, emission = inst.resonance_score(w2,fingers,True)
                rms = self.calc_emission(emission, fingers)
                #math.sqrt(sum(item*item for item in emission))
                x = math.log(rms)
                emission_score += emission_weight * x
                #emission_score2 += emission_weight * x * x
                            
            
        result = (score/div)**(1.0/3) 
        if self.tweak_emission:
            x = emission_score / emission_div
            #x2 = emission_score2 / emission_div
            #var = x2-x*x
            result += self.tweak_emission * -x #math.sqrt(var)/x
        return result
        
        
        #return ( (score/scale) ** (1.0/2) )*100.0

    def _constrainer(self, state_vec):
        return self.constraint_score(self.unpack(state_vec))

    def _scorer(self, state_vec):
        return self.score(self.unpack(state_vec))

    #def _opt_score(self, state_vec):
    #    inst = self.unpack(state_vec)
    #    
    #    cs = self.constraint_score(inst)
    #    if cs:
    #        result = (cs, 0.0)
    #    else:
    #        result = (0.0, self.score(inst))
    #    return result

    
    def _draw(self, diagram, state_vec, color='#000000', red_color='#ff0000'):
        instrument = self.unpack( state_vec )
        instrument.prepare()
        
        for i in range(self.n_holes):
            diagram.circle(0.0, -instrument.inner_hole_positions[i], instrument.hole_diameters[i],
                           red_color)
            diagram.circle(0.0, -instrument.hole_positions[i], instrument.hole_diameters[i], color)
        diagram.profile(instrument.outer, color)
        diagram.profile(instrument.stepped_inner, color)
        
        if self.closed_top:
            d = instrument.stepped_inner(instrument.length)
            diagram.line([(-0.5*d,-instrument.length),(0.5*d,-instrument.length)], color)
        
        tick_x = instrument.outer.maximum() * -0.625
        for pos in instrument.inner_kinks:
            diagram.line([(tick_x,-pos),(tick_x-5,-pos)], color)
        for pos in instrument.inner.pos[1:-1]:
            diagram.line([(tick_x-2,-pos),(tick_x-3,-pos)], color)
        for pos in instrument.outer_kinks:
            diagram.line([(tick_x-10,-pos),(tick_x-15,-pos)], color)
        for pos in instrument.outer.pos[1:-1]:
            diagram.line([(tick_x-12,-pos),(tick_x-13,-pos)], color)

    
    def _save(self, state_vec, other_vecs=[]):
        self.state_vec = state_vec
        self.instrument = self.unpack( state_vec )
        
        with open(os.path.join(self.output_dir, 'data.pickle'), 'wb') as f:
            if sys.version_info.major == 3:
                pickle.dump(self, f, fix_imports=True)
            else:
                pickle.dump(self, f)

        patched_instrument = self.patch_instrument(self.instrument)
        patched_instrument.prepare()
        patched_instrument.prepare_phase()
        
      #  #any_extra = any( item != 0.0 for item in self.hole_extra_height_by_diameter )
      #  #if any_extra:
      #  #TODO: implement embextra using patch_instrument
      #  mod_instrument = self.unpack( state_vec )
      #  #mod_instrument.hole_extra_height_by_diameter = [ 0.0 ] * len(self.hole_extra_height_by_diameter)
      #  mod_instrument.hole_lengths = [
      #      (mod_instrument.outer(mod_instrument.hole_positions[i])
      #       - mod_instrument.inner(mod_instrument.hole_positions[i])) * 0.5
      #      for i in range(self.n_holes)
      #  ]
      #  mod_instrument.prepare()
        
        diagram = svg.SVG()
        
        for vec in random.sample(other_vecs, min(20,len(other_vecs))):
            self._draw(diagram, vec, '#aaaaaa', '#ffaaaa')
        
        self._draw(diagram, state_vec)
        
        #for i in range(self.n_holes):
        #    diagram.circle(0.0, -self.instrument.inner_hole_positions[i], self.instrument.hole_diameters[i],
        #                   '#ff0000')
        #    diagram.circle(0.0, -self.instrument.hole_positions[i], self.instrument.hole_diameters[i])
        #diagram.profile(self.instrument.outer)
        #diagram.profile(self.instrument.stepped_inner)
        #
        #if self.closed_top:
        #    d = self.instrument.stepped_inner(self.instrument.length)
        #    diagram.line([(-0.5*d,-self.instrument.length),(0.5*d,-self.instrument.length)])
            
        text_x = diagram.max_x * 1.25
        text_y = 0
        for i in range(self.n_holes):
            this_y = min(text_y, -self.instrument.hole_positions[i])
            text_y = diagram.text(text_x, this_y, '%.1fmm' % self.instrument.hole_diameters[i])
            diagram.text(text_x + 90.0, this_y, 'at %.1fmm' % self.instrument.hole_positions[i])
            
            if i < self.n_holes-1:
                this_y = min(text_y, -0.5*(self.instrument.hole_positions[i]+self.instrument.hole_positions[i+1]))
                #text_y = 
                diagram.text(text_x + 45.0, this_y,
                   '%.1fmm' % (self.instrument.hole_positions[i+1]-self.instrument.hole_positions[i])
                )
        
        diagram.text(text_x + 90.0, min(text_y,-self.instrument.length), '%.1fmm' % self.instrument.length)

        text_x = diagram.max_x
        graph_x = text_x+200
        emit_x = graph_x+220
        text_y = 0
        
        for item in self.fingerings:
            note = item[0]
            fingers = item[1]
        
            w1 = wavelength(note, self.transpose)
            if len(item) < 3:
                w2 = patched_instrument.true_wavelength_near(w1, fingers)
            else:
                w2 = patched_instrument.true_nth_wavelength_near(w1, fingers, item[2])
            cents = int(round( log2(w2/w1) * 1200.0 ))

            n_probes = 301
            max_cents = 2400.0
            width = 200.0
            step = pow(0.5, max_cents/((n_probes-1)*0.5*1200.0))
            low = w1 * pow(step, -(n_probes-1)/2.0)
            probes = [ low * pow(step,i) for i in range(n_probes) ]
            #scores = [ patched_instrument.resonance_score(probe, fingers) for probe in probes ]
            #
            #points = [ (graph_x+i*width/n_probes,text_y-score*7.0)
            #           for i,score in enumerate(scores) ]
            #for i in range(len(probes)-1):
            #    if scores[i] > 0 and scores[i+1] < 0: continue
            #    diagram.line(points[i:i+2], '#000000', 0.2)


            scores = [ patched_instrument.resonance_phase(probe, fingers) for probe in probes ]

            points = [ (graph_x+i*width/n_probes,text_y-(((score+0.5)%1.0)-0.5)*14.0)
                       for i,score in enumerate(scores) ]
            for i in range(len(probes)-1):
                c = math.floor(scores[i]+0.5) 
                if c != math.floor(scores[i+1]+0.5): continue
                r,g,b = [ int((math.cos((c/5.0+offset) * math.pi*2.0)*0.5+0.5) * 200) 
                          for offset in [0.0,1.0/3,2.0/3] ]
                diagram.line(points[i:i+2], '#%02x%02x%02x' % (r,g,b), 0.2)


            diagram.line([(graph_x+width*0.5,text_y+7),(graph_x+width*0.5,text_y-7)], '#0000ff', 0.2)
            diagram.line([(graph_x,text_y),(graph_x+width,text_y)], '#0000ff', 0.2)

            diagram.text(text_x, text_y,
                  '%5s %s %-4d cents' % (describe(w1), '     ' if cents == 0 else ' flat' if cents > 0 else 'sharp', abs(cents))
            )
            
            #_, emission = patched_instrument.resonance_score(w2,fingers,True)
            #diagram.text(emit_x, text_y,
            #     ', '.join('%.2f' % item for item in emission)
            #     )
            
            phase = patched_instrument.resonance_phase(w2,fingers)
            diagram.text(emit_x, text_y, "%f" % phase)
            
            #if any_extra:
            #w3 = mod_instrument.true_wavelength_near(w1, fingers)
            #cents3 = int(round( log2(w3/w1) * 1200.0 ))
            #diagram.text(graph_x + width, text_y,
            #      '%s %-4d cents grad=%.1f diff=%d' % ('     ' if cents3 == 0 else ' flat' if cents3 > 0 else 'sharp', abs(cents3), grad3, cents3-cents)
            #)
            
            
            text_y -= 25
        
        diagram.text(graph_x, text_y - 10,
            'Nearby resonances:',
            color='#000000'
            )
        
        #diagram.text(emit_x, text_y - 20,
        #    'Volume of sound emission from\n'
        #    'instrument end and open holes:',
        #    color='#000000',
        #    )
            
            
        
        text_y -= 50.0 + 10.0 * max(len(self.inner_diameters),len(self.outer_diameters))
        
        diagram.text(graph_x-150.0, text_y, 'Outer diameters:', color='#000000')
        kinks = [0.0]+self.instrument.outer_kinks+[self.instrument.length]
        for i, item in enumerate(self.outer_diameters):
            diagram.text(graph_x-150.0, text_y+10.0+(len(self.outer_diameters)-i)*10.0, 
                describe_low_high(item) + 'mm at %.1fmm' % kinks[i]) 
        
        diagram.text(graph_x, text_y, 'Inner diameters:', color='#000000')
        kinks = [0.0]+self.instrument.inner_kinks+[self.instrument.length]
        for i, item in enumerate(self.inner_diameters):
            diagram.text(graph_x, text_y+10.0+(len(self.inner_diameters)-i)*10.0, 
                describe_low_high(item) + 'mm at %.1fmm' % kinks[i]) 
        
        diagram.save( os.path.join(self.output_dir, 'diagram.svg') )
        
        del self.instrument

    def run(self):
        import optimize

        assert self.initial_length is not None, 'Initial length required'
        assert len(self.min_hole_diameters) == self.n_holes
        assert len(self.max_hole_diameters) == self.n_holes
        assert len(self.hole_angles) == self.n_holes
        assert len(self.inner_diameters) >= 2
        assert len(self.outer_diameters) >= 2

        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        state_vec = self.initial_state_vec
        state_vec = optimize.improve(self.shell_name(), self._constrainer, self._scorer, state_vec, monitor=self._save)
        
        self._save(state_vec)
        
        #print(self._opt_score(state_vec))


def bore_scaler(value, maximum=1e30):
    @property
    def func(self):
        scale = math.sqrt(self.scale) * self.bore_scale
        return [ min(item*scale, maximum) if item is not None else None for item in value ]
    return func

@config.Float_flag('bore_scale',
    'Bore diameter is scaled as the square root of the instrument size times this amount.'
    )
class Instrument_designer_with_bore_scale(Instrument_designer):
    bore_scale = 1.0


def load(output_dir):
    with open(os.path.join(output_dir, 'data.pickle'), 'rb') as f:
        if sys.version_info.major == 3:
            return pickle.load(f, fix_imports=True)
        else:
            return pickle.load(f)




#=======================
# Main

def main(module_path, class_name):
    # Explicitly import module
    # If class defined in __main__ module, pickles won't load
    module = __import__(module_path, globals(), fromlist=True)
    designer = getattr(module, class_name)()    
    
    args = sys.argv[1:]
    
    config.shell_run(designer, args, sys.executable + ' -m ' + module_path)
    


