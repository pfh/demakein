"""

Gwarggllykiiiiillllllmeeeeeeeeecougcougcough

Note: pypy gc does not count c++ allocated memory, triggers major gc infrequently

"""

import os, subprocess, hashlib, gc, time, platform

def update_file(filename, content):
    good = os.path.exists(filename)
    if good:
        with open(filename,'rb') as f:
            current = f.read()
        good = (current == content)
    if not good:
        with open(filename,'wb') as f:
            f.write(content)
    return not good

def execute(command):
    assert 0 == os.system(command)

CMAKE_TEMPLATE = r"""
cmake_minimum_required (VERSION 2.6)

project (Project)

%(cmake_code)s

%(cmake_lib)s
"""

UNBOXED_TYPES = [
    'bool','int','long','unsigned int','unsigned long','double','void','char *','char const*'
]

class Box(object):
    def __init__(self, module, is_reference, cpp_type, value, deleter=None):
        self.module = module
        self.is_reference = is_reference
        self.cpp_type = cpp_type
        self.value = value
        self.deleter = deleter
    
    def __del__(self):
        if self.deleter:
            self.deleter(self.value)
    
    def __repr__(self):    
        return 'Box(%s,%s)' % (self.cpp_type + (' &' if self.is_reference else ''), self.value)
    
    def __str__(self):
        ss = self.module.new('std::stringstream()')
        self.module.do('a<<b', a=ss,b=self)
        cpp_str = self.module('a.str()',a=ss)
        c_str = self.module('a.c_str()',a=cpp_str)
        string = self.module.ffi.string(c_str)
        return string


class Lazy_init(object):
    def __init__(self, *args, **kwargs):
        self._init_args = (args, kwargs)
        self._init_done = False
    
    def __getattr__(self, name):
        if not self._init_done:
            self._lazy_init(*self._init_args[0],**self._init_args[1])
            del self._init_args
            self._init_done = True
        return object.__getattribute__(self, name)

