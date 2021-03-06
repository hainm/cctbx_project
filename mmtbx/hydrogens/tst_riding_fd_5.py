from __future__ import division
import time
#import sys
from cctbx.array_family import flex
from mmtbx import monomer_library
import mmtbx.monomer_library.server
import mmtbx.monomer_library.pdb_interpretation
from libtbx.test_utils import approx_equal
#from scitbx import matrix
from mmtbx.hydrogens import riding
from mmtbx.hydrogens import modify_gradients

#-----------------------------------------------------------------------------
# This finite difference test checks transformation of riding H gradients
# for H geometries, H/D exchanged
# C-H exchange might not be sensical, but it's always good to test anyway
#-----------------------------------------------------------------------------
#
def exercise(pdb_str, eps):
  mon_lib_srv = monomer_library.server.server()
  ener_lib = monomer_library.server.ener_lib()
  processed_pdb_file = monomer_library.pdb_interpretation.process(
    mon_lib_srv    = mon_lib_srv,
    ener_lib       = ener_lib,
    raw_records    = pdb_str,
    force_symmetry = True)
  pdb_hierarchy = processed_pdb_file.all_chain_proxies.pdb_hierarchy
  xray_structure = processed_pdb_file.xray_structure()
  sites_cart = xray_structure.sites_cart()
  geometry = processed_pdb_file.geometry_restraints_manager(
    show_energies      = False,
    plain_pairs_radius = 5.0)

  es = geometry.energies_sites(
    sites_cart = sites_cart,
    compute_gradients = True)
  g_analytical = es.gradients
#
  riding_h_manager = riding.manager(
    pdb_hierarchy       = pdb_hierarchy,
    geometry_restraints = geometry)

  h_parameterization = riding_h_manager.h_parameterization

  riding_h_manager.idealize_hydrogens_inplace(
      pdb_hierarchy=pdb_hierarchy,
      xray_structure=xray_structure)
  #sites_cart = pdb_hierarchy.atoms().extract_xyz()
  sites_cart = xray_structure.sites_cart()

  #for i in g_analytical:
  #  print i
  #print '----------'
  g_analytical = geometry.energies_sites(
    sites_cart = sites_cart, compute_gradients = True).gradients
  modify_gradients.modify_gradients(
    sites_cart         = sites_cart,
    h_parameterization = h_parameterization,
    grads              = g_analytical)
  #
  ex = [eps,0,0]
  ey = [0,eps,0]
  ez = [0,0,eps]
  g_fd = flex.vec3_double()
  for i_site in xrange(sites_cart.size()):
    g_fd_i = []
    for e in [ex,ey,ez]:
      ts = []
      for sign in [-1,1]:
        sites_cart_ = sites_cart.deep_copy()
        xray_structure_ = xray_structure.deep_copy_scatterers()
        sites_cart_[i_site] = [
          sites_cart_[i_site][j]+e[j]*sign for j in xrange(3)]
        xray_structure_.set_sites_cart(sites_cart_)
        # after shift, recalculate H position
        riding_h_manager.idealize_hydrogens_inplace(
          xray_structure=xray_structure_)
        sites_cart_ = xray_structure_.sites_cart()
        ts.append(geometry.energies_sites(
          sites_cart = sites_cart_,
          compute_gradients = False).target)
      g_fd_i.append((ts[1]-ts[0])/(2*eps))
    g_fd.append(g_fd_i)

  for g1, g2 in zip(g_analytical, g_fd):
    #print g1,g2
    assert approx_equal(g1,g2, 1.e-4)
  #print '*'*79

# flat 2 neighbors
pdb_str_01 = """
CRYST1   15.083   11.251   14.394  90.00  90.00  90.00 P 1
SCALE1      0.066300  0.000000  0.000000        0.00000
SCALE2      0.000000  0.088881  0.000000        0.00000
SCALE3      0.000000  0.000000  0.069473        0.00000
ATOM      1  C   ARG A   2       5.253  20.304  25.155  1.00  0.00           C
ATOM      2  N   HIS A   3       6.067  20.098  24.123  1.00  0.00           N
ATOM      3  CA  HIS A   3       7.516  20.107  24.260  1.00  0.00           C
ATOM      4  H  AHIS A   3       5.747  19.921  23.171  0.50  0.00           H
ATOM      5  D  BHIS A   3       5.747  19.921  23.171  0.50  0.00           D
"""

