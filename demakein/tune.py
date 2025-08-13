
import math

from . import config, design, optimize


class Working(object): pass

class Observation(object): pass

@config.help(
    'Modelling the mouthpiece is more difficult than modelling the body of an '
    'instrument. Some parameters are most easily determined empirically.',
    'This tool tries to explain observed frequencies obtained from an instrument '
    'by tweaking parameters to do with the mouthpiece. '
    'Resultant parameters should then result in a correctly tuned instrument '
    'when the design tool is run again.',
    )
@config.Main_section(
    'observations',
    'Comma separated lists of frequency followed by '
    'whether each finger hole is open (0) or closed (1) '
    '(from bottom to top).'
    )
@config.String_flag(
    'param',
    'Comma separated list of parameters to tweak.'
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
            result[key] = getattr(self.working.designer,key)
        return result
    
    def _combined_param(self, state):
        result = self.working.fixed_param.copy()
        for key, value in zip(self.working.opt_param,state):
            result[key] = value
        return result
    
    def _errors(self, param={}):
        mod = self.working.designer(**param)
        
        instrument = mod.patch_instrument(
            mod.unpack(self.working.designer.state_vec)
            )
        instrument.prepare_phase()
        
        errors = [ ]
        
        s = 1200.0/math.log(2)
        for item in self.working.observations:
            w_obtained = mod.speed_of_sound / item.fqc
            w_expected = instrument.true_wavelength_near(w_obtained, item.fingers)
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
        self.working.observations = [ ]
        self.working.opt_param = [ ]
        self.working.fixed_param = { }
        
        for item in self.observations:
            parts = item.split(',')
            assert len(parts) == (self.working.designer.n_holes+1)
            fingers = [ int(item2) for item2 in parts[1:] ]
            obs = Observation()
            obs.fqc = float(parts[0])
            obs.fingers = fingers
            obs.desc = item
            self.working.observations.append(obs)
        
        if not self.observations:
            for item in self.working.designer.fingerings:
                obs = Observation()
                obs.fqc = design.fqc(item[0]) * (2**(self.working.designer.transpose/12.0))
                obs.fingers = item[1]
                obs.desc = design.describe_fqc(obs.fqc) + "," + str(int(obs.fqc+0.5)) + "," + ",".join(str(item2) for item2 in obs.fingers)
                self.working.observations.append(obs)
        
        for item in self.param.split(','):
            if not item: 
                continue
            
            is_fixed = '=' in item
            if is_fixed:
                item, value = item.split('=')
                value = float(value)
            
            # Can use underscores or dashes
            item = item.replace("_","-").lstrip("-")
            
            for item2 in self.working.designer.parameters:
                if item == item2.shell_name().lstrip("-"):
                    if is_fixed:
                        #self.working.designer = self.working.designer(**{item2.name:value})
                        self.working.fixed_param[item2.name] = value
                    else:
                        self.working.opt_param.append(item2.name)
                    break
            else:
                assert False, 'Unknown parameter: %s' % item
        
        initial = [ 
            getattr(self.working.designer,item)
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
        
        
        
        
