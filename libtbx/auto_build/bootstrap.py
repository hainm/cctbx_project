# -*- python -*-
import os
import sys
import subprocess
import optparse
import getpass

# Mock commands to run standalone, without buildbot.
class ShellCommand(object):
  def __init__(self, **kwargs):
    self.kwargs = kwargs    

  def get_command(self):
    return self.kwargs['command']
  
  def get_workdir(self):
    return self.kwargs.get('workdir', 'build')

  def run(self):
    command = self.get_command()
    workdir = self.get_workdir()
    print "===== Running in %s:"%workdir, " ".join(command)
    if workdir:
      try:
        os.makedirs(workdir)
      except Exception, e:
        pass
    p = subprocess.Popen(
      args=command,
      cwd=workdir,
      stdout=sys.stdout,
      stderr=sys.stderr
    )
    p.wait()
    if p.returncode != 0 and self.kwargs.get('haltOnFailure'):
      raise RuntimeError, "Process failed with return code %s"%(p.returncode)
  
class SVN(ShellCommand):
  def get_command(self):
    return ['svn', 'co', self.kwargs['repourl'], self.kwargs['codebase']]
    
  def get_workdir(self):
    return 'modules'

# Import Buildbot if available.
try:
  import buildbot.steps.shell
  import buildbot.steps.source.svn
  import buildbot.process.factory
  import buildbot.config
except ImportError:
  pass

##### Codebases #####
# rsync'd packages.
HOT = {
  'phaser_regression':  '%(cciuser)s@cci.lbl.gov:/net/cci/auto_build/repositories/phaser_regression',
  'phaser':             '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/phaser',
  'ccp4io_adaptbx':     '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/ccp4io_adaptbx',
  'annlib_adaptbx':     '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/annlib_adaptbx',
  'tntbx':              '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/tntbx',
  'ccp4io':             '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/ccp4io',
  'clipper':            '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/clipper',
  'docutils':           '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/docutils',
  # Duke
  # 'reduce':             '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/reduce',
  # 'probe':              '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/probe',
  # 'king':               '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/king',
  # 'suitename':          '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/suitename',
  # tar.gz
  'scons':              '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/hot_test/scons',
  'boost':              '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/hot_test/boost',
  'annlib':             '%(cciuser)s@cci.lbl.gov:/net/boa/scratch1/auto_build/repositories/hot_test/annlib',
}