# flat 2 neighbors shaked
pdb_str_02 = """
CRYST1   15.083   11.251   14.394  90.00  90.00  90.00 P 1
SCALE1      0.066300  0.000000  0.000000        0.00000
SCALE2      0.000000  0.088881  0.000000        0.00000
SCALE3      0.000000  0.000000  0.069473        0.00000
ATOM      1  C   ARG A   2       5.099  20.402  25.169  1.00  0.00           C
ATOM      2  N   HIS A   3       6.078  20.274  24.222  1.00  0.00           N
ATOM      3  CA  HIS A   3       7.421  19.969  24.222  1.00  0.00           C
ATOM      4  H  AHIS A   3       5.582  19.974  23.131  0.50  0.00           H
ATOM      5  D  BHIS A   3       5.926  20.100  23.155  0.50  0.00           D
"""

# alg1a minimized
pdb_str_03 = """
CRYST1   14.446   16.451   11.913  90.00  90.00  90.00 P 1
SCALE1      0.069223  0.000000  0.000000        0.00000
SCALE2      0.000000  0.060787  0.000000        0.00000
SCALE3      0.000000  0.000000  0.083942        0.00000
ATOM      1  CD  ARG A  50       4.896   7.973   6.011  1.00 10.00           C
ATOM      2  NE  ARG A  50       5.406   6.701   5.508  1.00 10.00           N
ATOM      3  CZ  ARG A  50       6.515   6.111   5.944  1.00 10.00           C
ATOM      4  NH1 ARG A  50       7.243   6.676   6.898  1.00 10.00           N
ATOM      5  NH2 ARG A  50       6.898   4.953   5.424  1.00 10.00           N
ATOM      6  HE AARG A  50       4.876   6.233   4.773  0.50 10.00           H
ATOM      7 HH11AARG A  50       6.956   7.567   7.304  0.50 10.00           H
ATOM      8 HH12AARG A  50       8.093   6.218   7.227  0.50 10.00           H
ATOM      9 HH21AARG A  50       6.342   4.515   4.690  0.50 10.00           H
ATOM     10 HH22AARG A  50       7.749   4.500   5.758  0.50 10.00           H
ATOM     11  DE BARG A  50       4.876   6.233   4.773  0.50 10.00           D
ATOM     12 DH11BARG A  50       6.956   7.567   7.304  0.50 10.00           D
ATOM     13 DH12BARG A  50       8.093   6.218   7.227  0.50 10.00           D
ATOM     14 DH21BARG A  50       6.342   4.515   4.690  0.50 10.00           D
ATOM     15 DH22BARG A  50       7.749   4.500   5.758  0.50 10.00           D
TER
"""

# alg1a shaked
pdb_str_04 = """
CRYST1   14.446   16.451   11.913  90.00  90.00  90.00 P 1
SCALE1      0.069223  0.000000  0.000000        0.00000
SCALE2      0.000000  0.060787  0.000000        0.00000
SCALE3      0.000000  0.000000  0.083942        0.00000
ATOM      1  CD  ARG A  50       4.830   7.928   6.084  1.00 10.00           C
ATOM      2  NE  ARG A  50       5.434   6.841   5.374  1.00 10.00           N
ATOM      3  CZ  ARG A  50       6.450   6.116   6.035  1.00 10.00           C
ATOM      4  NH1 ARG A  50       7.392   6.694   6.803  1.00 10.00           N
ATOM      5  NH2 ARG A  50       6.898   5.026   5.305  1.00 10.00           N
ATOM      6  HE AARG A  50       4.867   6.348   4.684  0.50 10.00           H
ATOM      7 HH11AARG A  50       7.140   7.516   7.352  0.50 10.00           H
ATOM      8 HH12AARG A  50       8.199   6.141   7.091  0.50 10.00           H
ATOM      9 HH21AARG A  50       6.308   4.628   4.574  0.50 10.00           H
ATOM     10 HH22AARG A  50       7.759   4.551   5.577  0.50 10.00           H
ATOM     11  DE BARG A  50       4.867   6.348   4.684  0.50 10.00           D
ATOM     12 DH11BARG A  50       7.140   7.516   7.352  0.50 10.00           D
ATOM     13 DH12BARG A  50       8.199   6.141   7.091  0.50 10.00           D
ATOM     14 DH21BARG A  50       6.308   4.628   4.574  0.50 10.00           D
ATOM     15 DH22BARG A  50       7.759   4.551   5.577  0.50 10.00           D
"""

