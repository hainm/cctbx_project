from __future__ import division
# LIBTBX_SET_DISPATCHER_NAME phenix.model_vs_map

from scitbx.array_family import flex
import sys, math, time
import iotbx.pdb
from libtbx.utils import Sorry
import mmtbx.utils
import mmtbx.maps.correlation
from cctbx import maptbx
from cctbx import miller
from mmtbx import monomer_library
import mmtbx.monomer_library.server
import mmtbx.monomer_library.pdb_interpretation
from libtbx import adopt_init_args
from mmtbx.rotamer.rotamer_eval import RotamerEval
from libtbx.test_utils import approx_equal
from mmtbx.maps import correlation
from libtbx.str_utils import format_value
from mmtbx.validation.ramalyze import ramalyze
from mmtbx.validation.cbetadev import cbetadev
from libtbx.utils import null_out
from mmtbx import model_statistics
from libtbx.str_utils import make_sub_header
from cctbx import adptbx

legend = """phenix.development.model_map_statistics:
  Given PDB file and a map compute various statistics.

How to run:
  phenix.development.model_map_statistics model.pdb map.ccp4 resolution=3

Feedback:
  PAfonine@lbl.gov"""

master_params_str = """
  map_file_name = None
    .type = str
  model_file_name = None
    .type = str
  resolution = None
    .type = float
  scattering_table = wk1995  it1992  *n_gaussian  neutron electron
    .type = choice
"""

def master_params():
  return iotbx.phil.parse(master_params_str, process_includes=False)

def broadcast(m, log):
  print >> log, "-"*79
  print >> log, m
  print >> log, "*"*len(m)

def show_histogram(data=None, n_slots=None, data_min=None, data_max=None,
                   log=None):
  from cctbx.array_family import flex
  hm = flex.histogram(data = data, n_slots = n_slots, data_min = data_min,
    data_max = data_max)
  lc_1 = hm.data_min()
  s_1 = enumerate(hm.slots())
  for (i_1,n_1) in s_1:
    hc_1 = hm.data_min() + hm.slot_width() * (i_1+1)
    print >> log, "%10.4f - %-10.4f : %d" % (lc_1, hc_1, n_1)
    lc_1 = hc_1