# SVN packages.
CODEBASES = {
  # CCTBX
  'cctbx_project':      'svn://svn.code.sf.net/p/cctbx/code/trunk',
  'cbflib':             'svn://svn.code.sf.net/p/cbflib/code-0/trunk/CBFlib_bleeding_edge',
  # PHENIX:
  'Plex':               'svn+ssh://%(cciuser)s@cci.lbl.gov/Plex/trunk',
  'PyQuante':           'svn+ssh://%(cciuser)s@cci.lbl.gov/PyQuante/trunk',
  'chem_data':          'svn+ssh://%(cciuser)s@cci.lbl.gov/chem_data/trunk',
  'elbow':              'svn+ssh://%(cciuser)s@cci.lbl.gov/elbow/trunk',
  'ksdssp':             'svn+ssh://%(cciuser)s@cci.lbl.gov/ksdssp/trunk',
  'pex':                'svn+ssh://%(cciuser)s@cci.lbl.gov/pex/trunk',
  'phenix':             'svn+ssh://%(cciuser)s@cci.lbl.gov/phenix/trunk',
  'phenix_html':        'svn+ssh://%(cciuser)s@cci.lbl.gov/phenix_html/trunk',
  'phenix_examples':    'svn+ssh://%(cciuser)s@cci.lbl.gov/phenix_examples/trunk',
  'phenix_regression':  'svn+ssh://%(cciuser)s@cci.lbl.gov/phenix_regression/trunk',
  'pulchra':            'svn+ssh://%(cciuser)s@cci.lbl.gov/pulchra/trunk',
  'solve_resolve':      'svn+ssh://%(cciuser)s@cci.lbl.gov/solve_resolve/trunk',
  'reel':               'svn+ssh://%(cciuser)s@cci.lbl.gov/reel/trunk',
  # LABELIT
  'labelit':            'svn+ssh://%(cciuser)s@cci.lbl.gov/labelit/trunk',
  'labelit_regression': 'svn+ssh://%(cciuser)s@cci.lbl.gov/labelit_regression/trunk',
  # DIALS
  'dials':              'https://svn.code.sf.net/p/dials/code/trunk',
  'dials_regression':   'svn+ssh://%(cciuser)s@cci.lbl.gov/dials_regression/trunk',
  # XFEL
  'xfel_regression':    'svn+ssh://%(cciuser)s@cci.lbl.gov/xfel_regression/trunk',
  # Not sure about these:
  'gui_resources':      'svn+ssh://%(cciuser)s@cci.lbl.gov/gui_resources/trunk',
  'opt_resources':      'svn+ssh://%(cciuser)s@cci.lbl.gov/opt_resources/trunk',
  'muscle':             'svn+ssh://%(cciuser)s@cci.lbl.gov/muscle/trunk',
  # Dev, debugging
  'phenix_dev':         'svn+ssh://%(cciuser)s@cci.lbl.gov/phenix_dev/trunk',
  'cxi_xdr_xes':        'svn+ssh://%(cciuser)s@cci.lbl.gov/cxi_xdr_xes/trunk',
  # Duke
  'reduce':            'https://quiddity.biochem.duke.edu/svn/reduce/trunk',
  'probe':             'https://quiddity.biochem.duke.edu/svn/probe/trunk',
  'king':              'https://quiddity.biochem.duke.edu/svn/phenix/king',
  'suitename':         'https://quiddity.biochem.duke.edu/svn/suitename',
}
  
class ModuleManager(object):
  def get_hot(self, codebase, cciuser=None):
    cciuser = cciuser or getpass.getuser()
    return self.HOT[codebase]%{'cciuser':cciuser}

  def get_codebase(self, codebase, cciuser=None):
    return self.CODEBASES[codebase]%{'cciuser':cciuser}

  def get_codebases(self, cciuser=None):
    return dict((k,v%{'cciuser':cciuser}) for k,v in self.CODEBASES.items())

###################################
##### Base Configuration      #####
###################################