# 2tetra
pdb_str_05 = """
CRYST1   27.805   30.931   25.453  90.00  90.00  90.00 P 1
SCALE1      0.035965  0.000000  0.000000        0.00000
SCALE2      0.000000  0.032330  0.000000        0.00000
SCALE3      0.000000  0.000000  0.039288        0.00000
ATOM      1  CA  SER A   3      11.057  14.432  13.617  1.00  5.95           C
ANISOU    1  CA  SER A   3      582    671   1007   -168    135    158       C
ATOM      2  CB  SER A   3      10.277  13.648  12.559  1.00  6.41           C
ANISOU    2  CB  SER A   3      638    591   1207   -162    148    106       C
ATOM      3  OG  SER A   3       9.060  14.298  12.238  1.00  7.60           O
ANISOU    3  OG  SER A   3      680    955   1251   -244   -164    339       O
ATOM      4  HB2ASER A   3      10.818  13.578  11.757  0.40  6.41           H
ATOM      5  HB3ASER A   3      10.081  12.763  12.904  0.40  6.41           H
ATOM      6 DHB2BSER A   3      10.818  13.578  11.757  0.60  6.41           D
ATOM      7 DHB3BSER A   3      10.081  12.763  12.904  0.60  6.41           D
"""

# 2tetra distorted
pdb_str_06 = """
CRYST1   27.805   30.931   25.453  90.00  90.00  90.00 P 1
SCALE1      0.035965  0.000000  0.000000        0.00000
SCALE2      0.000000  0.032330  0.000000        0.00000
SCALE3      0.000000  0.000000  0.039288        0.00000
ATOM      1  CA  SER A   3      10.856  14.444  13.455  1.00  5.95           C
ANISOU    1  CA  SER A   3      582    671   1007   -168    135    158       C
ATOM      2  CB  SER A   3      10.225  13.565  12.597  1.00  6.41           C
ANISOU    2  CB  SER A   3      638    591   1207   -162    148    106       C
ATOM      3  OG  SER A   3       9.123  14.383  12.193  1.00  7.60           O
ANISOU    3  OG  SER A   3      680    955   1251   -244   -164    339       O
ATOM      4  HB2ASER A   3      10.969  13.436  11.739  0.40  6.41           H
ATOM      5  HB3ASER A   3      10.028  12.954  13.077  0.40  6.41           H
ATOM      6 DHB2BSER A   3      10.925  13.557  11.772  0.60  6.41           D
ATOM      7 DHB3BSER A   3      10.287  12.654  12.803  0.60  6.41           D
"""

# 3tetra minimized
pdb_str_07 = """
CRYST1   27.805   30.931   25.453  90.00  90.00  90.00 P 1
SCALE1      0.035965  0.000000  0.000000        0.00000
SCALE2      0.000000  0.032330  0.000000        0.00000
SCALE3      0.000000  0.000000  0.039288        0.00000
ATOM      1  N   SER A   4       7.601  20.006  12.837  1.00  5.10           N
ANISOU    1  N   SER A   4      500    632    808   -107     58    104       N
ATOM      2  CA  SER A   4       7.145  18.738  13.391  1.00  5.95           C
ANISOU    2  CA  SER A   4      582    671   1007   -168    135    158       C
ATOM      3  C   SER A   4       8.313  17.949  13.971  1.00  5.79           C
ANISOU    3  C   SER A   4      661    588    952   -116    206    135       C
ATOM      4  CB  SER A   4       6.433  17.910  12.319  1.00  6.41           C
ANISOU    4  CB  SER A   4      638    591   1207   -162    148    106       C
ATOM      5  HA ASER A   4       6.513  18.912  14.106  0.55  5.95           H
ATOM      5 DHA BSER A   4       6.513  18.912  14.106  0.45  5.95           D
"""

