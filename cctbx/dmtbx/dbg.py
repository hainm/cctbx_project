import sys, os, math
from cctbx_boost.arraytbx import shared
from cctbx_boost import sgtbx
from cctbx import xutils
from cctbx.development import debug_utils
from cctbx_boost import dmtbx

def ampl_phase_rad(f):
  amplidutes = shared.double()
  phases = shared.double()
  for i in xrange(f.size()):
    a, p = xutils.f_as_ampl_phase(f[i], deg=0)
    amplidutes.append(a)
    phases.append(p)
  return amplidutes, phases

def inplace_divide(array, arg):
  for i in xrange(array.size()):
    array[i] = array[i] / arg

def erase_small(miller_indices, data, cutoff):
  assert miller_indices.size() == data.size()
  for i in xrange(miller_indices.size()-1, -1, -1):
    if (data[i] < cutoff):
      miller_indices.erase(i)
      data.erase(i)

def exercise(SgInfo,
             number_of_point_atoms = 10,
             d_min=1.,
             e_min=1.2,
             loop_k_equiv=0,
             use_weights=0,
             verbose=0):
  elements = ["const"] * number_of_point_atoms
  xtal = debug_utils.random_structure(
    SgInfo, elements,
    volume_per_atom=50.,
    min_distance=1.5,
    general_positions_only=0,
    no_random_u=1)
  print xtal.UnitCell
  debug_utils.print_sites(xtal)
  MillerIndices = xutils.build_miller_indices(xtal, friedel_flag=1,d_min=d_min)
  Fcalc = xutils.calculate_structure_factors(MillerIndices, xtal, abs_F=1)
  e_values = Fcalc.F
  inplace_divide(
    e_values, math.sqrt(xtal.SgOps.OrderZ() * number_of_point_atoms))
  dmtbx.inplace_sort(MillerIndices.H, e_values, 1)
  s = shared.statistics(e_values)
  print "mean2:", s.mean2()
  print "number of structure factors:", e_values.size()
  erase_small(MillerIndices.H, e_values, e_min)
  print "number of structure factors:", e_values.size()
  Fcalc = xutils.calculate_structure_factors(MillerIndices, xtal, abs_F=0)
  dummy, phases = ampl_phase_rad(Fcalc.F)
  Fcalc.F = e_values
  if (0 or verbose):
    debug_utils.print_structure_factors(Fcalc)
  tprs = dmtbx.triplet_invariants(
   xtal.SgInfo, MillerIndices.H, e_values,
     loop_k_equiv, use_weights)
  print "number_of_weighted_triplets:", \
       tprs.number_of_weighted_triplets()
  print "total_number_of_triplets:", \
       tprs.total_number_of_triplets()
  print "average_number_of_triplets_per_reflection:", \
       tprs.average_number_of_triplets_per_reflection()
  new_phases = tprs.refine_phases(MillerIndices.H, e_values, phases)
  sum_w_phase_error = 0
  sum_w = 0
  for i in xrange(MillerIndices.H.size()):
    phase_error = debug_utils.phase_error(
      phases[i], new_phases[i], deg=0) * 180/math.pi
    if (0 or verbose):
      print MillerIndices.H[i], "%.3f %.3f %.3f" % (
        phases[i], new_phases[i], phase_error)
    sum_w_phase_error += e_values[i] * phase_error
    sum_w += e_values[i]
  print "mean weighted phase error: %.2f" % (sum_w_phase_error / sum_w,)
  if (0 or verbose):
    tprs.dump_triplets(MillerIndices.H)
  print

def run():
  Flags = debug_utils.command_line_options(sys.argv[1:], (
    "RandomSeed",
    "AllSpaceGroups",
    "IncludeVeryHighSymmetry",
    "loop_k_equiv",
    "use_weights",
    "ShowSymbolOnly",
  ))
  if (not Flags.RandomSeed): debug_utils.set_random_seed(0)
  symbols_to_stdout = 0
  if (len(sys.argv) > 1 + Flags.n):
    symbols = sys.argv[1:]
  else:
    symbols = debug_utils.get_test_space_group_symbols(Flags.AllSpaceGroups)
    symbols_to_stdout = 1
  for RawSgSymbol in symbols:
    if (RawSgSymbol.startswith("--")): continue
    SgSymbols = sgtbx.SpaceGroupSymbols(RawSgSymbol)
    SgInfo = sgtbx.SpaceGroup(SgSymbols).Info()
    LookupSymbol = SgInfo.BuildLookupSymbol()
    sys.stdout.flush()
    print >> sys.stderr, LookupSymbol
    sys.stderr.flush()
    if (symbols_to_stdout):
      print LookupSymbol
      sys.stdout.flush()
    if (SgInfo.SgOps().OrderZ() > 48 and not Flags.IncludeVeryHighSymmetry):
      print "High symmetry space group skipped."
      print
      sys.stdout.flush()
      continue
    if (Flags.ShowSymbolOnly):
      print "Space group:", LookupSymbol
    else:
      exercise(SgInfo,
        loop_k_equiv=Flags.loop_k_equiv,
        use_weights=Flags.use_weights)
    sys.stdout.flush()

if (__name__ == "__main__"):
  run()
  t = os.times()
  print "u+s,u,s:", t[0] + t[1], t[0], t[1]
