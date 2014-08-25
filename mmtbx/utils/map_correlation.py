from __future__ import division
from libtbx import adopt_init_args
from scitbx.array_family import flex
import mmtbx.map_tools
from cctbx import maptbx
from cctbx import miller

class Map_correlation(object):

  def __init__(self,
        xray_structure=None,
        fmodel=None,
        map_data=None,
        d_min=None):
    """  Creates data and model maps for correlation calculations   """
    assert [fmodel, map_data].count(None) == 1
    if(map_data is not None): assert [d_min, xray_structure].count(None) == 0
    adopt_init_args(self, locals())
    # get map_data defined
    if(self.fmodel is not None):
      mc = mmtbx.map_tools.electron_density_map(
        fmodel=self.fmodel).map_coefficients(
          map_type         = "2mFo-DFc",
          isotropize       = True,
          fill_missing     = False)
      crystal_gridding = self.fmodel.f_obs().crystal_gridding(
        d_min              = self.fmodel.f_obs().d_min(),
        resolution_factor  = 1./3)
      fft_map = miller.fft_map(
        crystal_gridding     = crystal_gridding,
        fourier_coefficients = mc)
      self.map_data = fft_map.real_map_unpadded()
    # get model map
    if(self.fmodel is not None):
      f_model = self.fmodel.f_model_scaled_with_k1()
      fft_map = miller.fft_map(
        crystal_gridding     = crystal_gridding,
        fourier_coefficients = f_model)
      self.map_model = fft_map.real_map_unpadded()
    else:
      crystal_gridding = maptbx.crystal_gridding(
        unit_cell             = self.xray_structure.unit_cell(),
        space_group_info      = self.xray_structure.space_group_info(),
        pre_determined_n_real = self.map_data.accessor().all())
      f_model = self.xray_structure.structure_factors(d_min=self.d_min).f_calc()
      fft_map = miller.fft_map(
        crystal_gridding     = crystal_gridding,
        fourier_coefficients = f_model)
      self.map_model = fft_map.real_map_unpadded()
    # compute map cc per selected atoms
    if(self.fmodel is not None):
      self.sites_cart = self.fmodel.xray_structure.sites_cart()
    else:
      self.sites_cart = self.xray_structure.sites_cart()

  def calc_correlation_coefficient(self,selections):
    """
    Calculates the correlation of selected atoms to the density map

    Args:
    -----
      selections (list of flex.size_t): Atoms selections

    Returns:
    --------
      cc (list of float): list of correlation values
    """
    assert isinstance(selections,list)
    cc = []
    for selection in selections:
      sites_cart_ = self.sites_cart.select(selection)
      sel = maptbx.grid_indices_around_sites(
        unit_cell  = self.xray_structure.unit_cell(),
        fft_n_real = self.map_data.focus(),
        fft_m_real = self.map_data.all(),
        sites_cart = sites_cart_,
        site_radii = flex.double(sites_cart_.size(), 2.0))
      cc.append(flex.linear_correlation(
        x=self.map_data.select(sel).as_1d(),
        y=self.map_model.select(sel).as_1d()).coefficient())
    return cc