def run(args, log=sys.stdout):
  print >> log, "-"*79
  print >> log, legend
  print >> log, "-"*79
  inputs = mmtbx.utils.process_command_line_args(args = args,
    master_params = master_params())
  params = inputs.params.extract()
  # estimate resolution
  d_min = params.resolution
  broadcast(m="Map resolution:", log=log)
  if(d_min is None):
    raise Sorry("Resolution is required.")
  print >> log, "  d_min: %6.4f"%d_min
  # model
  broadcast(m="Input PDB:", log=log)
  file_names = inputs.pdb_file_names
  if(len(file_names) != 1): raise Sorry("PDB file has to given.")
  if(inputs.crystal_symmetry is None):
    raise Sorry("No crystal symmetry defined.")
  processed_pdb_file = monomer_library.pdb_interpretation.process(
    mon_lib_srv      = monomer_library.server.server(),
    ener_lib         = monomer_library.server.ener_lib(),
    file_name        = file_names[0],
    crystal_symmetry = inputs.crystal_symmetry,
    force_symmetry   = True,
    log              = None)
  ph = processed_pdb_file.all_chain_proxies.pdb_hierarchy
  if(len(ph.models())>1):
    raise Sorry("Only one model allowed.")
  xrs = processed_pdb_file.xray_structure()
  xrs.scattering_type_registry(table = params.scattering_table)
  xrs.show_summary(f=log, prefix="  ")
  # restraints
  sctr_keys = xrs.scattering_type_registry().type_count_dict().keys()
  has_hd = "H" in sctr_keys or "D" in sctr_keys
  geometry = processed_pdb_file.geometry_restraints_manager(
    show_energies      = False,
    assume_hydrogens_all_missing = not has_hd,
    plain_pairs_radius = 5.0)
  # map
  broadcast(m="Input map:", log=log)
  if(inputs.ccp4_map is None): raise Sorry("Map file has to given.")
  inputs.ccp4_map.show_summary(prefix="  ")
  map_data = inputs.ccp4_map.map_data()
  print >> log, "  Actual map (min,max,mean):", \
    map_data.as_1d().min_max_mean().as_tuple()
  make_sub_header("Histogram of map values", out=log)
  md = map_data.as_1d()
  show_histogram(data=md, n_slots=10, data_min=flex.min(md),
    data_max=flex.max(md), log=log)
  # shift origin if needed
  shift_needed = not \
    (map_data.focus_size_1d() > 0 and map_data.nd() == 3 and
     map_data.is_0_based())
  if(shift_needed):
    N = map_data.all()
    O=map_data.origin()
    map_data = map_data.shift_origin()
    # apply same shift to the model
    a,b,c = xrs.crystal_symmetry().unit_cell().parameters()[:3]
    sites_cart = xrs.sites_cart()
    sx,sy,sz = a/N[0]*O[0], b/N[1]*O[1], c/N[2]*O[2]
    sites_cart_shifted = sites_cart-\
      flex.vec3_double(sites_cart.size(), [sx,sy,sz])
    xrs.set_sites_cart(sites_cart_shifted)
  ####
  # Compute and show all stats
  ####
  broadcast(m="Model statistics:", log=log)
  make_sub_header("Overall", out=log)
  ms = model_statistics.geometry(
    pdb_hierarchy      = ph,
    restraints_manager = geometry,
    molprobity_scores  = True)
  ms.show()
  make_sub_header("Histogram of devations from ideal bonds", out=log)
  show_histogram(data=ms.bond_deltas, n_slots=10, data_min=0, data_max=0.2,
    log=log)
  #
  make_sub_header("Histogram of devations from ideal angles", out=log)
  show_histogram(data=ms.angle_deltas, n_slots=10, data_min=0, data_max=30.,
    log=log)
  #
  make_sub_header("Histogram of non-bonded distances", out=log)
  show_histogram(data=ms.nonbonded_distances, n_slots=10, data_min=0,
    data_max=5., log=log)
  #
  make_sub_header("Histogram of ADPs", out=log)
  bs = xrs.extract_u_iso_or_u_equiv()*adptbx.u_as_b(1.)
  show_histogram(data=bs, n_slots=10, data_min=flex.min(bs),
    data_max=flex.max(bs), log=log)
  #
  # Compute FSC(map, model)
  broadcast(m="Map-model FSC:", log=log)
  mmtbx.maps.correlation.fsc_model_map(
    xray_structure=xrs, map=map_data, d_min=d_min, log=log)
  #
  # various CC
  cc_calculator = mmtbx.maps.correlation.from_map_and_xray_structure_or_fmodel(
    xray_structure = xrs,
    map_data       = map_data,
    d_min          = d_min)
  broadcast(m="Map-model CC:", log=log)
  print >> log, "Overall (entire box):  %6.4f"%cc_calculator.cc()
  print >> log, "Around atoms (masked): %6.4f"%cc_calculator.cc(
    selection=flex.bool(xrs.scatterers().size(), True))
  # per chain
  print >> log, "Per chain:"
  for chain in ph.chains():
    print >> log, "  chain %s: %6.4f"%(chain.id, cc_calculator.cc(
      selection=chain.atoms().extract_i_seq()))
  # per residue
  print >> log, "Per residue:"
  for rg in ph.residue_groups():
    cc = cc_calculator.cc(selection=rg.atoms().extract_i_seq())
    print >> log, "  chain id: %s resid %s: %6.4f"%(
      rg.parent().id, rg.resid(), cc)
  # per residue detailed counts
  print >> log, "Per residue (histogram):"
  crystal_gridding = maptbx.crystal_gridding(
    unit_cell             = xrs.unit_cell(),
    space_group_info      = xrs.space_group_info(),
    pre_determined_n_real = map_data.accessor().all())
  f_calc = xrs.structure_factors(d_min=d_min).f_calc()
  fft_map = miller.fft_map(
    crystal_gridding     = crystal_gridding,
    fourier_coefficients = f_calc)
  fft_map.apply_sigma_scaling()
  map_model = fft_map.real_map_unpadded()
  sites_cart = xrs.sites_cart()
  cc_per_residue = flex.double()
  for rg in ph.residue_groups():
    cc = mmtbx.maps.correlation.from_map_map_atoms(
      map_1      = map_data,
      map_2      = map_model,
      sites_cart = sites_cart.select(rg.atoms().extract_i_seq()),
      unit_cell  = xrs.unit_cell(),
      radius     = 2.)
    cc_per_residue.append(cc)
  show_histogram(data=cc_per_residue, n_slots=10, data_min=-1., data_max=1.0,
    log=log)
  #

