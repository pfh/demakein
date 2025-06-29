
# Run a job =====================================================

if __name__ == '__main__':
    def run_job():
        import sys, os, base64
    
        # Connect to coordinator
        current_dir, python_path, main_file, address, authkey, mail_number = eval(base64.b64decode(sys.argv[1]))
        
        # Try to recreate execution environment
        os.chdir(current_dir)
        sys.path = python_path
        
        from demakein import legion
            
        legion.manager(address, authkey, connect=True)
        
        if main_file is not None: # so unpickling functions in __main__ works
            module = imp.new_module('__job__')
            module.__file__ = main_file
            sys.modules['__job__'] = module
            sys.modules['__main__'] = module
            exec(compile(open(main_file, "rb").read(), main_file, 'exec'), module.__dict__)
        
        # Retrieve function and execute
        func, args, kwargs = legion.coordinator().get_mail(mail_number)
        func(*args,**kwargs) 
        sys.exit(0)

    run_job()

else:
    # Make classes pickled in jobs unpicklable in main
    import sys
    if '__job__' not in sys.modules and '__main__' in sys.modules:
        sys.modules['__job__'] = sys.modules['__main__']



# Load normally ==================================================


# Magic pickling of methods =======================================

# Based on an idea by Steven Bethard, http://bytes.com/topic/python/answers/552476-why-cant-you-pickle-instancemethods

import copyreg
import types

def _pickle_method(method):
    assert type(method.__self__.__class__) != type, "Can't pickle instance methods of old-style classes. Use new-style classes!"

    obj = method.__self__
    func = method.__func__
    func_name = method.__func__.__name__

    cls = method.__self__.__class__
    for func_class in cls.mro():
        if func_name in func_class.__dict__ and func_class.__dict__[func_name] is func:
            break
    else:
        assert False, "Couln't find correct class for method "+func_name

    return _unpickle_method, (func_class, func_name, obj, cls)

def _unpickle_method(func_class, func_name, obj, cls):
    return func_class.__dict__[func_name].__get__(obj, cls)

copyreg.pickle(types.MethodType, _pickle_method, _unpickle_method)




# =====================================================================

__all__ = """
   coordinator
   remake_needed remake_clear set_abort_make set_do_selection set_done_selection
   future 
   parallel_imap parallel_map parallel_for 
   thread_future thread_for
   Stage process barrier stage stage_function
   make process_make 
   Execute Make
   configure_making run_script run_tool run_toolbox
""".strip().split()

import multiprocessing 
from multiprocessing import managers
import threading, sys, os, signal, atexit, time, base64, socket, warnings, re, marshal, gc
import pickle as pickle

from . import grace, config, selection

class Stage_exception(grace.Error): pass


def chunk(iterable, chunk_size):
    items = [ ]
    for item in iterable:
        items.append(item)
        if len(items) >= chunk_size:
            yield items
            items = [ ]
    if items:
        yield items

def interleave(iterators):
    i = 0
    iterators = list(iterators)
    while iterators:
        i = i%len(iterators)
        try:
            yield next(iterators[i])
            i = i+1
        except StopIteration:
            del iterators[i]


def process_identity():
    return (socket.gethostname(), os.getpid())


def _deprecated(text):
    warnings.warn(text, stacklevel=3)

# Manager/coordinator ===================

def substitute(text, **args):
    return re.sub('|'.join(args), lambda match: args[match.group(0)], text)

def _init_globals():
    global _SERVER,_COORDINATOR,_MANAGER,_AUTHKEY,_COORDINATOR_PROXY
    # The coordinator in the manager-process
    _SERVER = None
    _COORDINATOR = None
    # Connection to manager-process
    _MANAGER = None
    _AUTHKEY = None
    # Local proxy of the coordinator in the manager-process
    _COORDINATOR_PROXY = None

def _run_job(address, authkey, mail_number):
    _init_globals()
    manager(address, authkey, connect=True)
    func, args, kwargs = coordinator().get_mail(mail_number)
    func(*args,**kwargs) 

DEFAULT_JOB_COMMAND = '__command__ &' if os.name == 'posix' else ''
DEFAULT_KILL_COMMAND = 'pkill -f __jobname__' if os.name == 'posix' else ''

