
"""

Tools as classes.

Metainformation about tools allows
- automatic help text
- ability to pickle and pass around specification of job that needs to be done (eg on a cluster)
- Make-like checking of what needs to be re-done

"""


import sys, os, pickle, traceback, textwrap, re, copy, functools, types, datetime, pipes, platform

from . import workspace


class Error(Exception): 
    pass


def filesystem_friendly_name(name):
    """ Remove special characters from a name """

    for char in '\'"<>&|/\\_ .':
        name = name.replace(char,'_')
    return name



def colored(color, text):
    return '\x1b[%dm%s\x1b[m' % (color, text)

def color_as_flag(text): return colored(1, text)
def color_as_template(text): return colored(32, text)
def color_as_value(text): return colored(35, text)
def color_as_comment(text): return colored(36, text)

def strip_color(text):
    return re.sub(r'\x1b\[\d*m','',text)

def write_colored_text(file, text):
    if not file.isatty() or not os.name == 'posix':
        text = strip_color(text)
    file.write(text)

def wrap(text, width, prefix='', suffix=''):
    result = [ ]
    for line in text.rstrip().split('\n'):
        result.extend(textwrap.wrap(line.rstrip(), width, break_on_hyphens=False, break_long_words=False) or [''])
    return prefix + (suffix+'\n'+prefix).join(result)


def get_flag_value(args, option, conversion_function):
    """ Get a command line option """
    args = args[:]
    value = None
    present = False
    while True:
        try:
            location = args.index(option)
        except ValueError: #Not found
            break
            
        if location == len(args)-1 :
            raise Error('Option %s requires a paramter' % option)
        
        try:
            value = conversion_function(args[location+1])
            present = True
        except Exception:
            raise Error('Option for %s not in expected format' % option)
        
        del args[location:location+2]

    return present, value, args

def expect_no_further_flags(args):
    for arg in args:
        if re.match(r'--?[A-Za-z\-]+$', arg):
            raise Error('Unexpected flag "%s"' % arg)
        if arg.endswith(':'):
            raise Error('Unexpected section "%s"' % arg)


def execute(args, commands, default_command):
    """ Execute a series of commands specified on the command line.
        
        eg
        [default command param] command: [param ...] command: [param ...]
    """
    command_locations = [ i for i,arg in enumerate(args) if arg in commands ]
    split_points = command_locations + [len(args)]    
    
    default_command(args[:split_points[0]])
    
    for start, end in zip(command_locations, split_points[1:]):
        commands[args[start]](args[start+1:end])

def as_bool(string):
    string = string.lower()
    if string in ('yes','y','true','t'): return True
    if string in ('no','n','false','f'): return False
    value = int(string)
    assert value in (0,1)
    return bool(value)

def describe_bool(boolean):
    if boolean:
        return 'yes'
    else:
        return 'no'


class Parameter(object):
    sort_order = 0

    def __init__(self, name, help='', affects_output=True):
        self.name = name
        self.help = help
        self.affects_output = affects_output
        
    def get_flags(self):
        return [ ]
    def get_sections(self):
        return [ ]

    def get_doc_help(self, obj):
        return self.help

    def parse(self, obj, what, string):
        return string
    
    def describe(self, value):
        return str(value)
    
    def describe_quoted(self, value):
        return pipes.quote(self.describe(value))

    def __call__(self, item):
        # Put the parameter after any parameters from base classes
        # but before any parameters from this class.
        # (parameter decorations are evaluated in reverse order)
        n = 0
        while n < len(item.parameters):
            is_in_base = False
            for base in item.__bases__:
                if item.parameters[n] in base.parameters:
                    is_in_base = True
                    break
            if not is_in_base: break                    
            n += 1
        item.parameters = item.parameters[:n] + (self,) + item.parameters[n:]
        return item
    
    def cast(self, obj, value):
        """ Convert value to desired type """
        return value
    
    def set(self, obj, value):
        setattr(obj, self.name, self.cast(obj, value))
    
    def get(self, obj):
        return getattr(obj, self.name)
        
    def describe_shell(self, obj, verbose=True):
        value = self.get(obj)
        if value is None and not verbose: 
            return ''
        return color_as_flag(self.shell_name()) + ' ' + \
               (color_as_value if value is not None else color_as_template)(self.describe_quoted(value))


