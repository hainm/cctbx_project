from __future__ import division
import math
from scitbx import matrix
from cctbx import miller
from dials.array_family import flex
from scitbx.math.tests.tst_weighted_correlation import simple_weighted_correlation
from xfel.cxi.postrefinement_legacy_rs import rs_parameterization
from xfel.cxi.postrefinement_updated_rs import rs2_refinery,lbfgs_minimizer_derivatives,chosen_weights
from scitbx.lstbx import normal_eqns
from scitbx.lstbx import normal_eqns_solving

class rs_hybrid(object):
  def __init__(self,measurements_orig, params, i_model, miller_set, result, out):
    measurements = measurements_orig.deep_copy()
    # Now manipulate the data to conform to unit cell, asu, and space group
    # of reference.  The resolution will be cut later.
    # Only works if there is NOT an indexing ambiguity!
    observations = measurements.customized_copy(
      anomalous_flag=not params.merge_anomalous,
      crystal_symmetry=miller_set.crystal_symmetry()
      ).map_to_asu()

    observations_original_index = measurements.customized_copy(
      anomalous_flag=not params.merge_anomalous,
      crystal_symmetry=miller_set.crystal_symmetry()
      )

    # Ensure that match_multi_indices() will return identical results
    # when a frame's observations are matched against the
    # pre-generated Miller set, self.miller_set, and the reference
    # data set, self.i_model.  The implication is that the same match
    # can be used to map Miller indices to array indices for intensity
    # accumulation, and for determination of the correlation
    # coefficient in the presence of a scaling reference.

    assert len(i_model.indices()) == len(miller_set.indices()) \
        and  (i_model.indices() ==
              miller_set.indices()).count(False) == 0
    matches = miller.match_multi_indices(
      miller_indices_unique=miller_set.indices(),
      miller_indices=observations.indices())

    pair1 = flex.int([pair[1] for pair in matches.pairs()])
    pair0 = flex.int([pair[0] for pair in matches.pairs()])
    # narrow things down to the set that matches, only
    observations_pair1_selected = observations.customized_copy(
      indices = flex.miller_index([observations.indices()[p] for p in pair1]),
      data = flex.double([observations.data()[p] for p in pair1]),
      sigmas = flex.double([observations.sigmas()[p] for p in pair1]),
    )
    observations_original_index_pair1_selected = observations_original_index.customized_copy(
      indices = flex.miller_index([observations_original_index.indices()[p] for p in pair1]),
      data = flex.double([observations_original_index.data()[p] for p in pair1]),
      sigmas = flex.double([observations_original_index.sigmas()[p] for p in pair1]),
    )