class CCIBuilder(object):
  """Create buildbot configurations for CCI and CCTBX-like software."""
  # Base packages
  BASE_PACKAGES = 'all'
  # Checkout these codebases
  CODEBASES = ['cctbx_project']
  CODEBASES_EXTRA = []
  # Copy these sources from cci.lbl.gov
  HOT = []
  HOT_EXTRA = []
  # Configure for these cctbx packages
  LIBTBX = ['cctbx']
  LIBTBX_EXTRA = []
  
  def __init__(self, 
    category=None, 
    platform=None, 
    sep=None, 
    python_system=None, 
    python_base=None, 
    cleanup=False,
    checkout=True,
    base=True, 
    build=True, 
    install=True, 
    tests=True, 
    distribute=False,
    buildbot=True,
    cciuser=None
      ):
    """Create and add all the steps."""
    self.buildbot = buildbot
    self.cciuser = cciuser or getpass.getuser()
    self.steps = []
    self.category = category
    self.platform = platform
    self.name = '%s-%s'%(self.category, self.platform)
    # Windows convenience hack.
    if 'windows' in self.platform:
      base = False
      sep = sep or '\\'
      python_system = python_system or ['python']
      python_base = python_base or ['..', 'base', 'Python', 'python.exe']    
    # Platform configuration.
    self.sep = sep or os.sep
    self.python_system = self.opjoin(*(python_system or ['python']))
    self.python_base = self.opjoin(*(python_base or ['..', 'base', 'bin', 'python']))
    
    # Cleanup
    if cleanup:      
      self.cleanup(['tests', 'docs', 'tmp', 'build'])
    else:
      self.cleanup(['tests', 'docs', 'tmp'])

    # Add sources
    if checkout:
      map(self.add_hot, self.get_hot())
      map(self.add_codebase, self.get_codebases())

    # Build base packages
    if base:
      self.add_build_base()

    # Configure, make
    if build:
      self.add_configure()
      self.add_make()
    
    # Install
    if install:
      self.add_install()

    # Tests, tests
    if tests:
      self.add_tests()
  
    # Distribute
    if distribute:
      self.add_distribute()

  def cmd(self, **kwargs):
    # Convenience for ShellCommand
    kwargs['haltOnFailure'] = kwargs.pop('haltOnFailure', True)
    kwargs['description'] = kwargs.get('description') or kwargs.get('name')
    kwargs['timeout'] = 60*60*2 # 2 hours
    if self.buildbot:
      return buildbot.steps.shell.ShellCommand(**kwargs)
    else:
      return ShellCommand(**kwargs)  
  
  def svn(self, **kwargs):
    if self.buildbot:
      return buildbot.steps.source.svn.SVN(**kwargs)
    else:
      return SVN(**kwargs)
  
  def run(self):
    for i in self.steps:
      i.run()

  def opjoin(self, *args):
    return self.sep.join(args)
  
  def get_codebases(self):
    return self.CODEBASES + self.CODEBASES_EXTRA
    
  def get_hot(self):
    return self.HOT + self.HOT_EXTRA
    
  def get_libtbx_configure(self):
    return self.LIBTBX + self.LIBTBX_EXTRA
  
  def get_changesources(self):
    return dict(
      (k, dict(repository=CODEBASES[k]%{'cciuser':self.cciuser}, branch='default', revision=None)) 
      for k in self.get_codebases()
      )
    
  def get_buildconfig(self):
    # The BuildConfig factory
    factory = buildbot.process.factory.BuildFactory(self.steps)
    # Name is category-platform
    return buildbot.config.BuilderConfig(
      category=self.category, 
      name=self.name, 
      slavenames=[self.platform], 
      factory=factory
    )
  
  def cleanup(self, dirs=None):
    dirs = dirs or []  
    self.add_step(self.cmd(
      name='cleanup',
      command=['rm', '-rf'] + dirs,
      workdir='.'
    ))

  def add_step(self, step):
    """Add a step."""
    self.steps.append(step)
    
  def add_codebase(self, codebase):
    self.add_step(self.svn(
        repourl=CODEBASES[codebase]%{'cciuser':self.cciuser},
        codebase=codebase,
        mode='incremental',
        workdir=self.opjoin('modules', codebase)
    ))

  def add_hot(self, package):
    """Add packages not in source control."""
    # rsync the hot packages.
    self.add_step(self.cmd(
      name='hot %s'%package, 
      command=[
        'rsync', 
        '-aL', 
        HOT[package]%{'cciuser':self.cciuser},
        '.'
      ], 
      workdir='modules'
    ))
    # If it's a tarball, unzip it.
    if package.endswith('.gz'):
      self.add_step(self.cmd(
        name='hot %s untar'%package, 
        command=['tar', '-xvzf', package], 
        workdir='modules'
      ))
    
  def add_command(self, command, name=None, workdir=None, args=None, **kwargs):
    # Relative path to workdir.
    workdir = workdir or ['build']
    dots = [".."]*len(workdir)
    dots.extend(['build', 'bin', command])    
    self.add_step(self.cmd(
      name=name or command, 
      command=[self.opjoin(*dots)] + (args or []),
      workdir=self.opjoin(*workdir),
      **kwargs
    ))
    
  def add_test_command(self, command, name=None, workdir=None, args=None, **kwargs):
    self.add_command(
      command, 
      name='test %s'%command, 
      workdir=(workdir or ['tests', command]),
      haltOnFailure=False,
      **kwargs
    )
  
  def add_test_parallel(self, module=None):
    self.add_command(
      'libtbx.run_tests_parallel',
      name='test %s'%module,
      workdir=['tests', module],
      args=['module=%s'%module, 'nproc=auto', 'verbosity=1'],
      haltOnFailure=False
    )

  # Override these methods.
  def add_build_base(self):
    """Build the base dependencies, e.g. Python, HDF5, etc."""
    self.add_step(self.cmd(
      name='base',
      command=[
        self.python_system,
        self.opjoin('modules', 'cctbx_project', 'libtbx', 'auto_build', 'install_base_packages.py'),
        '--python-shared',
        '--sphinx',
        '--skip-if-exists',
        '--%s'%self.BASE_PACKAGES
      ], 
      workdir='.'
    ))
  
  def add_configure(self):
    self.add_step(self.cmd(command=[
        self.python_base, 
        self.opjoin('..', 'modules', 'cctbx_project', 'libtbx', 'configure.py')
        ] + self.get_libtbx_configure(),
      workdir='build'
    ))
  
  def add_make(self):
    self.add_step(self.cmd(command=[self.opjoin('..', 'build', 'bin', 'libtbx.scons'), '-j', '4']))

  def add_install(self):
    """Run after compile, before tests."""
    pass
    
  def add_tests(self):
    """Run the unit tests."""
    pass
    
  def add_distribute(self):
    pass
  
