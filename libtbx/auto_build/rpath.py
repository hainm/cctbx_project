"""Fix RPATH and ORIGIN for relocatable binaries."""
from __future__ import division
import os
import re
import subprocess
import argparse
import sys

# Binary builds: /net/cci/auto_build/phenix_installers
# export DYLD_PRINT_INITIALIZERS="files"
# For Linux, requires PatchELF.
#   http://nixos.org/patchelf.html
# For Mac, requires otool and install_name_tool,
#   which are included with XCode.

##### Helper functions #####

def find_exec(root='.'):
  """Find executables (using +x permissions)."""
  # find . -type f -perm +111 -print
  p = check_output(['find', root, '-type', 'f', '-perm', '+111'])
  # unix find may print empty lines; strip those out.
  return filter(None, [i.strip() for i in p.split("\n")])

def find_ext(ext='', root='.'):
  """Find files with a particular extension. Include the ".", e.g. ".txt". """
  found = []
  for root, dirs, files in os.walk(root):
    found.extend([os.path.join(root, i) for i in files if i.endswith(ext)])
  return found

def cmd(*popenargs, **kwargs):
  print "Running:",
  print " ".join(*popenargs)
  ignorefail = kwargs.pop('ignorefail', False)
  kwargs['stdout'] = subprocess.PIPE
  kwargs['stderr'] = subprocess.PIPE
  process = subprocess.Popen(*popenargs, **kwargs)
  a, b = process.communicate()
  exitcode = process.wait()
  if exitcode:
    if ignorefail:
      print("WARNING: Command returned non-zero exit code: %s"%" ".join(*popenargs))
      print a
      print b
    else:
      print a
      print b
      raise Exception("Command returned non-zero exit code")

def echo(*popenargs, **kwargs):
    print "Running:",
    print " ".join(*popenargs)

# cmd = echo

def check_output(*popenargs, **kwargs):
  """Copy of subprocess.check_output()"""
  if 'stdout' in kwargs:
    raise ValueError('stdout argument not allowed, it will be overridden.')
  process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
  output, unused_err = process.communicate()
  retcode = process.poll()
  if retcode:
    cmd = kwargs.get("args")
    if cmd is None:
      cmd = popenargs[0]
    raise subprocess.CalledProcessError(retcode, cmd)
  return output

class FixLinuxRpath(object):
  def find_deps(self, filename):
    ret = []
    p = check_output(['ldd', filename])
    for line in p.split("\n"):
      lib, _, found = line.partition("=>")
      if "not found" in found:
        ret.append(lib.strip())
    return ret

  def run(self, root, replace=None):
    replace = replace or {}
    targets = set()
    targets |= set(find_ext('.so', root=root))
    # targets |= set(find_exec(root=root))

    # First pass: identify relative $ORIGIN for each library.
    origins = {}
    for target in sorted(targets):
      relpath = os.path.relpath(os.path.dirname(target), root)
      relpath = os.path.join('$ORIGIN', relpath)
      origins[os.path.basename(target)] = relpath

    print "=== ORIGINS ==="
    for k,v in sorted(origins.items()): print k, v

    # Second pass: find linked libraries, add rpath's
    for target in sorted(targets):
      deps = self.find_deps(target)
      found = set()
      for dep in deps:
        if origins.get(dep):
          found.add(origins[dep])
      if found:
        rpaths = ':'.join(found)
        cmd(['patchelf', '--set-rpath', rpaths, target])

    return

class FixMacRpath(object):
  """Process all binary files (executables, libraries) to rename linked libraries."""

  def find_deps(self, filename):
    """Find linked libraries using otool -L."""
    p = check_output(['otool','-L',filename])
    # otool doesn't return an exit code on failure, so check..
    if "not an object file" in p:
      raise Exception, "Not Mach-O binary"
    # Just get the dylib install names
    p = [i.strip().partition(" ")[0] for i in p.split("\n")[1:]]
    return p

  def id_rpath(self, filename):
    """Generate the @rpath for a file, relative to the current directory as @rpath root."""
    p = len(filename.split("/"))-1
    f = os.path.join("@loader_path", *[".."]*p)
    return f

  def run(self, root, replace=None):
    replace = replace or {}
    replace[root] = '@rpath'
    # Find all files that end in .so/.dylib, or are executable
    # This will include many script files, but we will ignore
    # these failures when running otool/install_name_tool
    targets = set()
    targets |= set(find_ext('.so', root=root))
    targets |= set(find_ext('.dylib', root=root))
    # targets |= set(find_exec(root=root))

    print "Targets:", len(targets)
    for f in sorted(targets):
      # Get the linked libraries and
      # check if the file is a Mach-O binary
      print "\n==== Target:", f
      try:
        libs = self.find_deps(f)
      except Exception, e:
        continue

      # Set the install_name id.
      install_name_id = os.path.join('@rpath', os.path.relpath(f, root))
      cmd(['install_name_tool', '-id', install_name_id, f], cwd=root, ignorefail=True)

      # Set @rpath, this is a reference to the root of the package.
      # Linked libraries will be referenced relative to this.
      rpath = os.path.join('@loader_path', os.path.relpath(root, os.path.dirname(f)))
      cmd(['install_name_tool', '-add_rpath', rpath, f], cwd=root, ignorefail=True)

      for lib in libs:
        rlib = lib
        for k,v in replace.items():
          rlib = re.sub(k, v, rlib)
        if lib != rlib:
          cmd(['install_name_tool', '-change', lib, rlib, f], cwd=root, ignorefail=True)

def run (args) :
  parser = argparse.ArgumentParser()
  parser.add_argument("root", help="Build path")
  parser.add_argument("--otherroot", help="Other build path")
  args = parser.parse_args(args)

  # Setup args.
  root = args.root
  replace = {}
  replace['^lib'] = '@rpath/lib'
  if args.otherroot:
    replace[args.otherroot] = '@rpath'

  # Run the rpath fixer.
  cls = FixLinuxRpath
  if sys.platform == 'darwin':
    cls = FixMacRpath
  cls().run(root=root, replace=replace)

if __name__ == "__main__" :
  run(sys.argv[1:])