# 3tetra distorted
pdb_str_08 = """
CRYST1   27.805   30.931   25.453  90.00  90.00  90.00 P 1
SCALE1      0.035965  0.000000  0.000000        0.00000
SCALE2      0.000000  0.032330  0.000000        0.00000
SCALE3      0.000000  0.000000  0.039288        0.00000
ATOM      1  N   SER A   4       7.694  20.012  12.917  1.00  5.10           N
ANISOU    1  N   SER A   4      500    632    808   -107     58    104       N
ATOM      2  CA  SER A   4       7.004  18.841  13.534  1.00  5.95           C
ANISOU    2  CA  SER A   4      582    671   1007   -168    135    158       C
ATOM      3  C   SER A   4       8.178  17.985  14.068  1.00  5.79           C
ANISOU    3  C   SER A   4      661    588    952   -116    206    135       C
ATOM      4  CB  SER A   4       6.270  18.108  12.379  1.00  6.41           C
ANISOU    4  CB  SER A   4      638    591   1207   -162    148    106       C
ATOM      5  HA ASER A   4       6.524  18.724  14.126  0.55  5.95           H
ATOM      5 DHA BSER A   4       6.513  18.912  14.106  0.45  5.95           H
"""

# alg1b minimized
pdb_str_09 = """CRYST1   27.805   30.931   25.453  90.00  90.00  90.00 P 1
SCALE1      0.035965  0.000000  0.000000        0.00000
SCALE2      0.000000  0.032330  0.000000        0.00000
SCALE3      0.000000  0.000000  0.039288        0.00000
ATOM      1  CA  SER A   6      10.253  21.454  16.783  1.00  5.95           C
ANISOU    1  CA  SER A   6      582    671   1007   -168    135    158       C
ATOM      2  CB  SER A   6       9.552  20.703  15.649  1.00  6.41           C
ANISOU    2  CB  SER A   6      638    591   1207   -162    148    106       C
ATOM      3  OG  SER A   6       8.345  21.347  15.280  1.00  7.60           O
ANISOU    3  OG  SER A   6      680    955   1251   -244   -164    339       O
ATOM      4  HB2 SER A   6      10.214  20.670  14.784  0.45  6.41           H
ATOM      5  HB3 SER A   6       9.325  19.690  15.982  0.45  6.41           H
ATOM      6  HG ASER A   6       7.910  20.853  14.554  0.55  7.60           H
ATOM      7  DG BSER A   6       7.910  20.853  14.554  0.55  7.60           D
TER
"""

# alg1b distorted
pdb_str_10 = """
CRYST1   27.805   30.931   25.453  90.00  90.00  90.00 P 1
SCALE1      0.035965  0.000000  0.000000        0.00000
SCALE2      0.000000  0.032330  0.000000        0.00000
SCALE3      0.000000  0.000000  0.039288        0.00000
ATOM      1  CA  SER A   6      10.083  21.475  16.848  1.00  5.95           C
ANISOU    1  CA  SER A   6      582    671   1007   -168    135    158       C
ATOM      2  CB  SER A   6       9.437  20.751  15.546  1.00  6.41           C
ANISOU    2  CB  SER A   6      638    591   1207   -162    148    106       C
ATOM      3  OG  SER A   6       8.368  21.346  15.146  1.00  7.60           O
ANISOU    3  OG  SER A   6      680    955   1251   -244   -164    339       O
ATOM      4  HB2 SER A   6      10.034  20.616  14.977  0.45  6.41           H
ATOM      5  HB3 SER A   6       9.158  19.775  16.137  0.45  6.41           H
ATOM      6  HG ASER A   6       7.964  20.906  14.679  0.55  7.60           H
ATOM      7  DG BSER A   6       7.989  20.672  14.454  0.55  7.60           D
"""

