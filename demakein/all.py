
import demakein

import nesoni
from nesoni import config

@config.help("""\
Design and make all instruments, in a variety of sizes.
""","""\
Note that I use the terms "soprano", "alto", "tenor", and "bass" to \
refer to the sizes of instruments. Flutes and shawms I name this way are actually \
an octave above the singing voices of the same name.
""")
@config.Bool_flag('panpipes', 'Do panpipes.')
@config.Bool_flag('flutes', 'Do flutes.')
@config.Bool_flag('whistles', 'Do whistles.')
@config.Bool_flag('shawms', 'Do shawms.')
@config.String_flag('version', 'version code, for file names')
class All(config.Action_with_output_dir):
    panpipes = True
    flutes = True
    whistles = True
    shawms = True
    version = 'v'+demakein.VERSION.lstrip('0.')
    
    def _do_flute(self, model_name, model_code, size_name, size_code, designer, transpose):
        workspace = self.get_workspace()
        outdir = workspace / (model_name+'-'+size_name)

        designer(
            outdir,
            transpose=transpose
            ).make()
        
        demakein.Make_flute(
            outdir,
            prefix = model_code+size_code+'-'+self.version+'-',
            decorate=True,
            ).make()

    def _do_shawm(self, model_name, model_code, size_name, size_code, designer, transpose, bore):
        workspace = self.get_workspace()
        outdir = workspace / (model_name+'-'+size_name)
    
        designer(
            outdir,
            transpose=transpose,
            bore=bore,
            ).make()

        demakein.Make_shawm(
            outdir,
            prefix=model_code+size_code+'-'+self.version+'-',
            decorate=True,
            ).make()
    
    def _do_folk_whistle(self, model_name, model_code, size_name, size_code, transpose):
        workspace = self.get_workspace()
        outdir = workspace / (model_name+'-'+size_name)
        
        demakein.Design_folk_whistle(
            outdir,
            transpose=transpose,
            ).make()
        
        demakein.Make_whistle(
            outdir,
            prefix=model_code+size_code+'-'+self.version+'-',
            ).make()
    
    def run(self):
        workspace = self.get_workspace()
        
        stage = nesoni.Stage()
        
        if self.panpipes:
            if self.make:
                demakein.Make_panpipe(
                    workspace/'panpipe'
                    ).process_make(stage)
        
        if self.flutes:
            for model_name, model_code, designer in [
                    ('folk-flute-straight', 'FFS', demakein.Design_straight_folk_flute),
                    ('folk-flute-tapered',  'FFT', demakein.Design_tapered_folk_flute),
                    ('pflute-straight',     'PFS', demakein.Design_straight_pflute),
                    ('pflute-tapered',      'PFT', demakein.Design_tapered_pflute),
                    ]:
                for size_name, size_code, transpose in [
                        ('tenor', 't', 0),
                        ('alto', 'a', 5),
                        ('soprano', 's', 12),
                        ]:
                    stage.process(self._do_flute,model_name,model_code,size_name,size_code,designer,transpose)

        if self.whistles:
            for model_name, model_code in [
                    ('folk-whistle', 'FW'),
                    ]:
                for size_name, size_code, transpose in [
                        ('tenor', 't', 0),
                        ('alto', 'a', 5),
                        ('soprano', 's', 12),
                        ('sopranino', 'ss', 17),
                        ]:
                    stage.process(self._do_folk_whistle,model_name,model_code,size_name,size_code,transpose)

        if self.shawms:
            for model_name, model_code, designer in [
                 ('shawm', 'SH', demakein.Design_shawm),
                 ('folk-shawm', 'FSH', demakein.Design_folk_shawm),
                 ]:
                 for size_name, size_code, transpose, bore in [
                         ('4mm-alto', '4a', 5, 4.0),
                         ('4mm-tenor', '4t', 0, 4.0),
                         ('6mm-tenor', '6t', 0, 6.0),
                         ('6mm-bass', '6b', -7, 6.0),
                         ]:
                     stage.process(self._do_shawm,model_name,model_code,size_name,size_code,designer,transpose,bore)

        stage.barrier()