class Hidden(Parameter):
    def describe_shell(self, obj, verbose=True):
        return ''


class Positional(Parameter): 
    sort_order = 1

    def shell_name(self):
        return '<%s>' % self.name.replace('_','-').lower()
    
    def parse(self, obj, what, string):
        expect_no_further_flags([string])
        return string
    
    def describe_shell(self, obj, verbose=True):
        value = self.get(obj)
        if value is None:
            return color_as_template(self.shell_name()) if verbose else ''
        else:
            return color_as_value(self.describe(value))


class Flag(Parameter):
    sort_order = 0

    def shell_name(self):
        return '--'+self.name.replace('_','-').rstrip('-').lower()
    
    def get_flags(self):
        return [ self.shell_name() ]


class String_flag(Flag):
    def describe(self, value):
        return value if value is not None else '...'


class Bool_flag(Flag):
    def parse(self, obj, what, string): 
        return as_bool(string)
        
    def describe(self, value): 
        if value is None: 
            return 'yes/no'
        return describe_bool(value)


class Ifavailable_flag(Flag):
    """ A flag with possible values
        False
        True
        'ifavailable'
        
        The intention is to allow more things to be on by default,
        while still allowing a feature to be forced on or forced off
        if absolute replicability is required.
    """
    def parse(self, obj, what, string):
        string = string.lower()
        if string in ('yes','y','t'):
            return True
        elif string in ('no','n','f'):
            return False
        elif string in ('ifavailable','if'):
            return 'ifavailable'

    def describe(self, value):
        if value is None:
            return 'yes/no/ifavailable'
        elif value == 'ifavailable':
            return 'ifavailable'
        elif value:
            return 'yes'
        else:
            return 'no'

def apply_ifavailable(value, test):
    from . import grace
    if value == 'ifavailable':
        return test()
    else:
        return value

def apply_ifavailable_program(value, program):
    from . import grace
    if value == 'ifavailable':
        return grace.can_execute(program)
    else:
        return value

def apply_ifavailable_jar(value, jar):
    from . import io
    if value == 'ifavailable':
        try: io.find_jar(jar)
        except Error:
            return False
        return True
    else:
        return value


class Int_flag(Flag):
    def parse(self, obj, what, string):
        return int(string)
    
    def describe(self, value):
        if value is None: 
           return 'NNN'
        return '%d' % value


class Float_flag(Flag):
    def parse(self, obj, what, string):
        return float(string)
    
    def describe(self, value):
        if value is None: 
           return 'N.NN'
        if abs(value) < 0.01:
           return '%.3e' % value
        return '%.3f' % value

        

class Section(Parameter):
    sort_order = 3

    def __init__(self, name, help='', affects_output=True, allow_flags=False, empty_is_ok=True, append=True):
        Parameter.__init__(self,name=name,help=help,affects_output=affects_output)
        self.allow_flags = allow_flags
        self.empty_is_ok = empty_is_ok
        self.append = append

    def parse(self, obj, what, args):
        if not self.allow_flags:
            expect_no_further_flags(args)
        if self.append:
            return (self.get(obj) or []) + args
        else:
            return args

    def shell_name(self):
        return self.name.replace('_','-').rstrip('-').lower()+':'
    
    def get_sections(self):
        return [ self.shell_name() ]

    def describe_each(self, value):
        if not value: return [ ]
        return [ str(item) for item in value ]

    def describe(self, value):
        if value is None: return '...'
        return ' '.join(self.describe_each(value))
    
    def describe_quoted(self, value):
        if value is None: return '...'
        return ' '.join([ pipes.quote(item) for item in self.describe_each(value) ])

    def describe_shell(self, obj, verbose=True):
        value = self.get(obj)
        if not verbose and not value: return ''
        return Parameter.describe_shell(self, obj, verbose) 


