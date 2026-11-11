"""TC-SSSAO Rule Input Preflight Test Suite.

Full fixture suite for the production P1–P29 contract, plus B3 and dual evidence.
Historical fixture/docstring labels P1–P31 differ from production check IDs;
production IDs are those in scripts/validate/check_rule_input_preflight.py.
Negative numeric/config cases call that checker; SHACL integrity cases validate
real shapes. No negative case relies on an unrelated stable-IRI violation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace, RDF, URIRef

# Project paths
BASE = Path(__file__).resolve().parents[1]
OWL_FILE = BASE / "ontology" / "tc_sssao.owl"
RULES_FILE = BASE / "rules" / "tc_sssao_rules.ttl"
RULE_CONFIG_FILE = BASE / "rules" / "tc_sssao_rule_config.ttl"
CAUSAL_SHAPE_FILE = BASE / "rules" / "tc_sssao_causal_assertion_integrity.ttl"
STATE_TRANS_SHAPE_FILE = BASE / "rules" / "tc_sssao_state_transition_integrity.ttl"
SEVERITY_SHAPE_FILE = BASE / "rules" / "tc_sssao_severity_rank_shape.ttl"
SPATIAL_PAIR_SHAPE_FILE = BASE / "rules" / "tc_sssao_spatial_pair_shape.ttl"
STABLE_IRI_SHAPE_FILE = BASE / "rules" / "tc_sssao_stable_iri_shape.ttl"

FIXTURES_DIR = Path(__file__).parent / "fixtures"

ONTO = Namespace("https://w3id.org/tc-sssao#")
BT = Namespace("https://w3id.org/tc-sssao/data/boundary-test#")


def derived_state(kind: str, event_iri: str) -> URIRef:
    """Compute derived state IRI from event IRI using SHA256 hash."""
    digest = hashlib.sha256(event_iri.encode("utf-8")).hexdigest().lower()
    return URIRef(f"https://w3id.org/tc-sssao#derived_{kind}_state_{digest}")


def load_ontology() -> Graph:
    """Load the main OWL ontology."""
    g = Graph()
    g.parse(OWL_FILE.as_uri(), format="xml")
    return g


def load_rules() -> Graph:
    """Load the SHACL rules graph."""
    g = Graph()
    g.parse(RULES_FILE.as_uri(), format="turtle")
    return g


def load_rule_config() -> Graph:
    """Load the rule deployment configuration."""
    g = Graph()
    g.parse(RULE_CONFIG_FILE.as_uri(), format="turtle")
    return g


def load_extra_shapes() -> Graph:
    """Load additional SHACL shape graphs."""
    g = Graph()
    g.parse(CAUSAL_SHAPE_FILE.as_uri(), format="turtle")
    g.parse(STATE_TRANS_SHAPE_FILE.as_uri(), format="turtle")
    g.parse(SEVERITY_SHAPE_FILE.as_uri(), format="turtle")
    g.parse(SPATIAL_PAIR_SHAPE_FILE.as_uri(), format="turtle")
    g.parse(STABLE_IRI_SHAPE_FILE.as_uri(), format="turtle")
    return g


def run_shacl_validation(
    data_graph: Graph,
    shacl_graph: Graph | None = None,
    ontology_graph: Graph | None = None,
) -> tuple[bool, Graph, str]:
    """Run SHACL validation and return (conforms, report_graph, report_text)."""
    if shacl_graph is None:
        shacl_graph = load_rules()
    if ontology_graph is None:
        ontology_graph = load_ontology()

    # Merge ontology and config into data graph
    merged = data_graph + ontology_graph + _load_rule_config()

    conforms, report_graph, report_text = validate(
        data_graph=merged,
        shacl_graph=shacl_graph,
        ont_graph=None,
        inference="rdfs",
        advanced=True,
        inplace=False,
        debug=False,
    )
    return conforms, report_graph, report_text


def _load_rule_config() -> Graph:
    """Load the rule deployment configuration (θ parameters for R5—R8)."""
    g = Graph()
    g.parse(RULE_CONFIG_FILE.as_uri(), format="turtle")
    return g


def count_violations(report_graph: Graph) -> int:
    """Count violations in SHACL report."""
    NS_SH = Namespace("http://www.w3.org/ns/shacl#")
    return sum(1 for _ in report_graph.subjects(RDF.type, NS_SH.Violation))


def count_rule_deployment_configs(data_graph: Graph) -> int:
    """Count RuleDeploymentConfiguration instances in data graph."""
    return sum(
        1
        for _ in data_graph.subjects(
            RDF.type, ONTO.RuleDeploymentConfiguration
        )
    )


# =============================================================================
# Config Tests (P1-P3)
# =============================================================================


def test_config_zero_instances_fail():
    """Verify the production preflight, including rejection/acceptance status."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p1_zero_config.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_config_singleton({"config": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_config_one_instance_pass():
    """Verify the production preflight, including rejection/acceptance status."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p2_one_config.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_config_singleton({"config": data})
    assert preflight.EXIT_CODE == 0
    assert any(row["status"] == "PASS" for row in preflight.RESULTS)


def test_config_two_instances_fail():
    """The official preflight must reject the controlled P3 violation."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p3_two_configs.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_config_singleton({"config": data})
    assert any(x["check_id"] == "P3" and x["status"] == "FAIL"
               for x in preflight.RESULTS), preflight.RESULTS
    assert preflight.EXIT_CODE == 1