_init_globals()

    
class My_coordinator:
    """ LIFO allocation of cores
        - LIFO is generally more memory efficient
        - Behaves as expected when only one core used
        
        Processes are assumed to start owning one core.
        
        Keep track of the number of cores a process has is it's own business.
        
        Maintaining LIFOness makes this is a delicate and subtle dance.
        The implementation of future(...) below is non-obvious.      
    """
    def __init__(self):
        self.lock = threading.RLock()
        self.waiters = [ ]
        self.cores = multiprocessing.cpu_count()
        self.used = 1 #Main process
        
        self.statuses = { }
        
        self.mail = { }
        self.mail_count = 0
        
        self.futures = { }
        self.future_count = 0
        
        self.job_name = 'nesoni_%d_' % os.getpid()
        
        self.job_command = DEFAULT_JOB_COMMAND
        self.kill_command = DEFAULT_KILL_COMMAND

    def set(self, **kwargs):
        for key in kwargs:
            assert key in ('job_command','kill_command','cores')
            setattr(self,key,kwargs[key])
    
    def set_mail(self, value):
        with self.lock:
            number = self.mail_count
            self.mail_count += 1
            self.mail[number] = value
        return number
    
    def get_mail(self, number):
        with self.lock:
            return self.mail.pop(number)

    def new_future(self):
        with self.lock:
            number = self.future_count
            self.futures[number] = [ threading.Event(), None, 1 ]
            self.future_count += 1
            return number
    
    def ref_future(self, number):
        with self.lock:
            assert number in self.futures, 'Future refcounting inconsistency'
            self.futures[number][2] += 1
    
    def deref_future(self, number):
        with self.lock:
            assert number in self.futures, 'Future refcounting inconsistency'
            self.futures[number][2] -= 1
            if self.futures[number][2] <= 0:
                del self.futures[number]
    
    def deliver_future(self, number, value):
        with self.lock:
            if number in self.futures:
                self.futures[number][1] = value
                self.futures[number][0].set()

    def get_future(self, number):
        event = self.futures[number][0]        
        if not event.isSet():
            self.release_core()
            event.wait()
            self.acquire_core()
        
        result = self.futures[number][1]
        self.deref_future(number)
        return result

    def time(self):
        """ A common source of timestamps, if spread over many nodes. """
        return time.time()

    def _update(self):
        with self.lock:
            #Conservative policy: 
            #  Use no more than the given cores.
            #  Prefer biggest first, then earliest first.
            self.waiters.sort(key=lambda item: -item[0])
            i = 0
            while i < len(self.waiters):
                if self.waiters[i][0] + self.used <= self.cores:
                    self.used += self.waiters[i][0]
                    self.waiters[i][1].set()
                    del self.waiters[i]
                else:
                    i = i + 1
            
            #Greedy policy: 
            #  Whenever there are cores free, start something up, 
            #  even if it uses more cores than available.
            #while self.waiters and self.used < self.cores:
            #    self.used += self.waiters[-1][0]
            #    self.waiters[-1][1].set()
            #    del self.waiters[-1]
            
            #Conservative and biggest first policy:
            #  Wait until there are enough cores free to do the largest job.
            #self.waiters.sort(key=lambda item: item[0])
            #while self.waiters and self.used + self.waiters[-1][0] <= self.cores:
            #    self.used += self.waiters[-1][0]
            #    self.waiters[-1][1].set()
            #    del self.waiters[-1]
    
    def set_cores(self, n):
        with self.lock:
            self.cores = n
            self._update()

    def get_cores(self):
        with self.lock:
            return self.cores
    
    def change_cores_used(self, delta):
        """ Advise of use of more or less cores, no delay allowed. """
        with self.lock:
            self.used += delta
            self._update()
    
    def release_core(self):
        self.change_cores_used(-1)

    def trade_cores(self, old, new):
        # If cores being released, allow process to continue,
        # so it can free up memory and quit.
        if new <= old:
            with self.lock:
                self.used = self.used - old + new
                self._update()
            return
        
        with self.lock:
            #assert new <= self.cores, 'Don\'t have %d cores.' % new
            self.used -= old
            event = threading.Event()
            self.waiters.append((new, event))
            self._update()
        event.wait()

    def acquire_core(self):
        self.trade_cores(0,1)

    def set_status(self, identity, value):
        old = self.statuses.get(identity,"")
        if value:
            self.statuses[identity] = value
        elif identity in self.statuses:
            del self.statuses[identity]
        
        if sys.stderr.isatty() and not os.environ.get('NESONI_NOTITLE'):
            items = [ self.statuses[item] for item in sorted(self.statuses,reverse=True) ]
            alloc = 200 / max(1,len(items))
            status = ''
            for item in items:
                if len(item) > alloc:
                    status += item[:alloc]+'> '
                else:
                    status += item + ' '

            #Show in terminal title
            sys.stderr.write('\x1b]2;'+status+'\x07')
            sys.stderr.flush()
        
        return old

    def job(self, func, *args, **kwargs):
        number = self.set_mail((func,args,kwargs))

        if not self.job_command:
            multiprocessing.Process(target=_run_job, args=(_SERVER.address, _SERVER.authkey, number,)).start()
        
        else:
            main = sys.modules['__main__']
            if hasattr(main,'__file__'):
                main_file = main.__file__
            else:
                main_file = None
                        
            address = _SERVER.address
            authkey = _SERVER.authkey
            token = base64.b64encode(repr((
                os.getcwd(),
                sys.path,
                main_file,
                address,
                authkey,
                number
            )).encode()).decode()
            
            command = substitute(self.job_command,
                __command__ = '%s %s %s %s' % (sys.executable, __file__, token, self.job_name),
                __token__ = token,
                __jobname__ = self.job_name
            )
            
            retval = os.system(command)
            assert retval == 0, 'Failed to run job with: '+command
        
    def kill_all(self):
        if self.kill_command:
            command = substitute(self.kill_command, __jobname__ = self.job_name)
            os.system(command)