class Grouped_section(Section):
    def parse(self, obj, what, args):
        if not self.allow_flags:
            expect_no_further_flags(args)
        return self.get(obj) + [ args ]

    def describe_each(self, value):
        return [ self.shell_name() + ' ' + ' '.join(item) for item in value ]
    
    def describe_quoted(self, value):
        return ' '.join([ 
            self.shell_name() + 
            ' ' + 
            ' '.join([ pipes.quote(item2) for item2 in item]) 
            for item in value
            ])
    
    def describe_shell(self, obj, verbose=True):
        value = self.get(obj)
        if verbose and not value:
            return color_as_flag(self.shell_name()) + ' ' + color_as_template('...')
        return '\n'.join(
            color_as_flag(self.shell_name()) + 
            ' ' + 
            color_as_value(' '.join(pipes.quote(item2) for item2 in item))
            for item in value
            )
            

class Float_section(Section):
    def parse(self, obj, what, args):
        return self.get(obj) + [ float(item) for item in args ]

    def describe_each(self, value):
        return [ '%f' % item for item in value ]


class Main_section(Section):
    sort_order = 2
    
    def get_sections(self):
        return [ ]

    def shell_name(self):
        return '<' + self.name.replace('_','-').rstrip('-').lower()+' ...>'

    def describe_shell(self, obj, verbose=True):
        value = self.get(obj)
        if not value:
            if verbose:
                return color_as_template(self.shell_name())
            else:
                return ''
        else:
            return color_as_value(self.describe(value))


class Configurable_section(Section):
    """ A section containing another configuarbale.
    
        presets if given is a list [(name, lambda obj -> configurable, description)]  
        
        Each item may be a configurable or None
        
        To avoid circular dependancies, 
        if the class attribute is not set
        it defaults to the first preset.
    """
    def __init__(self, name, help='', affects_output=True, empty_is_ok=True, presets=[]):
        super(Configurable_section,self).__init__(
            name=name,
            help=help,
            affects_output=affects_output,
            allow_flags=True,
            empty_is_ok=empty_is_ok
        )
        self.presets = presets
        self.original_help = help
        
        if self.presets:
            self.help += '\n\nChoose from the following, then supply extra flags as needed:\n'
            
            for item in self.presets:
                self.help += ' ' + item[0] + ' - ' + item[2] + '\n'

    def get_doc_help(self, obj):
        help = self.original_help
        help += '\n\nThis can either be a string to select one of the following presets, '
        help += 'or an instance of the same type as one of the presets, '
        help += 'or indeed an instance of any Configurable that quacks sufficiently like one of the presets:\n\n'
        for item in self.presets:
            help += ' ' + repr(item[0]) + ' (' + repr(item[1](obj)) + ')\n    ' + item[2] + '\n'        
        help += '\nFurther parameters of the form '+self.name+'__parametername can be given'
        help += ' in order to customize the Configurable further.'
        return help
    
    def get(self, obj):
        if hasattr(obj, self.name):
            return super(Configurable_section,self).get(obj)
        else:
            return self.presets[0][1](obj)

    def cast(self, obj, value):
        if isinstance(value, str):
            for item in self.presets:
                if value.lower() == item[0].lower():
                    return item[1](obj)
        assert value is None or isinstance(value, Configurable), 'Incorrect type for '+self.name
        return value
        
    def parse(self, obj, what, args):
        for item in self.presets:
            if args and args[0].lower() == item[0].lower():
                base = item[1](obj)
                args = args[1:]
                break
        else:
            base = self.get(obj)
        
        if base is None:
            assert not args, 'Can\'t modify empty section'        
            new = None
        else:
            new = base()
            new.parse( args )
        return new

    def describe_shell(self, obj, verbose=True):
        value = self.get(obj)
        preset_guess = None
        for item in self.presets:
            if value == item[1](obj):
                preset_guess = item
                break
        if not preset_guess:
            for item in self.presets:
                if type(value) == type(item[1](obj)):
                    preset_guess = item
                    break
        
        result = color_as_flag(self.shell_name()) 
        if preset_guess:
            result += ' ' + color_as_value(preset_guess[0])
        if value is not None and (not verbose or not preset_guess or (value != preset_guess[1])):
            result += value.describe(invocation='',show_help=False,escape_newlines=False,brief=True)
        return result