# propeller minimized
pdb_str_11 = """
CRYST1   27.805   30.931   25.453  90.00  90.00  90.00 P 1
SCALE1      0.035965  0.000000  0.000000        0.00000
SCALE2      0.000000  0.032330  0.000000        0.00000
SCALE3      0.000000  0.000000  0.039288        0.00000
ATOM      1  CA  VAL A   7      17.924   8.950  14.754  1.00 10.37           C
ANISOU    1  CA  VAL A   7     1783    902   1255     67   -148    -14       C
ATOM      2  CB  VAL A   7      16.678   8.886  13.852  1.00 11.26           C
ANISOU    2  CB  VAL A   7     1571    963   1743     96   -176     62       C
ATOM      3  CG1 VAL A   7      16.660  10.063  12.888  1.00 11.06           C
ANISOU    3  CG1 VAL A   7     1704   1072   1425    125   -105     37       C
ATOM      4 HG11AVAL A   7      16.643  10.888  13.399  0.35 13.27           H
ATOM      5 HG12AVAL A   7      15.868  10.002  12.331  0.35 13.27           H
ATOM      6 HG13AVAL A   7      17.457  10.030  12.336  0.35 13.27           H
ATOM      7 DG11BVAL A   7      16.643  10.888  13.399  0.65 13.27           D
ATOM      8 DG12BVAL A   7      15.868  10.002  12.331  0.65 13.27           D
ATOM      9 DG13BVAL A   7      17.457  10.030  12.336  0.65 13.27           D
"""

# propeller shaked
pdb_str_12 = """
CRYST1   27.805   30.931   25.453  90.00  90.00  90.00 P 1
SCALE1      0.035965  0.000000  0.000000        0.00000
SCALE2      0.000000  0.032330  0.000000        0.00000
SCALE3      0.000000  0.000000  0.039288        0.00000
ATOM      1  CA  VAL A   7      17.967   9.002  14.926  1.00 10.37           C
ANISOU    1  CA  VAL A   7     1783    902   1255     67   -148    -14       C
ATOM      2  CB  VAL A   7      16.698   8.861  13.864  1.00 11.26           C
ANISOU    2  CB  VAL A   7     1571    963   1743     96   -176     62       C
ATOM      3  CG1 VAL A   7      16.655  10.154  13.014  1.00 11.06           C
ANISOU    3  CG1 VAL A   7     1704   1072   1425    125   -105     37       C
ATOM      4 HG11AVAL A   7      16.508  10.702  13.486  0.35 13.27           H
ATOM      5 HG12AVAL A   7      15.946   9.926  12.504  0.35 13.27           H
ATOM      6 HG13AVAL A   7      17.430   9.954  12.137  0.35 13.27           H
ATOM      7 DG11BVAL A   7      16.842  11.073  13.530  0.65 13.27           D
ATOM      8 DG12BVAL A   7      15.776  10.049  12.295  0.65 13.27           D
ATOM      9 DG13BVAL A   7      17.656   9.940  12.381  0.65 13.27           D
"""

pdb_list = [pdb_str_01, pdb_str_02, pdb_str_03, pdb_str_04, pdb_str_05,
  pdb_str_06, pdb_str_07, pdb_str_08, pdb_str_09, pdb_str_10, pdb_str_11,
  pdb_str_12]
#
pdb_list_name = ['pdb_str_01', 'pdb_str_02', 'pdb_str_03', 'pdb_str_04', 'pdb_str_05',
  'pdb_str_06', 'pdb_str_07', 'pdb_str_08', 'pdb_str_09', 'pdb_str_10', 'pdb_str_11',
  'pdb_str_12']

#pdb_list = [pdb_str_02]
#pdb_list_name = ['pdb_str_02']

def run():
  #for idealize in [True, False]:
  for pdb_str, str_name in zip(pdb_list,pdb_list_name):
      #print 'pdb_string:', str_name, 'idealize =', idealize
    exercise(pdb_str=pdb_str, eps=1.e-4)


if (__name__ == "__main__"):
  t0 = time.time()
  run()
  #run(sys.argv[1:])
  print "OK. Time:", round(time.time()-t0, 2), "seconds"
