
import math, copy

from . import config, design, optimize


class Working(object): pass

class Observation(object): pass

class Getsetter(object):
    def set_designer(self, designer, value):
        return designer
    def set_inst(self, inst, value):
        return inst

class Flag_getsetter(Getsetter):
    def __init__(self, name):
        self.name = name
    def get(self, designer, inst):
        return getattr(designer,self.name)
    def set_designer(self, designer, value):
        return designer(**{ self.name: value })

class Array_getsetter(Getsetter):
    def __init__(self, name, index):
        self.name = name
        self.index = index
    def get(self, designer, inst):
        return getattr(inst,self.name)[self.index]
    def set_inst(self, inst, value):
        inst = copy.deepcopy(inst)
        getattr(inst,self.name)[self.index] = value
        return inst


@config.help(
    'Modelling the mouthpiece is more difficult than modelling the body of an '
    'instrument. Some parameters are most easily determined empirically.',
    'This tool tries to explain observed frequencies obtained from an instrument '
    'by tweaking parameters to do with the mouthpiece. '
    'Resultant parameters should then result in a correctly tuned instrument '
    'when the design tool is run again.',
    )
@config.Positional(
    'param',
    'Comma separated list of parameters to tweak.'
    )
@config.Main_section(
    'observations',
    'Comma separated lists of frequency followed by '
    'whether each finger hole is open (0) or closed (1) '
    '(from bottom to top).'
    )
class Tune(config.Action_with_working_dir):
    param = ""
    observations = [ ]
    
    def _constraint_score(self, state):
        #All positive
        return sum( max(-item,0.0) for item in state )
    
    def _current_param(self):
        result = { }
        for key in list(self.working.fixed_param) + self.working.opt_param:
            result[key] = self.working.getsetters[key].get(self.working.designer,self.working.initial_inst)
        return result
    
    def _combined_param(self, state):
        result = self.working.fixed_param.copy()
        for key, value in zip(self.working.opt_param,state):
            result[key] = value
        return result
    
    def _get_designer_inst(self, param):
        designer = self.working.designer
        for name in param:
            designer = self.working.getsetters[name].set_designer(designer, param[name])
        inst = designer.unpack(self.working.designer.state_vec)
        for name in param:
            inst = self.working.getsetters[name].set_inst(inst, param[name])
        return designer, inst
    
    def _errors(self, param={}):
        designer, inst = self._get_designer_inst(param)
        inst = designer.patch_instrument(inst)
        inst.prepare_phase()
        
        errors = [ ]
        
        s = 1200.0/math.log(2)
        for item in self.working.observations:
            w_obtained = designer.speed_of_sound / item.fqc
            w_expected = inst.true_wavelength_near(w_obtained, item.fingers)
            errors.append( (math.log(w_obtained)-math.log(w_expected))*s )
        
        return errors
    
    def _score(self, param):
        errors = self._errors(param)
        p = 2
        return (sum( abs(item**p) for item in errors ) / max(1,len(errors)))**(1.0/p)
    
    def _score_state(self, state):
        return self._score(self._combined_param(state))
    
    def _report(self, param, etc=[]):        
        print()
        for name, value in param.items():
            print('%s %.3f' % (name, value))
        print()
        for error, observation in zip(self._errors(param),self.working.observations):
            print('%6.1f cents  %s' % (error, observation.desc))
        print('--------------')        
        print('%6.1f score' % self._score(param))
        print()
    
    def run(self):
        self.working = Working()
        self.working.designer = design.load(self.working_dir)
        self.working.initial_inst = self.working.designer.unpack(self.working.designer.state_vec)
        self.working.getsetters = { }
        self.working.observations = [ ]
        self.working.opt_param = [ ]
        self.working.fixed_param = { }
        
        # Get getsetters
        for item in self.working.designer.parameters:
            if isinstance(item, config.Float_flag):
                self.working.getsetters[item.shell_name().lstrip("-")] = Flag_getsetter(item.name)
        for i in range(self.working.designer.n_holes):
            self.working.getsetters["diam"+str(i)] = Array_getsetter("hole_diameters",i)
            self.working.getsetters["len"+str(i)] = Array_getsetter("hole_lengths",i)
            self.working.getsetters["pos"+str(i)] = Array_getsetter("inner_hole_positions",i)
        
        # Parse observations
        for item in self.observations:
            parts = item.split(',')
            assert len(parts) == (self.working.designer.n_holes+1)
            fingers = [ int(item2) for item2 in parts[1:] ]
            obs = Observation()
            obs.fqc = float(parts[0])
            obs.fingers = fingers
            obs.desc = item
            self.working.observations.append(obs)
        
        # Provide a default set of "observations" if absent
        if not self.observations:
            for item in self.working.designer.fingerings:
                obs = Observation()
                obs.fqc = design.fqc(item[0]) * (2**(self.working.designer.transpose/12.0))
                obs.fingers = item[1]
                obs.desc = design.describe_fqc(obs.fqc) + "," + str(int(obs.fqc+0.5)) + "," + ",".join(str(item2) for item2 in obs.fingers)
                self.working.observations.append(obs)
        
        # Parse parameters
        for item in self.param.split(','):
            if not item: 
                continue
            
            is_fixed = '=' in item
            if is_fixed:
                item, value = item.split('=')
                value = float(value)
            
            # Can use underscores or dashes
            item = item.replace("_","-").lstrip("-")
            assert item in self.working.getsetters, "Unknown parameter: "+item
            
            if is_fixed:
                self.working.fixed_param[item] = value
            else:
                self.working.opt_param.append(item)
        
        initial = [ 
            self.working.getsetters[item].get(self.working.designer,self.working.initial_inst)
            for item in self.working.opt_param
            ]
        
        print('Current model, and errors:')
        self._report(self._current_param())
        
        if self.working.fixed_param:
            print('Model with fixed parameters set, and errors:')
            self._report(self._combined_param(initial))
        
        if self.working.opt_param:
            state = optimize.improve(
                self.shell_name(), 
                self._constraint_score, 
                self._score_state, 
                initial,
                #monitor=self._report
                )
            
            print('\nOptimized model, and errors:')
            self._report(self._combined_param(state))
        
        
        
        
