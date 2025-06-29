
"""

Some helper facilities, originally from nesoni.

"""

import sys

from .config import Error, filesystem_friendly_name

class Log:
    def __init__(self):
        self.text = [ ]
        self.f = None
    
    def attach(self, f):
        assert not self.f
        self.f = f
        self.f.write(''.join(self.text))
        self.f.flush()
    
    def close(self):
        if self.f is not None:
            self.f.close()
            self.f = None
    
    def log(self, text):
        sys.stderr.write(text)
        self.quietly_log(text)
    
    def quietly_log(self, text):        
        self.text.append(text)
        if self.f:
           self.f.write(text)
           self.f.flush()


def status(string):
    """ Display a status string. """
    from . import legion
    return legion.coordinator().set_status( legion.process_identity(), string )



