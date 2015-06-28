
import math

from nesoni import config

from . import design, optimize

class Working(object): pass

@config.help(
    'Modelling the mouthpiece is more difficult than modelling the body of an '
    'instrument. Some parameters are most easily determined empirically.',
    'This tool tries to explain observed frequencies obtained from an instrument '
    'by tweaking parameters to do with the mouthpiece. '
    'Resultant parameters should then result in a correctly tuned instrument '
    'when the design tool is run again.',
    )
@config.Positional(
    'tweak',
    'Comma separated list of parameters to tweak.'
    )
@config.Main_section(
    'observations',
    'Comma separated lists of frequency followed by '
    'whether each finger hole is open (0) or closed (1) '
    '(from bottom to top).'
    )
class Tune(config.Action_with_working_dir):
    tweak = None
    observations = [ ]
    
    def _constraint_score(self, state):
        #All positive
        return sum( max(-item,0.0) for item in state )
    
    def _errors(self, state):
        mod = self.working.designer(
            **dict(zip(self.working.parameters,state))
            )
        
        instrument = mod.patch_instrument(
            mod.unpack(self.working.designer.state_vec)
            )
        instrument.prepare_phase()
        
        errors = [ ]
        
        s = 1200.0/math.log(2)
        for item in self.observations:
            parts = item.split(',')
            assert len(parts) == (mod.n_holes+1)
            fingers = [ int(item2) for item2 in parts[1:] ]
            w_obtained = design.SPEED_OF_SOUND / float(parts[0])
            w_expected = instrument.true_wavelength_near(w_obtained, fingers)

            errors.append( (math.log(w_obtained)-math.log(w_expected))*s )
    
        return errors
    
    def _score(self, state):
        errors = self._errors(state)
        p = 2
        return (sum( abs(item**p) for item in errors ) / max(1,len(errors)))**(1.0/p)
    
    def _report(self, state, etc=[]):        
        print
        for name, value in zip(self.working.parameters, state):
            print '%s %.3f' % (name, value)
        print
        for error, observation in zip(self._errors(state),self.observations):
            print '%6.1f cents  %s' % (error, observation)
        print '--------------'        
        print '%6.1f score' % self._score(state)
        print
    
    def run(self):
        self.working = Working()
        self.working.designer = design.load(self.working_dir)
        self.working.parameters = [ ]
        
        for item in self.tweak.split(','):
            fixed = '=' in item
            if fixed:
                item, value = item.split('=')
                value = float(value)
            
            for item2 in self.working.designer.parameters:
                if item2.shell_name().lstrip('-') == item.lstrip('-'):
                    if fixed:
                        self.working.designer = self.working.designer(**{item2.name:value})
                    else:
                        self.working.parameters.append(item2.name)
                    break
            else:
                assert False, 'Unknown parameter: %s' % item
        
        initial = [ 
            getattr(self.working.designer,item)
            for item in self.working.parameters
            ]

        print 'Current model and errors:'        
        self._report(initial)
        
        if self.parameters:
            state = optimize.improve(
                self.shell_name(), 
                self._constraint_score, 
                self._score, 
                initial,
                #monitor=self._report
                )
            
            print 'Optimized model and errors:'
            self._report(state)
        
        
        
        