class My_manager(managers.SyncManager):
    class _Server(managers.SyncManager._Server):
        def serve_forever(self):
            global _SERVER, _COORDINATOR
            _SERVER = self
            _COORDINATOR = My_coordinator()
            
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            managers.SyncManager._Server.serve_forever(self)
    
def _get_coordinator():
    return _COORDINATOR
My_manager.register('get_coordinator', callable=_get_coordinator)


def manager(address=('127.0.0.1',0),authkey=None,connect=False):
    """ Get manager, starting it if necessary.
        Note: the manager should be started before doing anything
              interesting with processes and pipes!
              
              This will happen implicitly if you use
              configure_making, or run_script, or run_tool,
              or run_toolbox. Which you should.
    """

    global _MANAGER, _AUTHKEY
    if _MANAGER is None:
        if authkey is None:
            authkey = base64.b16encode(os.urandom(256))
        _MANAGER = My_manager(address=address, authkey=authkey)
        _AUTHKEY = authkey
        if connect:
            _MANAGER.connect()
        else:
            _MANAGER.start()        
            atexit.register( lambda: coordinator().kill_all() )
    return _MANAGER


def coordinator():
    """ Get a proxy of the coordinator object in the manager process.     
    """
    global _COORDINATOR, _COORDINATOR_PROXY
    if _COORDINATOR is not None: #We are the manager process
        return _COORDINATOR
    if _COORDINATOR_PROXY is None:
        _COORDINATOR_PROXY = manager().get_coordinator()
    return _COORDINATOR_PROXY

# =======================================