def test_thetaA_negative_fail():
    """The official preflight must reject the controlled P4 violation."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p4_thetaA_negative.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_thresholds({"config": data})
    assert any(x["check_id"] == "P4" and x["status"] == "FAIL"
               for x in preflight.RESULTS), preflight.RESULTS
    assert preflight.EXIT_CODE == 1


def test_thetaM_greater_than_1_fail():
    """The official preflight must reject the controlled P5 violation."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p5_thetaM_gt_1.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_thresholds({"config": data})
    assert any(x["check_id"] == "P5" and x["status"] == "FAIL"
               for x in preflight.RESULTS), preflight.RESULTS
    assert preflight.EXIT_CODE == 1


def test_thetaA_equals_thetaM_fail():
    """The official preflight must reject the controlled P6 violation."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p6_thetaA_eq_thetaM.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_thresholds({"config": data})
    assert any(x["check_id"] == "P6" and x["status"] == "FAIL"
               for x in preflight.RESULTS), preflight.RESULTS
    assert preflight.EXIT_CODE == 1


def test_thetaA_greater_than_thetaM_fail():
    """The official preflight must reject the controlled P7 violation."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p7_thetaA_gt_thetaM.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_thresholds({"config": data})
    assert any(x["check_id"] == "P7" and x["status"] == "FAIL"
               for x in preflight.RESULTS), preflight.RESULTS
    assert preflight.EXIT_CODE == 1


