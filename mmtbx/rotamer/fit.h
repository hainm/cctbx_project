#ifndef MMTBX_ROTAMER_H
#define MMTBX_ROTAMER_H

#include <boost/python/list.hpp>
#include <boost/python/detail/api_placeholder.hpp>
#include <boost/python/extract.hpp>
#include <cctbx/maptbx/real_space_gradients_simple.h>
#include <scitbx/math/fast_approx_math.h>
#include <scitbx/math/rotate_around_axis.h>
#include <scitbx/vec3.h>
#include <cctbx/maptbx/eight_point_interpolation.h>

namespace mmtbx { namespace rotamer {
namespace af=scitbx::af;

template <typename FloatType=double>
class fit {
public:
  af::shared<af::shared<std::size_t> > axes;
  af::shared<af::shared<std::size_t> > rotatable_points_indices;
  af::shared<af::shared<FloatType> > angles_array;
  af::shared<scitbx::vec3<FloatType> > all_points_result;
  FloatType score_;

  fit() {}

  fit(
    FloatType target_value,
    boost::python::list const& axes_,
    boost::python::list const& rotatable_points_indices_,
    boost::python::list const& angles_array_,
    af::const_ref<FloatType, af::c_grid_padded<3> > const& density_map,
    af::shared<scitbx::vec3<FloatType> > all_points,
    cctbx::uctbx::unit_cell const& unit_cell,
    af::const_ref<std::size_t> const& selection,
    af::const_ref<FloatType> const& sin_table,
    af::const_ref<FloatType> const& cos_table,
    FloatType const& step,
    int const& n)
  :
  score_(target_value)
  {
    SCITBX_ASSERT(boost::python::len(axes_)==
                  boost::python::len(rotatable_points_indices_));
    for(std::size_t i=0;i<boost::python::len(axes_);i++) {
      axes.push_back(
        boost::python::extract<af::shared<std::size_t > >(axes_[i])());
      rotatable_points_indices.push_back(
        boost::python::extract<af::shared<std::size_t> >(
          rotatable_points_indices_[i])());
    }
    for(std::size_t i=0;i<boost::python::len(angles_array_);i++) {
      angles_array.push_back(
        boost::python::extract<af::shared<FloatType> >(angles_array_[i])());
    }
    for(std::size_t j=0;j<angles_array.size();j++) {
      af::shared<FloatType> angles = angles_array[j];
      af::shared<scitbx::vec3<FloatType> > all_points_cp = all_points.deep_copy();
      for(std::size_t i=0;i<angles.size();i++) {
       scitbx::math::rotate_points_around_axis(
          axes[i][0],
          axes[i][1],
          all_points_cp.ref(),
          rotatable_points_indices[i].const_ref(),
          angles[i],
          sin_table,
          cos_table,
          step,
          n);
      }
      FloatType mv = cctbx::maptbx::real_space_target_simple<FloatType, FloatType>(
        unit_cell,
        density_map,
        all_points_cp.ref(),
        selection);
      if(mv>score_) {
        all_points_result = all_points_cp.deep_copy();
        score_ = mv;
      }
    }
  }

  fit(
    af::shared<scitbx::vec3<double> > const& sites_cart_start,
    boost::python::list const& axes_,
    boost::python::list const& rotatable_points_indices_,
    boost::python::list const& angles_array_,
    af::shared<scitbx::vec3<double> > all_points,
    af::const_ref<double> const& sin_table,
    af::const_ref<double> const& cos_table,
    double const& step,
    int const& n)
  {
    SCITBX_ASSERT(boost::python::len(axes_)==
                  boost::python::len(rotatable_points_indices_));
    for(std::size_t i=0;i<boost::python::len(axes_);i++) {
      axes.push_back(
        boost::python::extract<af::shared<std::size_t > >(axes_[i])());
      rotatable_points_indices.push_back(
        boost::python::extract<af::shared<std::size_t> >(
          rotatable_points_indices_[i])());
    }
    for(std::size_t i=0;i<boost::python::len(angles_array_);i++) {
      angles_array.push_back(
        boost::python::extract<af::shared<double> >(angles_array_[i])());
    }
    double mv_best = 1.e+9;//target_value;
    for(std::size_t j=0;j<angles_array.size();j++) {
      af::shared<double> angles = angles_array[j];
      af::shared<scitbx::vec3<double> > all_points_cp = all_points.deep_copy();
      for(std::size_t i=0;i<angles.size();i++) {
       scitbx::math::rotate_points_around_axis(
          axes[i][0],
          axes[i][1],
          all_points_cp.ref(),
          rotatable_points_indices[i].const_ref(),
          angles[i],
          sin_table,
          cos_table,
          step,
          n);
      }
      double mv = 0;
      for(std::size_t i=0;i<all_points_cp.size();i++) {
        scitbx::vec3<double> delta = all_points_cp[i]-sites_cart_start[i];
        mv += std::sqrt(delta[0]*delta[0]+delta[1]*delta[1]+delta[2]*delta[2]);
      }
      if(mv<mv_best) {
        all_points_result = all_points_cp.deep_copy();
        mv_best = mv;
      }
    }
  }

  af::shared<scitbx::vec3<double> > result() { return all_points_result; }

  FloatType score() { return score_;}

};

}} // namespace mmtbx::rotamer

#endif // MMTBX_ROTAMER_H