class Stage(object):
    """ Use this class to 
        - synchronize with sets of processes that you start.
        - enter context managers without deeply nesting "with"
          statements.
        
        Example:
        
        
        stage = Stage()
        stage.process(my_func1,...)
        stage.process(my_func2,...)
        ...
        
        stage.barrier()   #Wait for all processes started by this stage to finish
        
        Or:
        
        with Stage() as stage:
            stage.process(my_func1,...)
            stage.process(my_func2,...)
        # (barrier as with block exits)

        
        Limitations:
        
        A stage object can not be passed to a different process.
    """
    def __init__(self):
        self.futures = [ ]
        self.contexts = [ ]
        self.entered = False
    
    def __enter__(self):
        assert not self.entered
        self.entered = True
        return self
    
    def __exit__(self, *exc):
        assert self.entered
        self.entered = False
        self.barrier()

    def add(self, future):
        """ Add an existing future to this stage's collection. 
        
            This can be anything that can be called with no arguments.
        """
        if not self.futures:
            LOCAL.stages.add(self)
        self.futures.append(future)
        
    def process(self, func, *args, **kwargs):
        """ Create a new process that will execute func, and
            add it to this stage's collection. """
        item = future(func, *args, **kwargs)
        self.add(item)
        return item

    def thread(self, func, *args, **kwargs):
        """ Create a new thread that will execute func, and
            add it to this stage's collection. """
        item = thread_future(func, *args, **kwargs)
        self.add(item)
        return item

    def enter(self, context):
        """ Enter a context.
            Context will be exited at next barrier. """
        value = context.__enter__()
        self.contexts.append(context)
        return value

    def barrier(self):
        """ Wait for all processes that have been added to this stage
            to finish. 
            
            Leave all contexts that were entered.
            """
        exceptions = [ ]

        if self.futures:
            LOCAL.stages.remove(self)

            while self.futures:
                try:
                    self.futures.pop(0)()
                except Exception as e:
                    if isinstance(e, Stage_exception):
                        exceptions.extend(e.args)
                    else:
                        exceptions.append(e)
            
        while self.contexts:
            try:
                self.contexts.pop(-1).__exit__(None,None,None)
            except Exception as e:
                if isinstance(e, Stage_exception):
                    exceptions.extend(e.args)
                else:
                    exceptions.append(e)
        
        if exceptions:
            raise Stage_exception(*exceptions)




LOCAL = threading.local()
def set_locals():
    LOCAL.abort_make = False
    LOCAL.do_selection = ''
    LOCAL.done_selection = ''
    LOCAL.time = 0 #Note: do not run this code before the year 1970
    LOCAL.stages = set() #Stages with processes in them, so we can warn if they don't have .barrier() called on them
    LOCAL.stage = Stage() #Default stage. Deprecated.
set_locals()

def _check_stages():
    if LOCAL.stages:
        warnings.warn('Exited without calling .barrier() on all Stages.')  
atexit.register(_check_stages)


def remake_needed():
    """ Force all tools to be re-run. """
    LOCAL.time = coordinator().time()

def remake_clear():
    """ Subsequent tools don't depend on previous tools. """
    LOCAL.time = 0

def set_abort_make(value):
    """ If set to true, immediately abort if any tool needs to be run.
    
        Allows checking of what would be run without actually running it.    
    """
    LOCAL.abort_make = value

def set_do_selection(selection):
    LOCAL.do_selection = selection

def set_done_selection(selection):
    LOCAL.done_selection = selection




def _run_future(time,abort_make,do_selection,done_selection, func, args, kwargs, future_number):
    set_locals()
    LOCAL.time = time
    LOCAL.abort_make = abort_make
    LOCAL.do_selection = do_selection
    LOCAL.done_selection = done_selection
    result = None
    exception = None
    try:
        result = func(*args, **kwargs)
        assert not LOCAL.stages, 'Process completed without calling .barrier() on all Stages.'
    except:
        config.report_exception()
        exception = sys.exc_info()[1]
    
    coordinator().deliver_future(future_number, (LOCAL.time, exception, result))

    #Give core back to parent
    coordinator().release_core()


class Future_reference(object):
    """ Object to retrieve a future from coordinator process.
        Coordinator keeps a reference count:
        - future created with refcount 1
        - pickling the object increases refcount
        - deleting the object decreases refcount
        - retrieving the future decreases refcount, prevents further shenanigans
        
        Assumption: a pickled Future_reference is unpickled exactly once
    """

    def __init__(self, number):
        self.number = number
        self.retrieved = False
        self.time = None
        self.exception = None
        self.result = None
        
        self.lock = threading.Lock()
    
    def __call__(self):
        with self.lock:
            if not self.retrieved:
                self.time, self.exception, self.result = coordinator().get_future(self.number)
                self.retrieved = True
            
            LOCAL.time = max(LOCAL.time, self.time)
            if self.exception is not None:
                raise self.exception
            return self.result

    def __del__(self):
        if not self.retrieved:
            coordinator().deref_future(self.number)
    
    def __getstate__(self):
        with self.lock:
            if not self.retrieved:
                coordinator().ref_future(self.number)
            result = dict(self.__dict__)
            del result['lock']
            return result
    
    def __setstate__(self, data):
        self.lock = threading.Lock()
        for key in data:
            setattr(self,key,data[key])