class Module(Lazy_init):
    def _lazy_init(self, build_dir, preamble, cmake_code=''):
        import cffi
        
        self.build_dir = build_dir
        self.preamble = preamble
        self.code = [ ]
        self.cmake_code = cmake_code
        
        self.iteration = 0
        
        self.functions = { }

        self.modules = [ ]
        self.symbol_index = { }

        self.ffi = cffi.FFI()
        self.cdata_type = type(self.ffi.cast('int',0))
        
        self.gc_clock = 0
        
        self.parse_exports(self.preamble)
    
        try:
            with open(self.build_dir + '/hint','rb') as f:
                hint = f.read()
            hint = eval(hint)
            assert hint['preamble'] == self.preamble
            self.hint = hint['hint']
        except Exception:
            self.hint = [ ]
            
    def _gc_tick(self):
        t1 = time.time()
        if t1 >= self.gc_clock:
            gc.collect()
            t2 = time.time()
            self.gc_clock = t1+(t2-t1)*20.0
        
    def get_symbol(self, symbol):
        if symbol not in self.symbol_index:
            for module in self.modules:
                if hasattr(module,symbol):
                    self.symbol_index[symbol] = getattr(module, symbol)
                    break
        return self.symbol_index[symbol]
    
    def parse_exports(self, chunk):
        for line in chunk.split('\n'):
            if '/*export*/' in line:
                self.ffi.cdef(line.strip() + ';')
    
    def load_code(self, chunks):
        if not chunks:
            return
            
        iteration = self.iteration
        self.iteration += 1

        if not os.path.exists(self.build_dir):
            os.mkdir(self.build_dir)

        for chunk in chunks:
            self.parse_exports(chunk)

        filenames = [ ]
        for chunk in chunks:
            code = [ ]
            for line in (self.preamble+'\n'+chunk).split('\n'):
                if '/*export*/' in line:
                    code.append('extern "C" '+line.strip()+'\n')
                else:
                    code.append(line+'\n')            
            code = ''.join(code)
            filename = 'chunk_' + hashlib.sha1(code).hexdigest() + '.cpp'
            filenames.append(filename)
            update_file(self.build_dir+'/'+filename, code)
        
        if platform.system() == 'Darwin':
            cmake_lib = 'add_library (code%d SHARED %s)\n' % (iteration, ' '.join(filenames))
            cmake_code = self.cmake_code
            update_file(self.build_dir+'/CMakeLists.txt', CMAKE_TEMPLATE % locals())
            execute('cd '+self.build_dir+' && cmake .')
            execute('cd '+self.build_dir+' && make')
            self.modules.append( self.ffi.dlopen(self.build_dir+'/libcode%d.dylib' % iteration) )
                
        else:
            cmake_lib = 'add_library (code SHARED %s)\n' % ' '.join(filenames)
            cmake_code = self.cmake_code        
            update_file(self.build_dir+'/CMakeLists.txt', CMAKE_TEMPLATE % locals())
            execute('cd '+self.build_dir+' && cmake .')
            execute('cd '+self.build_dir+' && make && cp libcode.so libcode%d.so' % iteration)
            self.modules.append( self.ffi.dlopen(self.build_dir+'/libcode%d.so' % iteration) )
            execute('cd '+self.build_dir+' && rm libcode%d.so' % iteration)
        
        self.code.extend(chunks)

        with open(self.build_dir + '/hint','wb') as f:
            f.write( repr({'preamble':self.preamble, 'hint':self.code}) )

    def cpp_type(self, item):
        if isinstance(item, self.cdata_type):
            return self.ffi.getctype(self.ffi.typeof(value))
        elif isinstance(item, bool):
            return 'bool'
        elif isinstance(item, int):
            return 'int'
        elif isinstance(item, float):
            return 'double'
        elif isinstance(item, str):
            return 'char const*'
        elif isinstance(item, Box):
            return item.cpp_type
        assert False, 'Unhandled type'
    
    def c_type(self, item):
        if isinstance(item, Box):
            return 'void *'        
        cpp_type = self.cpp_type(item)
        if cpp_type == 'bool':
            return 'int'
        return cpp_type
    
    def c_value(self, c_type, item):
        if isinstance(item, str):
            item = self.ffi.new('char[]', item)
    
        if isinstance(item, Box):
            return self.ffi.cast(c_type, item.value)
        else:
            return self.ffi.cast(c_type, item)
        
    def is_reference(self, item):
        return isinstance(item,Box) and item.is_reference
    
    def require(self, *chunks):
        chunks = list(chunks) + self.hint
        self.hint = [ ]
        
        new_chunks = [ ]
        for chunk in chunks:
            if chunk not in self.code and chunk not in new_chunks:
                new_chunks.append(chunk)

        self.load_code(new_chunks)

    def eval(self, expression, _return_value=True, _as_reference=False, **args):
        """ _as_reference=True : 
                requires return type to be a pointer,
                result will behave as a reference, 
                will be garbage collected
        """
        self._gc_tick()
        
        arg_names = tuple(sorted(args))
        arg_is_reference = tuple( self.is_reference(args[item]) for item in arg_names )
        arg_cpp_types = tuple( self.cpp_type(args[item]) for item in arg_names )
        arg_c_types = [ self.c_type(args[item]) for item in arg_names ]
        arg_c_values = [ self.c_value(c_type, args[item]) for c_type, item in zip(arg_c_types, arg_names) ]
        signature = (_return_value, expression, arg_names, arg_cpp_types, arg_is_reference)
        
        if signature not in self.functions:
            parameters = [ ]
            header = ''
            for i in xrange(len(arg_names)):
                param = arg_names[i]
                c_type = arg_c_types[i]
                cpp_type = arg_cpp_types[i]
                is_reference = arg_is_reference[i]
                if cpp_type != c_type:
                    parameters.append( '%(c_type)s _%(param)s' % locals() )
                    if is_reference:
                        header += '  %(cpp_type)s &%(param)s = *(%(cpp_type)s*)_%(param)s;\n' % locals()
                    else:
                        header += '  %(cpp_type)s %(param)s = (%(cpp_type)s)_%(param)s;\n' % locals()
                else:
                    parameters.append( '%(c_type)s %(param)s' % locals() )
            all_parameters = ','.join(parameters)
            
            name = 'lambda_'+hashlib.sha1(repr(signature)).hexdigest()
            
            if not _return_value:
                as_reference = False
                return_cpp_type = 'void'
                return_c_type = 'void'
                delete_name = None
                code = (
                    '%(return_c_type)s %(name)s(%(all_parameters)s) /*export*/\n' % locals() +
                    '{\n' +
                    header +
                    '  %(expression)s;\n' % locals() +
                    '}\n\n'
                )            
                self.require(code)
                
            else:
                typegetter_name = 'type_'+name
                
                code = (
                    'const char* %(typegetter_name)s(%(all_parameters)s) /*export*/\n' % locals() +
                    '{\n' +
                    header +
                    '  return typeid(( %(expression)s )).name();\n' % locals() +
                    '}\n\n'
                )
                #                    ^ Double brackets so doesn't return function type
                self.require(code)
                
                mangle = self.ffi.string(self.get_symbol(typegetter_name)(*arg_c_values))
                with subprocess.Popen(['c++filt','-t',mangle],stdout=subprocess.PIPE).stdout as f:
                    return_cpp_type = f.read().strip()
                
                if _as_reference:
                    as_reference = True
                    assert return_cpp_type.endswith('*')
                    return_cpp_type = return_cpp_type[:-1]
                    return_c_type = 'void *'
                
                else:
                    as_reference = not (return_cpp_type in UNBOXED_TYPES)
                    if as_reference:
                        expression = 'new ('+return_cpp_type+')(('+expression+'))'
                        return_c_type = 'void *'
                    else:
                        return_c_type = return_cpp_type
                        if return_c_type == 'bool':
                            return_c_type = 'int'
                
                code = (
                    '%(return_c_type)s %(name)s(%(all_parameters)s) /*export*/\n' % locals() +
                    '{\n' +
                    header +
                    '  return (%(return_c_type)s)( %(expression)s );\n' % locals() +
                    '}\n\n'
                )            
                if not as_reference:
                    self.require(code)
                    delete_name = None
                else:
                    delete_name = 'delete_' + hashlib.sha1(return_cpp_type).hexdigest()
                    delete_code = (
                        'void %(delete_name)s(void *item) /*export*/\n'
                        '{\n'
                        '  delete (%(return_cpp_type)s *)item;\n'
                        '}\n\n'
                    ) % locals()
                    
                    self.require(code, delete_code)

            
            self.functions[signature] = (name, as_reference, return_c_type, return_cpp_type, delete_name)
        
        (name, as_reference, return_c_type, return_cpp_type, delete_name) = self.functions[signature]

        if delete_name:
            deleter = self.get_symbol(delete_name)
        else:
            deleter = None

        result = self.get_symbol(name)(*arg_c_values)
        
        if as_reference:
            result = Box(self, as_reference, return_cpp_type, result, deleter)
            
        elif return_cpp_type == 'bool':
            result = bool(result)

        return result
    
    __call__ = eval
    
    def do(self, expression, **args):
        self.eval(expression, _return_value=False, **args)
    
    def as_reference(self, expression, **args):
        """ Treat the result (a pointer) as a reference.
            Result will be garbage collected.
        """
        return self.eval(expression,_as_reference=True,**args)
    
    def new(self, initializer, **args):
        return self.as_reference('new '+initializer,**args)
    
    def call(self, func, *args):
        names = [ '_arg%d' % i for i in xrange(len(args)) ]
        param = dict(zip(names,args))
        expression = func + '('+','.join(names)+')'
        return self.eval(expression, **param)
    
    def iterate(self, expr_begin, expr_end, **args):
        i = self(expr_begin,**args)
        end = self(expr_end,**args)
        while not self('a==b',a=i,b=end):
            yield self('*a',a=i)
            self.do('++a',a=i)
    
    def circulate(self, expression, **args):
        start = self(expression,**args)
        i = self('a',a=start)
        while True:
            yield self('*a',a=i)
            self.do('++a',a=i)
            if self('a==b',a=i,b=start): 
                break
        


if __name__ == '__main__':
    M = Module('__testcpp__', """
#include <typeinfo>
#include <iostream>
#include <vector>
""")

    # Execute a statement
    M.do('std::cout << "Hello world." << std::endl')
    
    # Create a new object (will be deleted by garbage collector)
    vec = M.new('std::vector<int>')
    
    for i in xrange(10):
        M.do('a.push_back(b)', a=vec, b=i)
    
    # for(i=<expr1>;i!=<expr2>;i++) yield *i
    for i in M.iterate('a.begin()','a.end()',a=vec):
        #Compute a value
        square = M('a*a',a=i)
        
        M.do('std::cout << a << std::endl',a=square)

