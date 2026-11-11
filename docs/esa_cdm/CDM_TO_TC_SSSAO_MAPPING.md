# CDM_TO_TC_SSSAO_MAPPING

| ESA field/entity | TC-SSSAO representation | Transformation and scope |
|---|---|---|
| `event_id` | one event-scoped `ApproachEvent` context | One encounter context, not one encounter per CDM |
| each CDM row | `ObservationData`, normalized `AssessmentData`, and one `CollisionRiskEvent` snapshot |
| target/chaser | `hasPrimaryObject` / `hasSecondaryObject` |
| `risk` | `hasCollisionProbability` |
| `miss_distance` | `hasPredictedMissDistance` |
| `t_span`, `c_span` | `hasCombinedHardBodyRadius` |
| `time_to_tca` | execution-layer relative order and provenance literal |
| covariance fields | `AssessmentData` provenance metadata |
| `obs_available`, `obs_used`, `weighted_rms`, OD spans | assessment quality metadata |

The adapter retains the TC-SSSAO schema. Dataset-specific provenance
predicates use the `https://w3id.org/tc-sssao/esa-cdm-v1#` namespace and are not
declared as new ontology-schema properties.