def future(func, *args, **kwargs):
    """
    Underlying synchronization mechanism.
    
    Create a new process to run a function.
    
    The return value can be later called with
    no arguments to get the result of the function. 
    This has the side effect of synchronizing with 
    the process that was created, and this process
    being "infected" with the need to remake if 
    necessary.
    
    The returned value can be passed as a parameter
    to other futures, and sent through connections.
    """

    future_number = coordinator().new_future()

    #Give core to process we start
    p = coordinator().job(_run_future,LOCAL.time,LOCAL.abort_make,LOCAL.do_selection,LOCAL.done_selection,func,args,kwargs,future_number)
    
    #Get another for ourselves
    coordinator().acquire_core()
    
    return Future_reference(future_number)


def thread_future(func, *args, **kwargs):
    """
    Lightweight version of future, using threads.
    
    Can not be passed between processes.
    """
    storage = [ ]
    
    def run_future(time,abort_make,do_selection,done_selection):
        set_locals()
        LOCAL.time = time
        LOCAL.abort_make = abort_make
        LOCAL.do_selection = do_selection
        LOCAL.done_selection = done_selection
        result = None
        exception = None
        try:
            result = func(*args, **kwargs)
            LOCAL.stage.barrier()
            assert not LOCAL.stages, 'Process completed without calling .barrier() on all Stages.'
        except:
            config.report_exception()
            exception = sys.exc_info()[1]

        storage.extend([ LOCAL.time, exception, result ])

    thread = threading.Thread(target=run_future,args=(LOCAL.time,LOCAL.abort_make,LOCAL.do_selection,LOCAL.done_selection))
    thread.start()  
    def get_thread_future():
        thread.join()
        [time, exception, value] = storage
        LOCAL.time = max(LOCAL.time, time)
        if exception is not None:
            raise exception
        return value
    return get_thread_future
    

def _parallel_imap_task(filename, func, item, args, kwargs):
    result = func(item, *args, **kwargs)
    with open(filename,'wb') as f:
        marshal.dump(result, f)

def parallel_imap(func, iterable, *args, **kwargs):
    from . import workspace
    with workspace.tempspace() as temp:
        futures = [ ]
        for i, item in enumerate(iterable):
            futures.append(future(_parallel_imap_task,temp/str(i),func,item,args,kwargs))
        for i, item in enumerate(futures):
            item()
            with open(temp/str(i),'rb') as f:
                yield marshal.load(f)

#def parallel_imap(func,iterable, future=future):
#    # This may be memory inefficient for long iterators
#    return (item() for item in [ future(func,item2) for item2 in iterable ])

def parallel_map(func, iterable, *args, **kwargs):
    return list(parallel_imap(func, iterable, *args, **kwargs))


def parallel_for(iterable):
    """ Execute a "for loop" in parallel.
    """
    def doit(func):
        for item in [ future(func, item) for item in iterable ]:
            pass
    return doit

def thread_for(iterable):
    """ Execute a "for loop" in parallel.
        Use this as a function decorator. 
    """
    def doit(func):
        for item in [ thread_future(func, item) for item in iterable ]:
            item()
    return doit
    




def process(func, *args, **kwargs):
    """ Deprecated. Use Stage objects.
    
        Start a new process. 
    """
    _deprecated('process(...) is deprecated. Use Stage objects.')
    return LOCAL.stage.process(func, *args, **kwargs)

#def thread(func, *args, **kwargs):
#    LOCAL.parallels.append(future(func, *args, local=True, **kwargs))
#    return func