class Grouped_configurable_section(Section):
    def __init__(self, name, help='', affects_output=True, empty_is_ok=True, template_getter=None):
        super(Grouped_configurable_section,self).__init__(
            name=name,
            help=help,
            affects_output=affects_output,
            allow_flags=True,
            empty_is_ok=empty_is_ok
        )
        self.template_getter = template_getter

    def get_doc_help(self, obj):        
        element_type = type(self.template_getter(obj))
        help = 'Give this as a list of %s.\n\n' % element_type.__name__ + self.help
        return help

    def parse(self, obj, what, args):
        new = self.template_getter(obj)()
        new.parse( args )
        return self.get(obj) + [ new ]

    def describe_shell(self, obj, verbose=True):
        value = self.get(obj)
        if verbose and not value:
            return color_as_flag(self.shell_name()) + ' ' + color_as_template('...')
        return '\n'.join(
            color_as_flag(self.shell_name()) + 
            item.describe(invocation='',show_help=False,escape_newlines=False).rstrip('\n')
            for item in value
        )


class Configurable_section_list(Section):
    """ Create a list by optionally selecting a preset list 
        then giving additional sections.
    
        templates is a list of (name, lambda obj: list of configurables, description)
        sections is a list of (name, lambda obj: configurable, description)
    
        """
    def __init__(self, name, help='', affects_output=True, empty_is_ok=True,
          templates = [ 'clear', lambda obj: [] ],
          sections = [ ]):
        super(Configurable_section_list,self).__init__(
            name,
            help,
            affects_output=affects_output,
            empty_is_ok=empty_is_ok,
            )
        self.templates = templates
        self.sections = sections
        self.original_help = help
    
    def get_sections(self):
        return [ self.shell_name() ] + [ item[0]+':' for item in self.sections ]
    
    def parse(self, obj, what, args):
        if what == self.shell_name():
            result = [ ]
            for item in args:
                for name,getter,help in self.presets:
                    if name.lower() == item.lower():
                        result += getter(obj)
                        break
                else:
                    raise Error('Unknown preset "'+item+'" in '+self.shell_name())
            return result
        
        for name,getter,help in self.sections:
            if name.lower()+':' == what.lower():
                break
        else:
            assert False, 'This should never happen.'
        
        new = getter(obj)()
        new.parse(args)        
        return self.get(obj) + [ new ]
    
    def describe_shell(self, obj, verbose=True):
        value = self.get(obj)
        if verbose:
            if not value:
                result = [ ]
                if self.templates:
                    result.append(color_as_flag(self.shell_name()) + ' ' + color_as_template('...'))
                for item in self.sections:
                    result.append(color_as_flag(item[0]+':') + ' ' + color_as_template('...'))
                    result.append(color_as_template('...'))
                return '\n'.join(result)
            for item in self.templates:
                if item[1](obj) == value:
                    return color_as_flag(self.shell_name()) + ' ' + color_as_value(item[0]) 

        result = [ ]
        
        for item in self.templates:
            if item[1](obj) == [ ]:
                result.append( color_as_flag(self.shell_name()) + ' ' + color_as_value(item[0]) )
                break
        
        for item in value:
            section_guess = None
            for item2 in self.sections:
                if item == item2[1](obj):
                    section_guess = item2
                    break
            if not section_guess:
                for item2 in self.sections:
                    if type(item) == type(item2[1](obj)):
                        section_guess = item2
                        break
            
            if section_guess:
                this_result = color_as_flag(section_guess[0]+': ')
            else:
                this_result = color_as_flag('<'+type(item).__name__+'>: ')
            
            if not verbose or not section_guess or (value != section_guess[1](obj)):
                this_result += item.describe(invocation='',show_help=False,escape_newlines=False,brief=True)
            
            result.append(this_result)
        return '\n'.join(result)
        
    
    
    
        

def help(short, extra=''):
    full = short
    if extra: full += '\n\n' + extra

    def func(item):
        item.help = full
        item.help_short = short
        return item
    return func


def _wrap(func, before, after):
    @functools.wraps(func)
    def inner(self, *args,**kwargs):
        before(self)
        try:
            return func(self,*args,**kwargs)
        finally:
            after(self)
    return inner