##### Specific Configurations ######

class CCTBXBaseBuilder(CCIBuilder):
  """Base class for packages that include CCTBX as a dependency."""
  # Base packages
  BASE_PACKAGES = 'all'
  # Checkout these codebases
  CODEBASES = ['cbflib', 'cctbx_project', 'phenix_dev', 'gui_resources', 'chem_data']
  CODEBASES_EXTRA = []
  # Copy these sources from cci.lbl.gov
  HOT = ['annlib', 'boost', 'scons', 'ccp4io', 'ccp4io_adaptbx', 'annlib_adaptbx', 'tntbx', 'clipper', 'docutils']
  HOT_EXTRA = []
  # Configure for these cctbx packages
  LIBTBX = ['cctbx', 'cbflib', 'scitbx', 'libtbx', 'iotbx', 'mmtbx', 'smtbx', 'dxtbx', 'gltbx', 'wxtbx', 'phenix_dev', 'chem_data']
  LIBTBX_EXTRA = []
  def add_install(self):
    self.add_command('mmtbx.rebuild_rotarama_cache')
  
##### CCTBX-derived packages #####

class CCTBXBuilder(CCTBXBaseBuilder):
  CODEBASES_EXTRA = [ 'phenix_regression']
  LIBTBX_EXTRA = ['phenix_regression']
  def add_tests(self):
    self.add_test_command('libtbx.import_all_ext')
    self.add_test_command('libtbx.import_all_python', workdir=['modules', 'cctbx_project'])
    self.add_test_command('cctbx_regression.test_nightly')    
  
class CCTBXCIBuilder(CCTBXBaseBuilder):
  def add_tests(self):
    self.add_test_command('libtbx.import_all_ext')
    self.add_test_command('libtbx.import_all_python', workdir=['modules', 'cctbx_project'])
    self.add_test_command('libtbx.find_clutter', workdir=['modules', 'cctbx_project'], args=['--verbose'], flunkOnFailure=False, warnOnFailure=True)

class CCTBXDocsBuilder(CCTBXBaseBuilder):
  CODEBASES_EXTRA = ['dials', 'labelit']
  LIBTBX_EXTRA = ['sphinx', 'dials', 'labelit', 'xfel', 'rstbx']  
  def add_install(self):
    # Sphinx and numpydoc must be installed.
    self.add_step(self.cmd(
      name='sphinx build', 
      command=[
        self.opjoin('..', 'build', 'bin', 'sphinx.build'),
        '-b', 
        'html', 
        self.opjoin('..', 'modules', 'cctbx_project', 'sphinx'),
        '.'
      ], 
      workdir='docs'
    ))
    
  def add_distribute(self):  
    # Copy the docs to the server.
    self.add_step(self.cmd(
      name='sphinx upload',
      command=[
        'rsync', 
        '--delete', 
        '--chmod=a+rx', 
        '-r', 
        '.', 
        '%(cciuser)s@cci.lbl.gov:/net/boa/srv/html/cci/cctbx_docs'%{'cciuser':self.cciuser}
      ],
      workdir='docs'
    ))