###################
    I_observed = observations_pair1_selected.data()
    chosen = chosen_weights(observations_pair1_selected, params)

    MILLER = observations_original_index_pair1_selected.indices()
    ORI = result["current_orientation"][0]
    Astar = matrix.sqr(ORI.reciprocal_matrix())
    WAVE = result["wavelength"]
    BEAM = matrix.col((0.0,0.0,-1./WAVE))
    BFACTOR = 0.

    #calculation of correlation here
    I_reference = flex.double([i_model.data()[pair[0]] for pair in matches.pairs()])
    use_weights = False # New facility for getting variance-weighted correlation

    if use_weights:
       #variance weighting
      I_weight = flex.double(
        [1./(observations_pair1_selected.sigmas()[pair[1]])**2 for pair in matches.pairs()])
    else:
      I_weight = flex.double(len(observations_pair1_selected.sigmas()), 1.)

    """Explanation of 'include_negatives' semantics as originally implemented in cxi.merge postrefinement:
       include_negatives = True
       + and - reflections both used for Rh distribution for initial estimate of RS parameter
       + and - reflections both used for calc/obs correlation slope for initial estimate of G parameter
       + and - reflections both passed to the refinery and used in the target function (makes sense if
                           you look at it from a certain point of view)

       include_negatives = False
       + and - reflections both used for Rh distribution for initial estimate of RS parameter
       +       reflections only used for calc/obs correlation slope for initial estimate of G parameter
       + and - reflections both passed to the refinery and used in the target function (makes sense if
                           you look at it from a certain point of view)
    """
    if params.include_negatives:
      SWC = simple_weighted_correlation(I_weight, I_reference, I_observed)
    else:
      non_positive = ( observations_pair1_selected.data() <= 0 )
      SWC = simple_weighted_correlation(I_weight.select(~non_positive),
            I_reference.select(~non_positive), I_observed.select(~non_positive))

    print >> out, "Old correlation is", SWC.corr
    assert params.postrefinement.algorithm=="rs_hybrid"
    Rhall = flex.double()
    for mill in MILLER:
        H = matrix.col(mill)
        Xhkl = Astar*H
        Rh = ( Xhkl + BEAM ).length() - (1./WAVE)
        Rhall.append(Rh)
    Rs = math.sqrt(flex.mean(Rhall*Rhall))

    RS = 1./10000. # reciprocal effective domain size of 1 micron
    RS = Rs        # try this empirically determined approximate, monochrome, a-mosaic value

    self.rs2_current = flex.double([SWC.slope, BFACTOR, RS, 0., 0.])
    self.rs2_parameterization_class = rs_parameterization

    self.rs2_refinery = rs2_refinery(ORI=ORI, MILLER=MILLER, BEAM=BEAM, WAVE=WAVE,
        ICALCVEC = I_reference, IOBSVEC = I_observed, WEIGHTS = chosen)
    self.nave1_refinery = nave1_refinery(ORI=ORI, MILLER=MILLER, BEAM=BEAM, WAVE=WAVE,
        ICALCVEC = I_reference, IOBSVEC = I_observed, WEIGHTS = chosen)

    self.out=out; self.params = params;
    self.miller_set = miller_set
    self.observations_pair1_selected = observations_pair1_selected;
    self.observations_original_index_pair1_selected = observations_original_index_pair1_selected
    self.i_model = i_model

  def run_plain(self):
    self.MINI = lbfgs_minimizer_derivatives( current_x = self.rs2_current,
        parameterization = self.rs2_parameterization_class, refinery = self.rs2_refinery,
        out = self.out )

    self.refined_mini = self.MINI
    values = self.rs2_parameterization_class(self.MINI.x)
    self.nave1_current = flex.double(
      [values.G, values.BFACTOR, values.RS, values.thetax*1000., values.thetay*1000.])
    self.nave1_parameterization_class = nave1_parameterization
    self.MINI2 = per_frame_helper( current_x = self.nave1_current,
        parameterization = self.nave1_parameterization_class, refinery = self.nave1_refinery,
        out = self.out )
    print >>self.out, "Trying Lev-Mar2"
    iterations = normal_eqns_solving.naive_iterations(non_linear_ls = self.MINI2,
        step_threshold = 0.0001,
        gradient_threshold = 1.E-10)
    self.refined_mini = self.MINI2
    self.refinery = self.nave1_refinery # used elsewhere, not private interface

  def result_for_cxi_merge(self, file_name):
    scaler = self.nave1_refinery.scaler_callable(self.get_parameter_values())
    values = self.get_parameter_values()
    partiality_array = self.refinery.get_partiality_array(values)
    p_scaler = flex.pow(partiality_array,
                        0.5*self.params.postrefinement.merge_partiality_exponent)

    fat_selection = (self.nave1_refinery.lorentz_callable(self.get_parameter_values()) >
                     self.params.postrefinement.rs_hybrid.partiality_threshold) # was 0.2 for rs2
    fat_count = fat_selection.count(True)

    #avoid empty database INSERT, if insufficient centrally-located Bragg spots:
    # in samosa, handle this at a higher level, but handle it somehow.
    if fat_count < 3:
      raise ValueError
    print >> self.out, "On total %5d the fat selection is %5d"%(
      len(self.observations_pair1_selected.indices()), fat_count)
    observations_original_index = \
      self.observations_original_index_pair1_selected.select(fat_selection)

    observations = self.observations_pair1_selected.customized_copy(
      indices = self.observations_pair1_selected.indices().select(fat_selection),
      data = (self.observations_pair1_selected.data()/scaler).select(fat_selection),
      sigmas = (self.observations_pair1_selected.sigmas()/(scaler * p_scaler)).select(fat_selection)
    )
    matches = miller.match_multi_indices(
      miller_indices_unique=self.miller_set.indices(),
      miller_indices=observations.indices())

    I_weight = flex.double(len(observations.sigmas()), 1.)
    I_reference = flex.double([self.i_model.data()[pair[0]] for pair in matches.pairs()])
    SWC = simple_weighted_correlation(I_weight, I_reference, observations.data())
    print >> self.out, "CORR: NEW correlation is", SWC.corr
    self.final_corr = SWC.corr

    # New range assertions for refined variables
    # XXX Likely these limits are problem-specific (especially G-max) so look for another approach
    #     or expose the limits as phil parameters.
    assert self.final_corr > 0.1
    assert 0 < values.G and values.G < 0.5
    assert -25 < values.BFACTOR and values.BFACTOR < 25

    return observations_original_index,observations,matches

  def result_for_samosa(self):
    values = self.get_parameter_values()
    return self.refinery.get_eff_Astar(values), values.RS, self.refinery.get_partiality_array(values)

  def get_parameter_values(self):
    return self.refined_mini.parameterization(self.refined_mini.x)

