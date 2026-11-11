# R1_SCALABILITY_ANALYSIS

The current R1 SPARQL rule compares all pairs of `SpaceEvent` instances with
occurrence times, so its candidate matching can grow as `O(N^2)` before filters.
For ESA CDM replay this would create many cross-encounter temporal edges with no
value for B3.

The current implementation leaves R1 unchanged and applies option A from the task specification:
execution-layer partitioning by encounter (`event_id`). Sorting each group costs
`O(n_i log n_i)` and adjacency traversal costs `O(n_i)`, giving
`O(sum_i n_i log n_i)` over encounters. R3/R4 are not claimed as real-data
validated because the anonymous dataset lacks a complete manoeuvre-to-approach
causal chain.

No rule change plan is submitted because neither R1 nor the schema is modified.

