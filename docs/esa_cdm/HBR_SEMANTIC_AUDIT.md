# HBR_SEMANTIC_AUDIT

## Decision

The conversion `HBR = (t_span + c_span) / 2` is used, with the result converted
from metres to kilometres before TC-SSSAO R5--R8 evaluation.

## Evidence

- The official Kelvins data dictionary defines `x_span` as the size used by the
  collision-risk algorithm and explicitly states that a minimum **2 m diameter**
  is assumed for the chaser.
- The peer-reviewed dataset paper describes `t_span` as the target-satellite
  size used by the collision-risk computation and later explicitly calls it the
  satellite **diameter**.
- TC-SSSAO defines combined hard-body radius as the sum of the two object radii.

Thus each span is treated as a diameter, and the combined radius equals half of
their sum. No HBR is imputed when either span is missing, non-finite, or
non-positive; such rows are rejected by Preflight and disclosed in coverage.

Sources: [ESA Kelvins data dictionary](https://kelvins.esa.int/collision-avoidance-challenge/data/),
[Uriot et al., Astrodynamics, DOI 10.1007/s42064-021-0101-5](https://doi.org/10.1007/s42064-021-0101-5).