class Configurable_metaclass(type):
    def __new__(self, name, bases, dictionary):
        # Inherit parameters from all bases    
        parameters = ()
        for base in bases:            
            if hasattr(base, 'parameters'):
                for parameter in base.parameters:
                    if parameter not in parameters:
                        parameters += (parameter,)
        dictionary['parameters'] = parameters + dictionary.get('parameters',())
        
        if '__doc__' in dictionary:
            dictionary['__doc__original__'] = dictionary['__doc__']
            del dictionary['__doc__']
        
        result = type.__new__(self, name, bases, dictionary)
        
        for name in dictionary:
            if not isinstance(dictionary[name], types.FunctionType): continue
            
            func = dictionary[name]
            entries = [ ]
            exits = [ ]
            before_name = '_before_'+name
            after_name = '_after_'+name
            for item in result.mro():
                if before_name in item.__dict__ or after_name in item.__dict__:
                    func = _wrap(func,item.__dict__.get(before_name,lambda self:None),
                                      item.__dict__.get(after_name,lambda self:None))
            setattr(result, name, func) 
        
        return result 

    @property
    def __doc__(self):
        result = getattr(self,'__doc__original__','')
        result += '\n\n' + wrap(self.help, 70)
        
        result += '\n\nParameters:\n'
        for parameter in self.parameters:
            result += '\n' + parameter.name + ' = ' + repr(parameter.get(self)) + '\n' + wrap(parameter.get_doc_help(self()), 65, '     # ')
        return result

    def __dir__(self):
        result = [ ]
        for item in self.mro():
            for key, value in item.__dict__.items():
                if key not in result and isinstance(value, types.FunctionType) and not key.startswith('_'):
                    result.append(key)
        return result 


