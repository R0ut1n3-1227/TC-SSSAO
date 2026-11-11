import pytest
from rdflib import Graph, URIRef
from scripts.utils import shacl_utils as runner

def configure(monkeypatch):
    rules = Graph().parse(data='''
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    <urn:shape> a sh:NodeShape; sh:targetNode <urn:item>;
      sh:rule [a sh:SPARQLRule; sh:order 0; sh:construct "CONSTRUCT { <urn:item> <urn:result> true } WHERE { <urn:item> <urn:middle> true }"];
      sh:rule [a sh:SPARQLRule; sh:order 1; sh:construct "CONSTRUCT { <urn:item> <urn:middle> true } WHERE { <urn:item> <urn:seed> true }"].
    ''', format="turtle")
    monkeypatch.setattr(runner, "load_rules", lambda: rules)
    monkeypatch.setattr(runner, "load_ontology", Graph)
    monkeypatch.setattr(runner, "load_rule_config", Graph)
    return Graph().parse(data="<urn:item> <urn:seed> true .", format="turtle")

def test_untracked_predicates_need_more_rounds(monkeypatch):
    data = configure(monkeypatch)
    _, _, _, final, iterations, counts = runner.validate_diagnostic_graph_fixed_point(data)
    assert list(final.objects(URIRef("urn:item"), URIRef("urn:result")))
    assert iterations >= 3 and all(count == 0 for count in counts)

def test_iteration_cap_does_not_claim_convergence(monkeypatch):
    with pytest.raises(AssertionError, match="did not converge"):
        runner.validate_diagnostic_graph_fixed_point(configure(monkeypatch), max_iter=1)

def test_invalid_iteration_cap():
    with pytest.raises(ValueError):
        runner.validate_diagnostic_graph_fixed_point(Graph(), max_iter=0)

def test_rule_exception_is_not_hidden(monkeypatch):
    data = configure(monkeypatch)
    def fail(**kwargs):
        raise RuntimeError("rule execution failed")
    monkeypatch.setattr(runner, "validate", fail)
    with pytest.raises(RuntimeError, match="rule execution failed"):
        runner.validate_diagnostic_graph_fixed_point(data)

def test_nonconforming_fixed_point_is_not_reported_as_pass(monkeypatch):
    data = configure(monkeypatch)
    monkeypatch.setattr(runner, "validate", lambda **kwargs: (False, Graph(), "violation"))
    conforms, _, report, _, rounds, _ = runner.validate_diagnostic_graph_fixed_point(data)
    assert conforms is False and report == "violation" and rounds == 1
