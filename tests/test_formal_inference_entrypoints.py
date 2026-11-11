"""Production entry refusals occur before pySHACL domain validation."""
import importlib.util
from pathlib import Path
import pytest
from rdflib import Graph, Literal, RDF, RDFS, URIRef
from scripts.utils import shacl_utils as runner
from scripts.validate.check_rule_input_preflight import TC, RuleInputPreflightError, require_formal_input

ROOT = Path(__file__).resolve().parents[1]

def scenario():
    return Graph().parse(ROOT / "experiments/rule_logic_verification/data/scenario_facts.ttl", format="turtle")

def invalid(data, kind):
    if kind == "threshold":
        config = runner.load_rule_config()
        config.set((TC.RiskSituationRuleConfig, TC.attentionPcThreshold, Literal(0.5)))
        # Same config IRI, conflicting actual value must not be overwritten.
        return data + config
    if kind == "probability":
        event = next(data.subjects(RDF.type, TC.CollisionRiskEvent))
        data.set((event, TC.hasCollisionProbability, Literal(2.0)))
    if kind == "structure":
        data.add((TC.invalid_assertion, RDF.type, TC.CausalAssertion))
    if kind == "missing_pair":
        event = next(data.subjects(RDF.type, TC.CollisionRiskEvent))
        data.remove((event, TC.hasPrimaryObject, None))
    return data

def test_formal_valid_input():
    conforms, _, _, final, _, _ = runner.shacl_validate_fixed_point(scenario())
    assert conforms
    assert len(list(final.triples((None, TC.recoversTo, None)))) == 1

def test_valid_numeric_alias_does_not_create_false_cardinality_violation():
    data = scenario()
    original = set(data)
    config = runner.load_rule_config()
    # Same numeric value as an existing xsd:float miss distance, now xsd:double.
    config.set((TC.RiskSituationRuleConfig, TC.attentionPcThreshold, Literal(0.5)))
    config.set((TC.RiskSituationRuleConfig, TC.mitigationPcThreshold, Literal(0.6)))
    checks = require_formal_input(data, config, runner.load_ontology())
    assert not [r for r in checks if r["status"] == "FAIL"]
    assert set(data) == original

@pytest.mark.parametrize("value,refused", [(0.0, False), (2.0, True)])
def test_property_inheritance_cannot_bypass_probability_preflight(value, refused):
    data = scenario()
    event = next(data.subjects(RDF.type, TC.CollisionRiskEvent))
    data.remove((event, TC.hasCollisionProbability, None))
    data.add((TC.pcAlias, RDFS.subPropertyOf, TC.hasCollisionProbability))
    data.add((event, TC.pcAlias, Literal(value)))
    if refused:
        with pytest.raises(RuleInputPreflightError, match="outside \\[0,1\\]"):
            require_formal_input(data, runner.load_rule_config(), runner.load_ontology())
    else:
        assert not [r for r in require_formal_input(data, runner.load_rule_config(),
                                                   runner.load_ontology()) if r["status"] == "FAIL"]

@pytest.mark.parametrize("kind", ["literal_cause", "iri_probability"])
def test_complete_but_invalid_rdf_terms_refused_before_domain_rules(monkeypatch, kind):
    data = scenario()
    if kind == "literal_cause":
        data.add((TC.badAssertion, RDF.type, TC.CausalAssertion))
        data.add((TC.badAssertion, TC.hasCause, Literal("not an event")))
        data.add((TC.badAssertion, TC.hasEffect, TC.someEvent))
        data.add((TC.badAssertion, TC.hasCausalEvidence, TC.someEvidence))
        data.add((TC.someEvent, RDF.type, TC.SpaceEvent))
        data.add((TC.someEvidence, RDF.type, TC.SSAData))
    else:
        event = next(data.subjects(RDF.type, TC.CollisionRiskEvent))
        # Relative IRI is a resource even if Python float() accepts its text.
        data.set((event, TC.hasCollisionProbability, URIRef("0.5")))
    monkeypatch.setattr(runner, "validate", lambda **kwargs: pytest.fail("Domain rules reached"))
    with pytest.raises(RuleInputPreflightError, match="RDF_TERM_KIND"):
        runner.shacl_validate_fixed_point(data)

@pytest.mark.parametrize("kind", ["threshold", "probability", "structure", "missing_pair"])
def test_shared_formal_rejects_before_validate(monkeypatch, kind):
    def forbidden(**kwargs): raise AssertionError("domain inference must not run")
    monkeypatch.setattr(runner, "validate", forbidden)
    with pytest.raises(RuleInputPreflightError, match="Formal RDF input refused"):
        runner.shacl_validate_fixed_point(invalid(scenario(), kind))

@pytest.mark.parametrize("kind", ["threshold", "probability", "structure", "missing_pair"])
def test_real_scenario_main_rejects(monkeypatch, tmp_path, kind):
    path = ROOT / "experiments/rule_logic_verification/run_rule_scenario.py"
    spec = importlib.util.spec_from_file_location("formal_scenario_test", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    facts = tmp_path / "facts.ttl"
    invalid(scenario(), kind).serialize(facts, format="turtle")
    monkeypatch.setattr(module, "FACTS", facts)
    monkeypatch.setattr(module, "OUT", tmp_path / "outputs")
    import pyshacl
    monkeypatch.setattr(pyshacl, "validate", lambda **kwargs: pytest.fail("domain inference reached"))
    with pytest.raises(RuleInputPreflightError): module.main()

def test_negative_diagnostic_still_usable():
    data = Graph().parse(ROOT / "rules/tc_sssao_test_negative.ttl", format="turtle")
    conforms, report, _, _, _, _ = runner.validate_diagnostic_graph_fixed_point(data)
    assert not conforms and len(report) > 0
    # The legacy negative fixture targets SHACL conditions outside P1-P29;
    # inject a genuine P22 violation to test the formal refusal boundary.
    data.add((TC.invalid_assertion, RDF.type, TC.CausalAssertion))
    with pytest.raises(RuleInputPreflightError): runner.shacl_validate_fixed_point(data)