"""
THIS IS NOT USED ANYWHERE BUT MIGHT BE USEFUL IN FUTURE, REMOVE LATER

def min_nonbonded_distance(sites_cart, geometry, xray_structure, selection):
  selw = xray_structure.selection_within(radius = 3.0, selection =
    flex.bool(xray_structure.scatterers().size(), selection)).iselection()
  sites_cart_w = sites_cart.select(selw)
  #
  g = geometry.select(iselection=selw)
  pair_proxy_list_sorted=[]
  bond_proxies_simple, asu = g.get_all_bond_proxies(
    sites_cart = sites_cart_w)
  for proxy in bond_proxies_simple:
    tmp = list(proxy.i_seqs)
    tmp.sort()
    pair_proxy_list_sorted.append(tmp)
  pair_proxy_list_sorted.sort()
  #
  dist_min=999
  i_min,j_min = None,None
  for i, si in enumerate(sites_cart_w):
    for j, sj in enumerate(sites_cart_w):
      if(i<j):
        p = [i,j]
        p.sort()
        if(not p in pair_proxy_list_sorted):
          dist_ij = math.sqrt(
            (si[0]-sj[0])**2+
            (si[1]-sj[1])**2+
            (si[2]-sj[2])**2)
          if(dist_ij<dist_min):
            dist_min = dist_ij
            i_min,j_min = i, j
  return i_min,j_min,dist_min

class residue_monitor(object):
  def __init__(self,
               residue,
               id_str,
               bond_rmsd=None,
               angle_rmsd=None,
               map_cc=None,
               map_min=None,
               map_mean=None,
               rotamer_status=None,
               ramachandran_status=None,
               cbeta_status=None,
               min_nonbonded=None):
    adopt_init_args(self, locals())

  def show(self):
    print "%12s %6s %6s %6s %6s %6s %7s %9s %7s %7s"%(
      self.id_str,
      format_value("%6.3f",self.map_cc),
      format_value("%5.2f",self.map_min),
      format_value("%5.2f",self.map_mean),
      format_value("%6.3f",self.bond_rmsd),
      format_value("%6.2f",self.angle_rmsd),
      format_value("%6.3f",self.min_nonbonded),
      self.rotamer_status,
      self.ramachandran_status,
      self.cbeta_status)

class structure_monitor(object):
  def __init__(self,
               pdb_hierarchy,
               xray_structure,
               map_1, # map data
               map_2,
               geometry,
               atom_radius):
    adopt_init_args(self, locals())
    self.unit_cell = self.xray_structure.unit_cell()
    self.xray_structure = xray_structure.deep_copy_scatterers()
    self.unit_cell = self.xray_structure.unit_cell()
    self.rotamer_manager = RotamerEval()
    #
    sc1 = self.xray_structure.sites_cart()
    sc2 = self.pdb_hierarchy.atoms().extract_xyz()
    assert approx_equal(sc1, sc2, 1.e-3)
    #
    self.sites_cart = self.xray_structure.sites_cart()
    self.sites_frac = self.xray_structure.sites_frac()
    #
    self.map_cc_whole_unit_cell = None
    self.map_cc_around_atoms = None
    self.map_cc_per_atom = None
    self.rmsd_b = None
    self.rmsd_a = None
    self.dist_from_start = 0
    self.dist_from_previous = 0
    self.number_of_rotamer_outliers = 0
    self.residue_monitors = None
    #
    ramalyze_obj = ramalyze(pdb_hierarchy=pdb_hierarchy, outliers_only=False)
    self.rotamer_outlier_selection = ramalyze_obj.outlier_selection()
    #
    cbetadev_obj = cbetadev(
        pdb_hierarchy = pdb_hierarchy,
        outliers_only = False,
        out           = null_out())
    self.cbeta_outlier_selection = cbetadev_obj.outlier_selection()
    #
    self.initialize()

  def initialize(self):
    # residue monitors
    print "    ID-------|MAP-----------------|RMSD----------|NONB-|ROTAMER--|RAMA---|CBETA--|"
    print "             |CC     MIN    MEAN  |BOND    ANGLE |     |         |       |        "
    self.residue_monitors = []
    sites_cart = self.xray_structure.sites_cart()
    for model in self.pdb_hierarchy.models():
      for chain in model.chains():
        for residue_group in chain.residue_groups():
          for conformer in residue_group.conformers():
            for residue in conformer.residues():
              id_str="%s,%s,%s"%(chain.id,residue.resname,residue.resseq.strip())
              selection = residue.atoms().extract_i_seq()
              cc = correlation.from_map_map_atoms(
                map_1      = self.map_1,
                map_2      = self.map_2,
                sites_cart = self.sites_cart.select(selection),
                unit_cell  = self.unit_cell,
                radius     = self.atom_radius)
              rotamer_status = self.rotamer_manager.evaluate_residue(residue)
              grm = self.geometry.select(iselection=selection)
              es = grm.energies_sites(sites_cart=residue.atoms().extract_xyz())
              ramachandran_status="VALID"
              if(selection[0] in self.rotamer_outlier_selection):
                ramachandran_status="OUTLIER"
              cbeta_status="VALID"
              if(selection[0] in self.cbeta_outlier_selection):
                cbeta_status="OUTLIER"
              mnd = min_nonbonded_distance(
                sites_cart     = sites_cart,
                geometry       = self.geometry,
                xray_structure = self.xray_structure,
                selection      = selection)
              mi,me = self.map_values_min_mean(selection = selection)
              rm = residue_monitor(
                residue             = residue,
                id_str              = id_str,
                bond_rmsd           = es.bond_deviations()[2],
                angle_rmsd          = es.angle_deviations()[2],
                map_cc              = cc,
                map_min             = mi,
                map_mean            = me,
                min_nonbonded       = mnd[2],
                rotamer_status      = rotamer_status,
                ramachandran_status = ramachandran_status,
                cbeta_status        = cbeta_status)
              self.residue_monitors.append(rm)
              rm.show()

  def show(self):
    print "     ID       MAP CC    BOND      ANGLE  NONB     ROTAMER    RAMA      CBETA"
    for rm in self.residue_monitors:
      rm.show()

  def map_values_min_mean(self, selection):
    map_values = flex.double()
    for i in selection:
      mv = self.map_1.eight_point_interpolation(self.sites_frac[i])
      map_values.append(mv)
    mi,ma,me = map_values.min_max_mean().as_tuple()
    return mi, me

  def map_map_sites_cc(self, selection):
    return correlation.from_map_map_atoms(
      map_1      = self.map_1,
      map_2      = self.map_2,
      sites_cart = self.sites_cart.select(selection),
      unit_cell  = self.unit_cell,
      radius     = self.atom_radius)
"""

if (__name__ == "__main__"):
  t0 = time.time()
  run(args=sys.argv[1:])
  print
  print "Time:", round(time.time()-t0, 3)
