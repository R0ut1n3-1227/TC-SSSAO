"""Shared SHACL runner with deterministic fixed-point iteration.

Used by scripts that need to apply SHACL-SPARQL inference rules while
avoiding noise from repeated ontology injection / anonymous node changes.
"""
from __future__ import annotations

from pathlib import Path

from pyshacl import validate
from rdflib import Graph, URIRef
from rdflib.compare import isomorphic

def _find_project_root(start: Path) -> Path:
    path = start.resolve()
    for parent in [path, *path.parents]:
        if any((parent / marker).exists() for marker in ("pyproject.toml", "requirements.txt")):
            return parent
    raise RuntimeError(f"Could not find project root from {start}")

BASE = _find_project_root(Path(__file__).parent)
OWL = BASE / "ontology" / "tc_sssao.owl"
RULES = BASE / "rules" / "tc_sssao_rules.ttl"
RULE_CONFIG = BASE / "rules" / "tc_sssao_rule_config.ttl"

ONTO_NS = "https://w3id.org/tc-sssao#"
RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
DERIVED_PREFIX = ONTO_NS + "derived_"

TRACKED_PREDICATES = {
    URIRef(f"{ONTO_NS}precedesEvent"),
    URIRef(f"{ONTO_NS}followsEvent"),
    URIRef(f"{ONTO_NS}overlapsWithEvent"),
    URIRef(f"{ONTO_NS}causesEvent"),
    URIRef(f"{ONTO_NS}leadsToState"),
    URIRef(f"{ONTO_NS}transitsTo"),
    URIRef(f"{ONTO_NS}degradesTo"),
    URIRef(f"{ONTO_NS}recoversTo"),
}

DERIVED_STATE_CLASSES = {
    URIRef(f"{ONTO_NS}NormalSituationState"),
    URIRef(f"{ONTO_NS}AttentionSituationState"),
    URIRef(f"{ONTO_NS}WarningSituationState"),
    URIRef(f"{ONTO_NS}DangerousSituationState"),
}


def load_ontology() -> Graph:
    g = Graph()
    g.parse(OWL.as_uri(), format="xml")
    return g


def load_rules() -> Graph:
    g = Graph()
    g.parse(RULES.as_uri(), format="turtle")
    return g


def load_rule_config() -> Graph:
    """Load the rule deployment configuration (θ parameters for R5—R8).

    Must be merged into the DATA graph: pySHACL evaluates SPARQL rule WHERE
    clauses only against the data graph, so config kept in the rules graph
    would be invisible and R5—R8 would silently never fire.
    """
    g = Graph()
    g.parse(RULE_CONFIG.as_uri(), format="turtle")
    return g


def _is_domain_triple(triple):
    s, p, o = triple
    # 追踪 SHACL 推导规则可能生成的所有领域关系
    if isinstance(p, URIRef) and p in TRACKED_PREDICATES:
        return isinstance(s, URIRef) and isinstance(o, URIRef)
    # 追踪派生状态类型三元组（仅命名类，排除 blank node 等价类）
    if p == RDF_TYPE and isinstance(o, URIRef) and o in DERIVED_STATE_CLASSES:
        return isinstance(s, URIRef) and str(s).startswith(DERIVED_PREFIX)
    return False


def _domain_triples(graph: Graph):
    return {t for t in graph if _is_domain_triple(t)}


def shacl_validate_fixed_point(data_graph: Graph, max_iter: int = 10,
                               extra_shacl_graphs: list[Graph] | None = None):
    """Formal inference: current instance/config preflight is mandatory."""
    from scripts.validate.check_rule_input_preflight import require_formal_input
    onto, config = load_ontology(), load_rule_config()
    require_formal_input(data_graph, config, onto)
    return _fixed_point(data_graph, max_iter, extra_shacl_graphs, onto, config)


def validate_diagnostic_graph_fixed_point(data_graph: Graph, max_iter: int = 10,
                                          extra_shacl_graphs: list[Graph] | None = None):
    """Controlled invalid fixtures/schema diagnostics only; not formal inference.

    Kept separate so deliberate invalid-input tests can inspect SHACL reports.
    No disable-preflight switch is exposed on the formal API.
    """
    return _fixed_point(data_graph, max_iter, extra_shacl_graphs,
                        load_ontology(), load_rule_config())


def _fixed_point(
    data_graph: Graph,
    max_iter: int = 10,
    extra_shacl_graphs: list[Graph] | None = None,
    onto: Graph | None = None,
    config: Graph | None = None,
):
    """Run SHACL until the complete data graph reaches an isomorphic fixed point.

    The ontology and the rule deployment configuration (θ parameters) are
    merged into the data graph on the first iteration only. Subsequent
    iterations run on the already-expanded graph without re-injecting
    them, so anonymous-node changes in the OWL file are not counted as
    new domain triples. The config must live in the data graph because
    pySHACL evaluates rule WHERE clauses only against the data graph.

    Args:
        data_graph: Input data graph.
        max_iter: Maximum fixed-point iterations.
        extra_shacl_graphs: Optional list of additional SHACL graphs to merge
            with the project's main rules (e.g. experiment-specific rules).

    Returns:
        (conforms, report_graph, report_text, data_graph, iterations, additions_per_round)
    """
    if max_iter < 1:
        raise ValueError("max_iter must be at least 1")
    rules = load_rules()
    if extra_shacl_graphs:
        for extra in extra_shacl_graphs:
            for t in extra:
                rules.add(t)
    if onto is None or config is None:
        raise RuntimeError("Internal runner requires an explicit execution context")

    # First iteration: merge ontology + rule deployment config, then run
    # rules + RDFS expansion (config is inert for rule COUNTING: its triples
    # carry no TRACKED_PREDICATES / derived-state types).
    data_graph = data_graph + onto + config

    additions_per_round: list[int] = []
    for iterations in range(1, max_iter + 1):
        before = Graph()
        for triple in data_graph:
            before.add(triple)
        prev_domain = _domain_triples(data_graph)
        conforms, report_graph, report_text = validate(
            data_graph=data_graph,
            shacl_graph=rules,
            ont_graph=None,
            inference="rdfs",
            advanced=True,
            inplace=True,
            debug=False,
        )
        cur_domain = _domain_triples(data_graph)
        additions_per_round.append(len(cur_domain - prev_domain))
        # Counts retain their historical domain-statistics meaning. They are
        # not a stopping criterion: B4/B5 and custom shapes can add other facts.
        if isomorphic(before, data_graph):
            break
    else:
        raise AssertionError(
            f"SHACL rules did not converge within {max_iter} iterations. "
            f"Tracked domain additions (diagnostic only): {additions_per_round}"
        )

    return conforms, report_graph, report_text, data_graph, iterations, additions_per_round