class DIALSBuilder(CCTBXBaseBuilder):
  CODEBASES_EXTRA = ['dials', 'dials_regression']
  LIBTBX_EXTRA = ['dials', 'dials_regression']
  def add_tests(self):
    self.add_test_parallel('dials')
    self.add_test_parallel('dials_regression')

class LABELITBuilder(CCTBXBaseBuilder):
  CODEBASES_EXTRA = ['labelit', 'labelit_regression']
  LIBTBX_EXTRA = ['labelit', 'labelit_regression']
  def add_tests(self):
    pass
    
class XFELBuilder(CCTBXBaseBuilder):
 CODEBASES_EXTRA = ['dials', 'labelit', 'labelit_regression', 'dials_regression', 'xfel_regression', 'cxi_xdr_xes']
 LIBTBX_EXTRA = ['dials', 'labelit', 'labelit_regression', 'dials_regression', 'xfel', 'xfel_regression', 'cxi_xdr_xes']
 def add_tests(self):
   self.add_test_parallel('xfel_regression')

class PHENIXBuilder(CCTBXBaseBuilder):
  CODEBASES_EXTRA = [
    'phenix', 
    'phenix_regression', 
    'phenix_html',
    'phenix_examples',
    'labelit',
    'Plex', 
    'PyQuante', 
    'elbow', 
    'ksdssp', 
    'pex', 
    'pulchra', 
    'solve_resolve',
    'reel', 
    'gui_resources', 
    'opt_resources', 
    'muscle', 
    'labelit',
    'reduce', 
    'probe', 
    'king', 
    'suitename'
  ]
  HOT_EXTRA = ['phaser', 'phaser_regression']
  LIBTBX_EXTRA = ['phenix', 'phenix_regression', 'phenix_examples', 'solve_resolve', 'reel', 'phaser', 'phaser_regression', 'labelit']  
  def add_tests(self):
    # Windows convenience hack.
    if 'windows' in self.platform:
      self.add_test_command('phenix_regression.test_nightly_windows')      
    else:
      self.add_test_command('phenix_regression.test_nightly')
    # Other Phenix tests.
    self.add_test_parallel(module='elbow')
    # self.add_test_command('phaser_regression.regression', args='cci')
    self.add_test_command('phenix_html.rebuild_docs')
    self.add_test_command('phenix_regression.run_p9_sad_benchmark')
    self.add_test_command('phenix_regression.run_hipip_refine_benchmark')
    
  def add_distribute(self):
    if 'windows' in self.platform:
      pass
    else:
      self.add_command('phenix.make_dist', args=['dev', self.platform])

if __name__ == "__main__":
  parser = optparse.OptionParser()
  parser.add_option("--builder", help="Builder: cctbx, phenix, xfel, dials, labelit", default="cctbx")
  parser.add_option("--cciuser", help="CCI SVN username.")
  options, args = parser.parse_args()
  args = args or ['checkout', 'base', 'build', 'install', 'tests']
  print "Performing actions:", " ".join(args)
  builders = {
    'cctbx': CCTBXBuilder,
    'phenix': PHENIXBuilder,
    'xfel': XFELBuilder,
    'labelit': LABELITBuilder,
    'dials': DIALSBuilder
  }
  builder = builders[options.builder]
  builder(
    category='cctbx', 
    platform='debug',
    buildbot=False, 
    cciuser=options.cciuser,
    checkout=('checkout' in args),
    base=('base' in args),
    build=('build' in args),
    install=('install' in args),
    tests=('tests' in args)
  ).run()
  
  
    