class nave1_refinery(rs2_refinery):

    def jacobian_callable(self,values):
      PB = self.get_partiality_array(values)
      EXP = flex.exp(-2.*values.BFACTOR*self.DSSQ)
      G_terms = (EXP * PB * self.ICALCVEC)
      B_terms = (values.G * EXP * PB * self.ICALCVEC)*(-2.*self.DSSQ)
      P_terms = (values.G * EXP * self.ICALCVEC)

      thetax = values.thetax; thetay = values.thetay;
      Rx = matrix.col((1,0,0)).axis_and_angle_as_r3_rotation_matrix(thetax)
      dRx_dthetax = matrix.col((1,0,0)).axis_and_angle_as_r3_derivative_wrt_angle(thetax)
      Ry = matrix.col((0,1,0)).axis_and_angle_as_r3_rotation_matrix(thetay)
      dRy_dthetay = matrix.col((0,1,0)).axis_and_angle_as_r3_derivative_wrt_angle(thetay)
      ref_ori = matrix.sqr(self.ORI.reciprocal_matrix())
      miller_vec = self.MILLER.as_vec3_double()
      ds1_dthetax = flex.mat3_double(len(self.MILLER),Ry * dRx_dthetax * ref_ori) * miller_vec
      ds1_dthetay = flex.mat3_double(len(self.MILLER),dRy_dthetay * Rx * ref_ori) * miller_vec

      s1vec = self.get_s1_array(values)
      s1lenvec = flex.sqrt(s1vec.dot(s1vec))
      dRh_dthetax = s1vec.dot(ds1_dthetax)/s1lenvec
      dRh_dthetay = s1vec.dot(ds1_dthetay)/s1lenvec
      rs = values.RS
      Rh = self.get_Rh_array(values)
      rs_sq = rs*rs
      denomin = (2. * Rh * Rh + rs_sq)
      dPB_dRh = -PB * 4. * Rh / denomin
      dPB_dthetax = dPB_dRh * dRh_dthetax
      dPB_dthetay = dPB_dRh * dRh_dthetay
      Px_terms = P_terms * dPB_dthetax /1000.; Py_terms = P_terms * dPB_dthetay /1000.

      dPB_drs = 4 * rs * Rh * Rh / (denomin * denomin)
      Prs_terms = P_terms * dPB_drs

      return [G_terms,B_terms,Prs_terms,Px_terms,Py_terms]

class nave1_parameterization(rs_parameterization):
  def __getattr__(YY,item):
    if item=="thetax" : return YY.reference[3]/1000. #internally kept in milliradians
    if item=="thetay" : return YY.reference[4]/1000.
    if item=="G" :      return YY.reference[0]
    if item=="BFACTOR": return YY.reference[1]
    if item=="RS":      return YY.reference[2]
    return getattr(YY,item)

class per_frame_helper(normal_eqns.non_linear_ls, normal_eqns.non_linear_ls_mixin):
  def __init__(pfh,current_x=None, parameterization=None, refinery=None, out=None,):
    pfh.parameterization = parameterization
    pfh.refinery = refinery
    pfh.out = out
    super(per_frame_helper, pfh).__init__(n_parameters=current_x.size())
    pfh.n = current_x.size()
    pfh.x_0 = current_x
    pfh.restart()

  def restart(pfh):
    pfh.x = pfh.x_0.deep_copy()
    pfh.old_x = None

  def step_forward(pfh):
    pfh.old_x = pfh.x.deep_copy()
    pfh.x += pfh.step()

  def step_backward(pfh):
    assert pfh.old_x is not None
    pfh.x, pfh.old_x = pfh.old_x, None

  def parameter_vector_norm(pfh):
    return pfh.x.norm()

  def build_up(pfh, objective_only=False):
    values = pfh.parameterization(pfh.x)
    # XXX revisit these limits.  Seems like an ad hoc approach to have to set these limits
    #     Moreover, these tests throw out ~30% of LM14 data, thus search for another approach
    assert -150. < values.BFACTOR < 150. ,"limits on the exponent, please"
    assert -0.5 < 180.*values.thetax/math.pi < 0.5 , "limits on the theta rotation, please"
    assert -0.5 < 180.*values.thetay/math.pi < 0.5 , "limits on the theta rotation, please"
    assert 0.000001 < values.RS < 0.0003 , "limits on the RLP size, please"
    residuals = pfh.refinery.fvec_callable(values)
    pfh.reset()
    if objective_only:
      pfh.add_residuals(residuals, weights=pfh.refinery.WEIGHTS)
    else:
      grad_r = pfh.refinery.jacobian_callable(values)
      jacobian = flex.double(
        flex.grid(len(pfh.refinery.MILLER), pfh.n_parameters))
      for j, der_r in enumerate(grad_r):
        jacobian.matrix_paste_column_in_place(der_r,j)
        #print >> pfh.out, "COL",j, list(der_r)
      pfh.add_equations(residuals, jacobian, weights=pfh.refinery.WEIGHTS)
    print >> pfh.out, "rms %10.3f"%math.sqrt(flex.mean(pfh.refinery.WEIGHTS*residuals*residuals)),
    values.show(pfh.out)