def barrier():
    """ Deprecated. Use Stage objects.
    
        Wait for all processes started by this process to finish.    
        (Except for any processes explicitly put in a stage.)
    """
    _deprecated('barrier() is deprecated. Use Stage objects.')
    LOCAL.stage.barrier()


def stage(func, *args, **kwargs):
    """ Deprecated. Use Stage objects.
    
        Call a function, and wait for all processes started by it to finish    
        Can be used as a function decorator, but probably shouldn't be.
    """
    _deprecated('stage(...) is deprecated. Use Stage objects.')
    old = LOCAL.stage
    LOCAL.stage = Stage()
    result = None
    try:
        result = func(*args, **kwargs)
    finally:
        barrier()    
        LOCAL.stage = old
    return result


def stage_function(func):
    """ Deprecated. Use Stage objects.
    
        Ensure processes started by a function or method complete
        before the function returns.
    """
    _deprecated('@stage_function is deprecated. Use Stage objects.')
    def inner(*args, **kwargs):
        return stage(func, *args, **kwargs)
    return inner


    




# Make ===============================================

def _get_timestamp(action):
    """ Look for ident() in .state subdirectory of current directory.
        If pickled value matches return the timestamp.
    """
    if selection.matches(LOCAL.do_selection, [action.shell_name()]):
        return None
    
    try:
        for filename in [
            action.state_filename(),
            os.path.join('.state', grace.filesystem_friendly_name(action.ident())), #Old location of state files
        ]:
            if os.path.exists(filename):
                with open(filename,'rb') as f:
                    old = pickle.load(f)
                
                if action != old:
                    return None
                
                if not hasattr(old, 'timestamp'):
                    return None                        
                
                if hasattr(old, 'timestamp_for') and old.timestamp_for != filename:
                    return None
                
                return old.timestamp
                
                #for parameter in self.parameters:
                #    if parameter.get(self) != parameter.get(old):
                #        print >> sys.stderr, parameter.name, parameter.get(old), '->', parameter.get(self)            
    except Exception as error:
        import traceback
        traceback.print_exc()
        print('Error making %s, re-running: %s' % (action.ident(), error), file=sys.stderr)

    return None
    
def _run_and_save_state(action, timestamp):
    #filename = os.path.join('.state', grace.filesystem_friendly_name(action.ident()))
    #temp_filename = os.path.join('.state', 'temp-' + grace.filesystem_friendly_name(action.ident()))
    filename = action.state_filename()
    temp_filename = filename + '.temp'
    
    if os.path.exists(filename):
        os.unlink(filename)
    
    if selection.matches(LOCAL.done_selection, [action.shell_name()]):
        result = None
    else:
        result = action.run()
    
    LOCAL.time = max(LOCAL.time, timestamp)
    action.timestamp = timestamp
    action.timestamp_for = filename 
    action.timestamp_cwd = os.getcwd()
    #timestamp_for is used to ensure the action is being 
    # run from the same (relative) current directory as previously

    dirname = os.path.dirname(filename)
    if dirname and not os.path.exists(dirname):
        os.mkdir(dirname)

    with open(temp_filename,'wb') as f:
        pickle.dump(action, f)
    os.rename(temp_filename, filename)
    
    return result

def _make_inner(action):
    timestamp = coordinator().time()
    assert timestamp > LOCAL.time, 'Time running in reverse.'
    
    gc.collect()
    
    cores = action.cores_required()
    if cores > 1:
        coordinator().trade_cores(1, cores)
    try:        
        config.write_colored_text(sys.stderr, '\n'+action.describe()+'\n')
        
        if LOCAL.abort_make and not selection.matches(LOCAL.do_selection, [action.shell_name()]):
            raise grace.Error('%s would be run. Stopping here.' % action.ident())
        
        old_status = grace.status(action.shell_name())
        try:
            _run_and_save_state(action, timestamp)
        finally:
            grace.status(old_status)
    finally:
        gc.collect()
        
        if cores > 1:
            coordinator().trade_cores(cores, 1)



def make(action):
    """ Run a tool (an instance of a subclass of nesoni.config.Action) if necessary.
    """
    timestamp = _get_timestamp(action)    
    if timestamp is not None and timestamp >= LOCAL.time:
        LOCAL.time = timestamp
    else:
        _make_inner(action)


