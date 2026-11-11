# TEMPORAL_COMPATIBILITY_AUDIT

## Finding

The anonymised ESA release replaces absolute CDM creation and TCA timestamps
with `time_to_tca` in days. Therefore no truthful `xsd:dateTime` value is
available for these records.

## Current policy

- Do not manufacture absolute dates.
- Within one `event_id`, sort by decreasing `time_to_tca`: a larger value is an
  earlier CDM and a smaller value is a later update closer to TCA.
- Keep relative time as provenance metadata in the ESA adapter namespace.
- Execute B3 in the import/execution layer with exactly the locked adjacency and
  severity-increase semantics. Every source row participates in adjacency, so
  an unrated row cannot be skipped.
- Partition temporal processing by `event_id`; do not run v1 R1's global
  all-event comparison on this large relative-time dataset.

This is an execution strategy, not a change to R1, B3, OWL schema, or their
scientific meaning. A future schema version may introduce a general relative
assessment-time model after independent design review.

