
import os, cPickle, json, tempfile, contextlib, shutil

class Workspace(object):
    """ Directory containing pickled objects, etc 
    
        Properties:
            name  - directory base name
            param - a dictionary of parameters stored in a file
                    called "parameters".
                    Note: update this with .update_param(...)
        
        Operator overloading:
            workspace / 'filename'
                  - returns the full path of a file called 'filename'
                    in the workspace directory.
                    (Bless me Guido, for I have sinned.)
    
    """

    def __init__(self, working_dir, must_exist=False):
        self.working_dir = os.path.normpath(working_dir)
        if not os.path.exists(self.working_dir):
            assert not must_exist, working_dir + ' does not exist'
            os.mkdir(self.working_dir)
        else:
            assert os.path.isdir(self.working_dir), self.working_dir + ' exists and is not a directory'
        
        self.name = os.path.split(os.path.abspath(working_dir))[1]

    @property
    def param(self):
        if self.object_exists('parameters'):
            return self.get_object('parameters', plain_text=True)
        else:
            return { }

    def update_param(self, remove=[], **updates):
        param = self.param
        for item in remove:
            if item in self.param:
                del param[item]
        param.update(updates)
        self.set_object(param, 'parameters', plain_text=True)

    def open(self, path, mode):
        return open(self.object_filename(path), mode)
    
    def object_exists(self, path):
        return os.path.exists(self.object_filename(path))

    def get_object(self, path, plain_text=False):
        from nesoni import io
        f = io.open_possibly_compressed_file(self._object_filename(path))
        if plain_text:
            data = f.read()
            try:
                result = json.loads(data)
            except ValueError: #Older versions used repr instead of json.dump
                result = eval(data)
        else:
            result = cPickle.load(f)
        f.close()
        return result

    def set_object(self, obj, path, plain_text=False):
        from nesoni import io
        temp_filename = self._object_filename('tempfile')
        if plain_text:
            f = open(temp_filename, 'wb')
            json.dump(obj, f)
            f.close()
        else:
            f = io.Pipe_writer(temp_filename, ['gzip'])
            cPickle.dump(obj, f, 2)
            f.close()
        
        os.rename(temp_filename, self._object_filename(path))

    def path_as_relative_path(self, path):        
        #Breaks thumbnails if outputing to absolute output dir
        #if os.path.isabs(path):
        #    return path

        #assert os.path.sep == '/' #Someone else can work this out on windows and mac   
        sep = os.path.sep
        me = os.path.abspath(self.working_dir).strip(sep).split(sep)
        it = os.path.abspath(path).strip(sep).split(sep)
        n_same = 0
        while n_same < len(me) and n_same < len(it) and me[n_same] == it[n_same]:
            n_same += 1        
        return os.path.normpath( sep.join( ['..']*(len(me)-n_same) + it[n_same:] ) )

    def relative_path_as_path(self, path):
        if os.path.isabs(path):
            return path
        
        return os.path.normpath(os.path.join(self.working_dir,path))    
    object_filename = relative_path_as_path
    _object_filename = object_filename
    
    # A single step down the path of darkness, what's the worst that can happen?
    def __div__(self, path):
        if not isinstance(path, basestring):
            path = os.path.join(*path)
        return self.relative_path_as_path(path)


@contextlib.contextmanager
def tempspace(dir=None):
    """ Use this in a "with" statement to create a temporary workspace. 
        
        Example:
        
        with workspace.tempspace() as temp:
            with open(temp/'hello.c','wb') as f:
                f.write('#include <stdio.h>\nint main() { printf("Hello world\\n"); }')
            os.system('cd '+temp.working_dir+' && gcc hello.c && ./a.out')
    """
    path = tempfile.mkdtemp(dir=dir)
    try:
        yield Workspace(path, must_exist=True)
    finally:
        shutil.rmtree(path)