def test_normal_thresholds_pass():
    """Verify the production preflight, including rejection/acceptance status."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p8_normal_thresholds.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_thresholds({"config": data})
    assert preflight.EXIT_CODE == 0
    assert any(row["status"] == "PASS" for row in preflight.RESULTS)


def test_Pc_multivalued_fail():
    """Invalid numeric input must fail the production P1–P29 checker."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p9_pc_multivalued.ttl").as_uri(), format="turtle")
    # Pc validation applies to assessment/prediction evidence (formal input contract).
    data.add((ONTO.Obs, RDF.type, ONTO.AssessmentData))
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_collision_probability({"ontology": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_Pc_negative_fail():
    """Invalid numeric input must fail the production P1–P29 checker."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p10_pc_negative.ttl").as_uri(), format="turtle")
    # Pc validation applies to assessment/prediction evidence (formal input contract).
    data.add((ONTO.Obs, RDF.type, ONTO.AssessmentData))
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_collision_probability({"ontology": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_Pc_greater_than_1_fail():
    """Invalid numeric input must fail the production P1–P29 checker."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p11_pc_gt_1.ttl").as_uri(), format="turtle")
    # Pc validation applies to assessment/prediction evidence (formal input contract).
    data.add((ONTO.Obs, RDF.type, ONTO.AssessmentData))
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_collision_probability({"ontology": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_Pc_valid_pass():
    """P12: Valid Pc (0 < Pc <= 1) -> should PASS."""
    fixture = FIXTURES_DIR / "p12_pc_valid.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert conforms, "Valid Pc should pass"


# =============================================================================
# MissDistance Tests (P13-P14)
# =============================================================================


def test_missDistance_multivalued_fail():
    """Invalid numeric input must fail the production P1–P29 checker."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p13_miss_multivalued.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_miss_distance({"ontology": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_missDistance_negative_fail():
    """Invalid numeric input must fail the production P1–P29 checker."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p14_miss_negative.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_miss_distance({"ontology": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_HBR_multivalued_fail():
    """Invalid numeric input must fail the production P1–P29 checker."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p15_hbr_multivalued.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_hbr({"ontology": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_HBR_zero_fail():
    """Invalid numeric input must fail the production P1–P29 checker."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p16_hbr_zero.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_hbr({"ontology": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_HBR_negative_fail():
    """Invalid numeric input must fail the production P1–P29 checker."""
    from scripts.validate import check_rule_input_preflight as preflight
    data = Graph().parse((FIXTURES_DIR / "p17_hbr_negative.ttl").as_uri(), format="turtle")
    preflight.RESULTS.clear()
    preflight.EXIT_CODE = 0
    preflight.check_hbr({"ontology": data})
    assert preflight.EXIT_CODE == 1
    assert any(row["status"] == "FAIL" for row in preflight.RESULTS)


def test_primary_multivalued_fail():
    """P18: hasPrimaryObject multivalued -> should FAIL."""
    fixture = FIXTURES_DIR / "p18_primary_multivalued.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "Multivalued primary should fail"


def test_secondary_multivalued_fail():
    """P19: hasSecondaryObject multivalued -> should FAIL."""
    fixture = FIXTURES_DIR / "p19_secondary_multivalued.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "Multivalued secondary should fail"


def test_primary_equals_secondary_fail():
    """P20: hasPrimaryObject == hasSecondaryObject -> should FAIL."""
    fixture = FIXTURES_DIR / "p20_primary_eq_secondary.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "Primary == Secondary should fail"


# =============================================================================
# SeverityRank Tests (P21-P23)
# =============================================================================


def test_severity_rank_minus1_fail():
    """P21: hasSeverityRank = -1 -> should FAIL."""
    fixture = FIXTURES_DIR / "p21_severity_minus1.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "SeverityRank -1 should fail"


def test_severity_rank_4_fail():
    """P22: hasSeverityRank = 4 -> should FAIL."""
    fixture = FIXTURES_DIR / "p22_severity_4.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "SeverityRank 4 should fail"


def test_severity_rank_0_1_2_3_pass():
    """P23: Valid severity ranks (0,1,2,3) -> should PASS."""
    fixture = FIXTURES_DIR / "p23_severity_valid.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert conforms, "Valid severity ranks should pass"


# =============================================================================
# CausalAssertion Tests (P24-P26)
# =============================================================================


def test_causalAssertion_missing_evidence_fail():
    """P24: CausalAssertion missing hasCausalEvidence -> should FAIL."""
    fixture = FIXTURES_DIR / "p24_causal_missing_evidence.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "Missing causal evidence should fail"


def test_causalAssertion_two_effects_fail():
    """P25: CausalAssertion with two effects (maxCount=1) -> should FAIL."""
    fixture = FIXTURES_DIR / "p25_causal_two_effects.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "Two effects should fail"


def test_causalAssertion_complete_pass():
    """P26: Complete CausalAssertion -> should PASS."""
    fixture = FIXTURES_DIR / "p26_causal_complete.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert conforms, "Complete CausalAssertion should pass"


# =============================================================================
# StateTransition Tests (P27-P29)
# =============================================================================


def test_stateTransition_missing_trigger_fail():
    """P27: StateTransition missing triggeredByEvent -> should FAIL."""
    fixture = FIXTURES_DIR / "p27_transition_missing_trigger.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "Missing trigger should fail"


def test_stateTransition_two_targets_fail():
    """P28: StateTransition with two target states -> should FAIL."""
    fixture = FIXTURES_DIR / "p28_transition_two_targets.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "Two targets should fail"


def test_stateTransition_complete_pass():
    """P29: Complete StateTransition -> should PASS."""
    fixture = FIXTURES_DIR / "p29_transition_complete.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert conforms, "Complete StateTransition should pass"


# =============================================================================
# StableIRI Tests (P30-P31)
# =============================================================================


def test_collisionRisk_blank_node_fail():
    """P30: CollisionRiskEvent with blank node -> should FAIL."""
    fixture = FIXTURES_DIR / "p30_blank_node_collision_risk.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "Blank node CollisionRiskEvent should fail"


def test_collisionRisk_named_iri_pass():
    """P31: CollisionRiskEvent with named IRI -> should PASS."""
    fixture = FIXTURES_DIR / "p31_named_iri_collision_risk.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert conforms, "Named IRI CollisionRiskEvent should pass"


# =============================================================================
# B3 Adjacency Regression Test
# =============================================================================


def test_b3_adjacency_with_unrated_middle_event():
    """B3: T1 rated -> T2 unrated -> T3 rated; T1->T3 transitsTo should be FALSE.

    Regression test: B3 should NOT generate transitsTo across an unrated
    middle event. The adjacency filter must prevent skipping.
    """
    fixture = FIXTURES_DIR / "b3_adjacency_unrated_middle.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    ontology = load_ontology()
    rules = load_rules()
    config = load_rule_config()

    # Merge all graphs
    merged = data + ontology + config

    # Fixed-point iteration: same as _run_b3_severity_test
    for _ in range(10):
        before = len(merged)
        conforms, _, _ = validate(
            data_graph=merged,
            shacl_graph=rules,
            ont_graph=None,
            inference="rdfs",
            advanced=True,
            inplace=True,
            debug=False,
        )
        if len(merged) == before:
            break

    # Check derived state IRIs
    t1_iri = str(BT.T1)
    t3_iri = str(BT.T3)

    normal_state_t1 = derived_state("normal", t1_iri)
    warning_state_t3 = derived_state("warning", t3_iri)

    # T1->T3 transitsTo should NOT exist because T2 breaks adjacency
    has_transits = (normal_state_t1, ONTO.transitsTo, warning_state_t3) in merged
    assert not has_transits, "T1->T3 should NOT have transitsTo (T2 breaks adjacency)"


# =============================================================================
# B3 Severity Direction Tests
# =============================================================================


def _run_b3_severity_test(
    fixture_name: str,
    t1_kind: str,
    t2_kind: str,
    expect_transits: bool,
    expect_degrades: bool = False,
    expect_recovers: bool = False,
):
    """Helper for B3 severity direction tests.

    Args:
        fixture_name: Test fixture TTL file name.
        t1_kind: Severity kind of T1 (normal/attention/warning/dangerous).
        t2_kind: Severity kind of T2.
        expect_transits: Whether transitsTo should be generated.
        expect_degrades: Whether degradesTo should be generated (Warning→Dangerous only).
        expect_recovers: Whether recoversTo should be generated (severity decrease only).
    """
    fixture = FIXTURES_DIR / fixture_name
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    ontology = load_ontology()
    rules = load_rules()
    config = load_rule_config()
    merged = data + ontology + config

    # Fixed-point iteration: B4/B3 rules need multiple passes to fire correctly.
    # Each iteration adds new triples (derived states, precedesEvent, leadsToState)
    # which serve as input to subsequent rule evaluations.
    for _ in range(10):
        before = len(merged)
        validate(
            data_graph=merged,
            shacl_graph=rules,
            ont_graph=None,
            inference="rdfs",
            advanced=True,
            inplace=True,
            debug=False,
        )
        if len(merged) == before:
            break

    t1_iri = str(BT.T1)
    t2_iri = str(BT.T2)

    state_t1 = derived_state(t1_kind, t1_iri)
    state_t2 = derived_state(t2_kind, t2_iri)

    has_transits = (state_t1, ONTO.transitsTo, state_t2) in merged
    has_degrades = (state_t1, ONTO.degradesTo, state_t2) in merged
    has_recovers = (state_t1, ONTO.recoversTo, state_t2) in merged

    assert has_transits == expect_transits, (
        f"transitsTo({t1_kind}->{t2_kind}) expected={expect_transits}, got={has_transits}"
    )
    assert has_degrades == expect_degrades, (
        f"degradesTo({t1_kind}->{t2_kind}) expected={expect_degrades}, got={has_degrades}"
    )
    assert has_recovers == expect_recovers, (
        f"recoversTo({t1_kind}->{t2_kind}) expected={expect_recovers}, got={has_recovers}"
    )


def test_b3_severity_increasing_normal_to_attention_pass():
    """B3: Normal -> Attention (increasing) -> transitsTo should be TRUE."""
    _run_b3_severity_test(
        "b3_severity_increasing_normal_attention.ttl",
        "normal",
        "attention",
        expect_transits=True,
        expect_degrades=False,
    )


def test_b3_severity_increasing_attention_to_warning_pass():
    """B3: Attention -> Warning (increasing) -> transitsTo should be TRUE."""
    _run_b3_severity_test(
        "b3_severity_increasing_attention_warning.ttl",
        "attention",
        "warning",
        expect_transits=True,
        expect_degrades=False,
    )


def test_b3_severity_increasing_warning_to_dangerous_pass():
    """B3: Warning -> Dangerous (increasing) -> transitsTo AND degradesTo TRUE."""
    _run_b3_severity_test(
        "b3_severity_increasing_warning_dangerous.ttl",
        "warning",
        "dangerous",
        expect_transits=True,
        expect_degrades=True,
    )


def test_b3_severity_decreasing_dangerous_to_warning():
    """B3: Dangerous -> Warning (decreasing) -> transitsTo AND recoversTo should be TRUE.

    With the recovery extension, severity decrease adjacent snapshots generate both
    transitsTo and recoversTo.
    """
    _run_b3_severity_test(
        "b3_no_automatic_decrease_dangerous_warning.ttl",
        "dangerous",
        "warning",
        expect_transits=True,
        expect_degrades=False,
        expect_recovers=True,
    )


def test_b3_severity_decreasing_warning_to_attention():
    """B3: Warning -> Attention (decreasing) -> transitsTo AND recoversTo should be TRUE.

    With the recovery extension, severity decrease adjacent snapshots generate both
    transitsTo and recoversTo.
    """
    _run_b3_severity_test(
        "b3_no_automatic_decrease_warning_attention.ttl",
        "warning",
        "attention",
        expect_transits=True,
        expect_degrades=False,
        expect_recovers=True,
    )


def test_b3_no_same_severity_transition():
    """B3: Warning -> Warning (same) -> transitsTo should be FALSE."""
    _run_b3_severity_test(
        "b3_no_same_severity_transition.ttl",
        "warning",
        "warning",
        expect_transits=False,
        expect_degrades=False,
    )


# =============================================================================
# Dual Evidence Tests
# =============================================================================


def test_collision_risk_with_observation_plus_assessment_pass():
    """Dual evidence: ObservationData + AssessmentData -> should PASS.

    R5-R8 require Ev_assess (AssessmentData or PredictionData).
    Both observation and assessment data should satisfy this.
    """
    fixture = FIXTURES_DIR / "dual_evidence_observation_plus_assessment.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    ontology = load_ontology()
    rules = load_rules()
    config = load_rule_config()
    merged = data + ontology + config

    validate(
        data_graph=merged,
        shacl_graph=rules,
        ont_graph=None,
        inference="rdfs",
        advanced=True,
        inplace=True,
        debug=False,
    )

    # Risk event should generate a state (Attention, since 5E-6 is between thetaA and thetaM)
    risk_iri = str(ONTO.RiskEvent)
    attention_state = derived_state("attention", risk_iri)

    has_leads_to = (ONTO.RiskEvent, ONTO.leadsToState, attention_state) in merged
    assert has_leads_to, "Risk event with AssessmentData should generate Attention state"


def test_collision_risk_assessment_only_fail():
    """Assessment only (no observation) -> should PASS for R5-R8.

    Actually this should PASS - AssessmentData alone satisfies Ev_assess.
    """
    fixture = FIXTURES_DIR / "dual_evidence_assessment_only.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    ontology = load_ontology()
    rules = load_rules()
    config = load_rule_config()
    merged = data + ontology + config

    validate(
        data_graph=merged,
        shacl_graph=rules,
        ont_graph=None,
        inference="rdfs",
        advanced=True,
        inplace=True,
        debug=False,
    )

    # Risk event should generate a state
    risk_iri = str(ONTO.RiskEvent)
    attention_state = derived_state("attention", risk_iri)

    has_leads_to = (ONTO.RiskEvent, ONTO.leadsToState, attention_state) in merged
    assert has_leads_to, "Risk event with AssessmentData only should generate Attention state"


# =============================================================================
# CausalAssertion Dual Representation Tests
# =============================================================================


def test_causesEvent_from_R3_R4_without_CausalAssertion():
    """R3/R4 direct causesEvent without CausalAssertion -> should PASS.

    R3 and R4 rules infer causesEvent directly without needing CausalAssertion.
    """
    fixture = FIXTURES_DIR / "r3_r4_causes_event_without_causal_assertion.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    ontology = load_ontology()
    rules = load_rules()
    config = load_rule_config()
    merged = data + ontology + config

    validate(
        data_graph=merged,
        shacl_graph=rules,
        ont_graph=None,
        inference="rdfs",
        advanced=True,
        inplace=True,
        debug=False,
    )

    # R4 should infer: Approach causesEvent Risk
    has_causes = (ONTO.Approach, ONTO.causesEvent, ONTO.Risk) in merged
    assert has_causes, "R4 should infer causesEvent between Approach and Risk"


def test_causesEvent_from_B1_with_complete_CausalAssertion():
    """B1 with complete CausalAssertion -> should PASS.

    B1 bridge rule infers causesEvent from CausalAssertion with hasCause/hasEffect.
    """
    fixture = FIXTURES_DIR / "r3_r4_causes_event_with_complete_causal_assertion.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    ontology = load_ontology()
    rules = load_rules()
    config = load_rule_config()
    merged = data + ontology + config

    validate(
        data_graph=merged,
        shacl_graph=rules,
        ont_graph=None,
        inference="rdfs",
        advanced=True,
        inplace=True,
        debug=False,
    )

    # B1 should infer: Approach causesEvent Risk
    has_causes = (ONTO.Approach, ONTO.causesEvent, ONTO.Risk) in merged
    assert has_causes, "B1 should infer causesEvent from CausalAssertion"


def test_explicit_CausalAssertion_missing_evidence_fail():
    """Explicit CausalAssertion missing hasCausalEvidence -> should FAIL.

    CausalAssertionIntegrityShape requires hasCausalEvidence.
    """
    fixture = FIXTURES_DIR / "explicit_causal_assertion_missing_evidence.ttl"
    data = Graph()
    data.parse(fixture.as_uri(), format="turtle")

    shapes = load_extra_shapes()
    ontology = load_ontology()
    conforms, _, _ = run_shacl_validation(data, shapes, ontology)
    assert not conforms, "CausalAssertion without evidence should fail"


# =============================================================================
# Test Discovery Summary
# =============================================================================
if __name__ == "__main__":
    # Print test count when run directly
    import inspect

    test_functions = [
        name
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
    print(f"Total test functions: {len(test_functions)}")
    for name in sorted(test_functions):
        print(f"  - {name}")