def _time_advancer(timestamp):
    def time_advancer():
        LOCAL.time = max(LOCAL.time, timestamp)
    return time_advancer

def process_make(action, stage=None):
    """ This is just a more efficient version of stage.process(make, <action>)
    """
    if stage is None:
        stage = LOCAL.stage
    timestamp = _get_timestamp(action)    
    if timestamp is not None and timestamp >= LOCAL.time:
        stage.add(_time_advancer(timestamp))
    else:
        stage.process(_make_inner,action)



#def generate(func, *args, **kwargs):
#    """ Run an iterator in a separate process.
#    
#        For example:
#        
#          for item in thing_maker(param):
#              ...
#            
#        could be rewritten:
#        
#          for item in generate(thing_maker, param):
#              ...    
#    """
#    #return iter(func(*args,**kwargs))
#    
#    receiver, sender = multiprocessing.Pipe(False)
#    
#    def sender_func():
#        try:
#            for items in chunk(func(*args,**kwargs), 1<<8):
#                sender.send(items)
#        except:
#            sender.send('error')
#            import traceback
#            print >> sys.stderr, traceback.format_exc()            
#        else:    
#            sender.send(None)
#        finally:
#            coordinator().change_cores_used(-1)
#        sender.close()
#    
#    coordinator().change_cores_used(1)
#    process = start_process(sender_func)
#    
#    def generator():
#        while True:
#            data = receiver.recv()
#            if data is None: break
#            if data == 'error': raise Child_exception()
#            for item in data:
#                yield item
#        process.join()
#        receiver.close()
#    
#    return generator()




# @config.help("""\
# Execute a shell command, optionally reading stdin from a file, \
# and optionally sending stdout to a file.
# """)
# @config.Int_flag('cores','Advise how many cores the command will use.', 
#     affects_output=False)
# @config.String_flag('prefix','Location of state and log files.')
# @config.Main_section('command','Command to execute', allow_flags=True, empty_is_ok=False)
# @config.Section('execution_options',
#     'Extra options to add to start of command, eg to set the number of cores to use. '
#     'These should not affect the output, and changing them will not cause the command to be re-run.', 
#     affects_output=False)
# class Execute(config.Action_filter):
#     cores = 1
#     command = [ ]
#     execution_options = [ ]
#     prefix = None
# 
# 
#     def log_filename(self):
#         if self.prefix is None: 
#             return None
#         return self.prefix + '_log.txt'
# 
#     def state_filename(self):
#         if self.prefix is None: 
#             return super(Execute,self).state_filename()
#         return self.prefix + '.state'
#     
# 
#     def cores_required(self):
#         return self.cores
#     
#     def ident(self):
#         if self.output:
#             return self.shell_name()+'--'+self.output
#         else:
#             return self.shell_name()+'--'+' '.join(self.command)
#     
#     def run(self):
#         from nesoni import io
#         
#         assert self.command, 'Nothing to execute!'
#         
#         print self.ident()
#         
#         f_in = self.begin_input()
#         f_out = self.begin_output()
#         try:
#             io.execute(self.command[:1] + self.execution_options + self.command[1:], 
#                        stdin=f_in, stdout=f_out)
#         finally:
#             self.end_output(f_out)
#             self.end_input(f_in)



@config.Int_flag('make_cores', 'Approximate number of cores to use.')
@config.String_flag('make_do', 
    'Force this selection of tool names to be recomputed.\n'
    'Examples: --make-do all  --make-do analyse-samples/analyse-sample')
@config.String_flag('make_done', 
    'Mark this selection of tool names as done without recomputing them, '
    'if they would be recomputed.')