class Configurable(object):
    __metaclass__ = Configurable_metaclass
    
    parameters = ()
        
    help = ''
    help_short = ''
    
    def __init__(self, *args, **kwargs):
        self._modify(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        result = copy.deepcopy(self)
        result._modify(*args, **kwargs)
        return result
    
    def _modify(self, *args, **kwargs):
        unused = set(kwargs)
        for parameter in self.parameters:            
            if isinstance(parameter, Positional) and args:
                value = args[0]        
                args = args[1:]
            elif isinstance(parameter, Main_section) and args:
                value = args
                args = [ ]
            elif parameter.name in kwargs:
                value = kwargs[parameter.name]
                unused.remove(parameter.name)
            #elif 'modify_'+parameter.name in kwargs:
            #    value = kwargs['modify_'+parameter.name]( parameter.get(self) )
            #    unused.remove('modify_'+parameter.name)
            else:
                value = parameter.get(self)
            
            # Set all parameters, even unmodified ones,
            # so that values that are just a class default will be pickled    
            parameter.set(self, value)
        
        for parameter in self.parameters:
            modification = { }
            for name in unused.copy():
                if name.startswith(parameter.name+'__'):
                    modification[ name[len(parameter.name)+2:] ] = kwargs[name]
                    unused.remove(name)
            if modification:
                parameter.set(self, parameter.get(self)( **modification ))

        assert not unused, 'Unknown named parameter: '+', '.join(unused)
        assert not args, 'Unexpected parameters'         
        
    def parse_partial(self, args):
        """ Parse command line arguments.
        
            Return any unused arguments (including flags).
        """
        kwargs = { }
        for parameter in self.parameters:
            for flag in parameter.get_flags():
                present, value, args = get_flag_value(args,flag,lambda item: parameter.parse(self, flag, item))
                if present:
                    parameter.set(self, value)

        leftovers = [ ]        
        def default_command(args):
            leftovers.extend(args)

        commands = { }
        
        for parameter in self.parameters:
            if isinstance(parameter, Main_section):
                def command(args, self=self,parameter=parameter):
                    value = parameter.parse(self, None, args)
                    parameter.set(self, value) 
                default_command = command

            for section in parameter.get_sections():
                def command(args, self=self,section=section,parameter=parameter):
                    value = parameter.parse(self, section, args)
                    parameter.set(self, value) 
                commands[section] = command
         
        def outer_default_command(args):
            for parameter in self.parameters:
                if args and isinstance(parameter, Positional):
                    parameter.set(self, parameter.parse(self, None, args[0]))
                    args = args[1:]
            default_command(args)
        
        execute(args, commands, outer_default_command)
        return leftovers

    def parse(self, args):
        """ Parse command line arguments.
        
            Raise an error if there are any unused parameters or flags.
        """
        leftovers = self.parse_partial(args)
        expect_no_further_flags(leftovers)
        if leftovers:
            raise Error('Unexpected parameters: ' + ' '.join(leftovers))


    @classmethod
    def shell_name(self):
        return self.__name__.lower().replace('_','-').strip('-')
    
    def ident(self):
        return self.shell_name()
    
    def __repr__(self):
        name = type(self).__name__
        return '<an instance of '+name+'>'
    
    def __cmp__(self, other):
        c = cmp(self.__class__, other.__class__)
        if c: return c
        for parameter in self.parameters:
            if not parameter.affects_output: 
                continue
            
            c = cmp(parameter.get(self), parameter.get(other))
            if c: return c
        return 0
    
    def describe(self, invocation=None, show_help=False, escape_newlines=True, brief=False):
        if invocation is None:
            invocation = self.shell_name() + ':'            
    
        desc = [ colored(1, invocation) ]
        
        if escape_newlines:
            if os.name == 'nt':
                suffix = ' ^'
            else:
                suffix = ' \\'
        else:
            suffix = ''
        
        order = sorted(
            range(len(self.parameters)),
            key=lambda i: (self.parameters[i].sort_order, i)
        )
        
        for i in order:
            parameter = self.parameters[i]
            if brief and parameter.get(self) == parameter.get(type(self)()):
                continue
            line = parameter.describe_shell(self, show_help)
            if line:
                desc.append(wrap(line,67,'    ',suffix))
                if show_help and parameter.help:
                    desc.append(colored(36,wrap(parameter.help,65,'      # ')))
       
        return (colored(2,suffix)+'\n').join( desc ) + '\n'
    

class Action(Configurable):
    run = NotImplemented

    def cores_required(self):
        return 1
    
    def state_filename(self):
        return os.path.join('.state', filesystem_friendly_name(self.ident()))
    
    def make(self):
        from . import legion
        legion.make(self)

    def process_make(self, stage=None):
        from . import legion
        legion.process_make(self, stage)
        



class Action_with_log(Action):
    log_filename = NotImplemented
    
    _log_level = 0
    
    def _before_run(self):
        if self._log_level == 0:
            filename = self.log_filename()
            if filename is not None and os.path.exists(filename):
                os.unlink(filename)
        
            self._log_start = datetime.datetime.now()
        
            import demakein
            from . import grace
            self.log = grace.Log()
            self.log.quietly_log(
               '\n'+
               strip_color(self.describe())+'\n'+
               'from '+os.getcwd()+'\n\n'+    
               'demakein '+demakein.VERSION+'\n\n'
            )
        self._log_level = self._log_level + 1

        if os.name == 'posix':
            import resource 
            self._memory_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    
    def _after_run(self):
        self._log_level = self._log_level - 1
        if self._log_level == 0:
            now = datetime.datetime.now()
            
            if os.name == 'posix':
                # Broken on Windows, unsure why
                self.log.quietly_log(
                    '\n' +
                    ' started '+ self._log_start.strftime('%_d %B %Y %_I:%M %p') + '\n'
                    'finished '+ now.strftime('%_d %B %Y %_I:%M %p') + '\n'
                    'run time '+ str( datetime.timedelta(seconds=int((now-self._log_start).total_seconds())) ) + '\n'
                )
            
                # Can only see peak memory usage
                # so only report it if we increased it
                import resource 
                memory_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                if memory_after > self._memory_before:
                    self.log.quietly_log(
                        '\npeak memory used ' + str(memory_after) + 
                        (' kb' if platform.system() == 'Linux' else ' units') +
                        '\n')
                del self._memory_before

            filename = self.log_filename()
            if filename is not None and os.path.exists(os.path.split(filename)[0] or '.'):
                self.log.attach(open(filename,'ab'))
            self.log.close()
            del self.log
            del self._log_start
            del self._log_level


@Positional('prefix', 'Prefix for output files.')
class Action_with_prefix(Action_with_log):
    prefix = None
    def ident(self):
        return super(Action_with_prefix,self).ident() + '--' + (self.prefix or '') 

    def log_filename(self):
        if self.prefix is None: return None
        return self.prefix + '_log.txt'

    def state_filename(self):
        return self.prefix + '.state'
    
    def _before_run(self):
        if not self.prefix:
            raise Error('You need to specify a prefix for the output files.')


@Positional('output_dir', 'Directory for output files (will be created if does not exist).')
class Action_with_output_dir(Action_with_log):
    output_dir = None

    _workspace_class = workspace.Workspace
    def get_workspace(self):
        return self._workspace_class(self.output_dir, must_exist=False)

    def ident(self):
        return Action.ident(self) + '--' + (self.output_dir or '')    

    def log_filename(self):
        if self.output_dir is None: return None
        return os.path.join(self.output_dir, self.shell_name() + '_log.txt')

    def state_filename(self):
        return os.path.join(self.output_dir, self.shell_name() + '.state')
    
    def _before_run(self):
        if not self.output_dir:
            raise Error('You need to specify an output directory.')


@Positional('working_dir', 'Directory for input and output files.')
class Action_with_working_dir(Action_with_log):
    working_dir = None
    
    _workspace_class = workspace.Workspace
    def get_workspace(self):
        return self._workspace_class(self.working_dir, must_exist=True)
    
    def ident(self):
        return Action.ident(self) + '--' + (self.working_dir or '')

    def log_filename(self):
        if self.working_dir is None: return None
        return os.path.join(self.working_dir, self.shell_name() + '_log.txt')

    def state_filename(self):
        return os.path.join(self.working_dir, self.shell_name() + '.state')
    
    def _before_run(self):
        if not self.working_dir:
            raise Error('You need to specify a working directory.')



#@String_flag('output', 'Output file (defaults to stdout). If filename ends with .gz or .bz2 it will be compressed appropriately.')
#class Action_with_optional_output(Action):
#    output = None
#    
#    def ident(self):
#        return super(Action_with_optional_output,self).ident() + '--' + (self.output or '') 
#
#    def begin_output(self):
#        from nesoni import io
#    
#        if self.output is not None:
#           return io.open_possibly_compressed_writer(self.output)
#        else:
#           return sys.stdout
#
#    def end_output(self, f):
#        if self.output is not None:
#            f.close()

#@String_flag('input', 'Input file (defaults to stdin). The file may be compressed with gzip or bzip2 or be a BAM file.')
#class Action_with_optional_input(Action):
#    input = None
#
#    def begin_input(self):
#        from nesoni import io    
#        
#        if self.input is not None:
#           return io.open_possibly_compressed_file(self.input)
#        else:
#           return sys.stdin
#
#    def end_input(self, f):
#        if self.input is not None:
#            f.close()

#class Action_filter(Action_with_optional_input, Action_with_optional_output):
#    pass



def report_exception():    
    exception = sys.exc_info()[1]
    
    brief = False
    
    if (isinstance(exception, EnvironmentError) and \
        exception.strerror == 'No such file or directory' and \
        exception.filename):
       brief = True
    
    if isinstance(exception, Error) and len(exception.args) > 0:
        brief = True
    
    if not brief:
        write_colored_text(sys.stderr, 
        '\n' + colored(2, 'Traceback:\n'+''.join(traceback.format_tb(sys.exc_info()[2]))))

    write_colored_text(sys.stderr, 
        '\n' + colored(1,colored(31, exception.__class__.__name__+':')) + '\n')
    
    if isinstance(exception, EnvironmentError):
        args = [ exception.strerror, exception.filename ]
    else:
        args = exception.args
    
    for arg in args:
        if arg:
            write_colored_text(sys.stderr, 
                colored(31, wrap(str(arg), 70, '    ')) + '\n')
    sys.stderr.write('\n')


def shell_run(action, args, invocation=None, help=True):
    args = list(args)

    args_needed = False
    for item in action.parameters:
        if isinstance(item, Positional) or (isinstance(item, Section) and not item.empty_is_ok):
            args_needed = True

    if (args_needed and not args) or args == ['-h'] or args == ['--help']:
        write_colored_text(sys.stdout, 
            '\n'+action.describe(invocation, show_help=True, escape_newlines=False)+'\n'+
            wrap(action.help, 70)+'\n\n\n'
        )
        sys.exit(1)        
    
    try:
        action.parse(args)
        write_colored_text(sys.stderr, '\n'+action.describe(invocation)+'\n')
        action.run()
    except:
        report_exception()
        sys.exit(1)