@config.Bool_flag('make_show', 'Show the first actions that would be made (other than those specified by "--make-do"), then abort.')
@config.String_flag('make_address', 'IP address of the network interface you want the job manager to listen to.')
@config.String_flag('make_job', 
    'Command to launch a new python. Should either contain __command__, which will be subtituted '
    'with the full shell command, including the job name, or __token__ and __jobname__, '
    'which should be used in something like "python -m nesoni.legion __token__ __jobname__".'
)
@config.String_flag('make_kill', 
    'Command to kill all processes identified by __jobname__.'
)
class Make(config.Action):
    make_cores = int(os.environ.get('NESONI_CORES','0')) or multiprocessing.cpu_count()
    make_show = False
    make_do = ''
    make_done = ''
    
    make_address = os.environ.get('NESONI_ADDRESS') or socket.gethostbyname(socket.gethostname())
    make_job = os.environ.get('NESONI_JOB') or DEFAULT_JOB_COMMAND
    make_kill = os.environ.get('NESONI_KILL') or DEFAULT_KILL_COMMAND
    
    def _before_run(self):
        manager((self.make_address, 0))
        coordinator().set(
            job_command = self.make_job,
            kill_command = self.make_kill,
            cores = self.make_cores,
        )
        set_abort_make(self.make_show)
        set_do_selection(self.make_do)
        set_done_selection(self.make_done)

    def run(self):
        pass


@config.help("""\
Execute a script.
""")
@config.Hidden('function', 'Function to execute.')
@config.Main_section('script_parameters', 'Script parameters.', allow_flags=True)
class Make_script(Make):
    function = None
    script_parameters = [ ]

    def run(self):
        self.function(*self.script_parameters)


def configure_making(args):
    """ Configure make options, return remaining arguments.
    
        Exits program if options are invalid.
    """
    
    try:
        maker = Make()
        leftovers = maker.parse_partial(args)
        if leftovers != args:
            config.write_colored_text(sys.stderr, '\n'+maker.describe('Make options')+'\n')        
        maker.run()    
        return leftovers
    except:
        config.report_exception()
        sys.exit(1)
    

def run_script(function):
    """ Run a workflow script. Various command line flags are parsed,
        then any remaining command line parameters are passed to the 
        function. 
        
        Intended usage:

    
        from nesoni import *
    
        def my_script():
            ...
        
        if __name__ == '__main__':
            run_script(my_script)
    """
    maker = Make_script(function=function)    
    config.shell_run(maker, sys.argv[1:], sys.executable + ' ' + sys.argv[0])


def run_tool(action_class):
    """
    Provide a command line interface for an Action.
    """
    args = configure_making(sys.argv[1:])
    config.shell_run(action_class(), args, sys.argv[0])


def run_toolbox(action_classes, script_name='', show_make_flags=True):
    """
    Provide a command line interface for a list of Actions.
    
    Note:    
    strings included in the action_classes list will be printed 
    as help text, for example to display section headings.
    """
    args = configure_making(sys.argv[1:])
    
    commands = { }

    for item in action_classes:
        if isinstance(item, str):
            continue
        name = item.shell_name()
        commands[ name ] = item

    if args == [ '--help-make' ]:
        help = [ '\n' ]
        help.append('\nMake options:\n'+Make().describe('', show_help=True, escape_newlines=False)+'\n')

        config.write_colored_text(sys.stdout, ''.join(help)+'\n\n')
        sys.exit(1)

    if not args or args == ['-h'] or args == ['--help']:
        help = [ '\n' ]
        
        for item in action_classes:
            if isinstance(item, str):
                help.append(config.wrap(item, 70) + '\n\n')
                continue
            name = item.shell_name()
            help.append('    %s\n' % config.colored(1,name+':'))
            help.append(config.color_as_comment(config.wrap(item.help_short, 70, '        ')) + '\n\n')

        if show_make_flags:
            #help.append('\nMake options:\n'+Make().describe('', show_help=True, escape_newlines=False)+'\n')
            help.append('\nFor workflow make options type "%s --help-make".\n' % script_name)

        config.write_colored_text(sys.stdout, ''.join(help))
        sys.exit(1)
        
    try:        
        command, args = args[0], args[1:]
        
        mangled_command = command.lower().rstrip(':')
        if mangled_command not in commands:
            raise grace.Error("Don't know how to "+command)        
    except:
        config.report_exception()
        sys.exit(1)

    config.shell_run(commands[mangled_command](), args, (script_name+' ' if script_name else '') + mangled_command+':')
    

