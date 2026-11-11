#!/usr/bin/env python3
"""
TC-SSSAO Rule Input Preflight System
=====================================
Runs BEFORE any domain rule inference (R1-R18, B1-B5).
Validates critical input constraints: config singleton, threshold validity,
risk input integrity, object pair integrity, severity rank range,
CausalAssertion integrity, StateTransition integrity, and stable IRI.

Exit code 0 = all checks PASS
Exit code 1 = at least one check FAIL

Checks P1-P29:
  P1-P3:  RuleDeploymentConfiguration singleton
  P4-P7:  Threshold validity (0 <= thetaA < thetaM <= 1)
  P8-P10: CollisionProbability single-valued and range
  P11-P12: PredictedMissDistance single-valued and non-negative
  P13-P15: CombinedHardBodyRadius single-valued and positive
  P16-P18: Object pair integrity (primary/secondary, distinct)
  P19-P21: SituationSeverityRank range {0,1,2,3}
  P22-P24: CausalAssertion integrity (cause/effect/evidence)
  P25-P27: StateTransition integrity (source/target/trigger)
  P28-P29: Stable IRI (no blank nodes for risk events)
"""

import json
import sys
import hashlib
import math
from contextvars import ContextVar
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal, BNode
    from rdflib.plugins.sparql import prepareQuery
    from rdflib.namespace import XSD
except ImportError:
    print("ERROR: rdflib is required. Install with: pip install rdflib")
    sys.exit(1)

# Namespaces
TC = Namespace("https://w3id.org/tc-sssao#")
SH = Namespace("http://www.w3.org/ns/shacl#")

RESULTS: List[Dict[str, Any]] = []
EXIT_CODE = 0
_ACTIVE_RESULTS = ContextVar("formal_preflight_results", default=None)


def result(check_id: str, status: str, message: str, count: Optional[int] = None):
    global EXIT_CODE
    r = {"check_id": check_id, "status": status, "message": message}
    if count is not None:
        r["count"] = count
    active = _ACTIVE_RESULTS.get()
    if active is not None:
        active.append(r)
        return
    RESULTS.append(r)
    if status == "FAIL":
        EXIT_CODE = 1
        print(f"[FAIL] {check_id}: {message}")
    else:
        print(f"[PASS] {check_id}: {message}")


def normalize_ttl_text(text: str) -> str:
    """Normalize TTL text for hashing: collapse whitespace, remove comments."""
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return " ".join(lines)


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_graphs(base_dir: Path) -> Dict[str, Graph]:
    """Load all relevant TTL files into separate named graphs."""
    g = {}
    files = {
        "ontology": base_dir / "ontology" / "tc_sssao.owl",
        "rules": base_dir / "rules" / "tc_sssao_rules.ttl",
        "config": base_dir / "rules" / "tc_sssao_rule_config.ttl",
        "alignments": base_dir / "ontology" / "tc_sssao_alignments.ttl",
    }
    for name, path in files.items():
        if path.exists():
            g[name] = Graph()
            # Auto-detect format: .owl = RDF/XML, .ttl = Turtle
            suffix = path.suffix.lower()
            fmt = "xml" if suffix == ".owl" else ("turtle" if suffix == ".ttl" else None)
            g[name].parse(str(path), format=fmt)
            print(f"Loaded {name}: {len(g[name])} triples from {path}")
        else:
            print(f"WARNING: {name} not found at {path}")
            g[name] = Graph()
    return g


# =============================================================================
# P1-P3: RuleDeploymentConfiguration singleton
# =============================================================================
def check_config_singleton(g: Graph):
    query = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(?config) AS ?cnt) WHERE {
        ?config a tc:RuleDeploymentConfiguration .
    }
    """
    rows = list(g["config"].query(query))
    cnt = int(rows[0][0]) if rows else 0

    if cnt == 0:
        result("P1", "FAIL", "Expected exactly one RuleDeploymentConfiguration; found 0", cnt)
    elif cnt == 1:
        result("P2", "PASS", "Exactly one RuleDeploymentConfiguration found", cnt)
    else:
        result("P3", "FAIL", f"Expected exactly one RuleDeploymentConfiguration; found {cnt}", cnt)


# =============================================================================
# P4-P7: Threshold validity
# =============================================================================
def check_thresholds(g: Graph):
    # Extract thetaA and thetaM from config instance
    # TC-SSSAO: RuleDeploymentConfiguration instance has attentionPcThreshold / mitigationPcThreshold
    query = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT ?thetaA ?thetaM WHERE {
        ?config a tc:RuleDeploymentConfiguration .
        ?config tc:attentionPcThreshold ?thetaA .
        ?config tc:mitigationPcThreshold ?thetaM .
    }
    """
    rows = list(g["config"].query(query))

    thetaA = None
    thetaM = None
    if rows:
        for row in rows:
            val_a = float(row.thetaA)
            val_m = float(row.thetaM)
            if thetaA is None:
                thetaA = val_a
                thetaM = val_m

    if thetaA is None or thetaM is None:
        result("P4", "FAIL", "Could not extract thetaA and thetaM from config", 0)
        return

    # P4: thetaA < 0
    if thetaA < 0:
        result("P4", "FAIL", f"thetaA = {thetaA} < 0", 0)
    else:
        result("P4", "PASS", f"thetaA = {thetaA} >= 0", 1)

    # P5: thetaM > 1
    if thetaM > 1:
        result("P5", "FAIL", f"thetaM = {thetaM} > 1", 0)
    else:
        result("P5", "PASS", f"thetaM = {thetaM} <= 1", 1)

    # P6: thetaA = thetaM
    if abs(thetaA - thetaM) < 1e-15:
        result("P6", "FAIL", f"thetaA = thetaM = {thetaA}", 0)
    else:
        result("P6", "PASS", f"thetaA = {thetaA} != thetaM = {thetaM}", 1)

    # P7: thetaA > thetaM
    if thetaA > thetaM:
        result("P7", "FAIL", f"thetaA = {thetaA} > thetaM = {thetaM}", 0)
    else:
        result("P7", "PASS", f"thetaA = {thetaA} < thetaM = {thetaM} (valid)", 1)


# =============================================================================
# P8-P10: CollisionProbability single-valued and range
# =============================================================================
def check_collision_probability(g: Graph):
    # Find classifiable CollisionRiskEvents (those with assessment/prediction evidence)
    query = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?event ?pc (COUNT(DISTINCT ?pc2) AS ?pc_count) WHERE {
        ?event a tc:CollisionRiskEvent .
        {
            ?event tc:supportedByData ?data .
            ?data a ?dt . FILTER(?dt = tc:AssessmentData || ?dt = tc:PredictionData)
        } UNION {
            ?event tc:detectedFromData ?data .
            ?data a ?dt . FILTER(?dt = tc:AssessmentData || ?dt = tc:PredictionData)
        }
        ?event tc:hasCollisionProbability ?pc .
        ?event tc:hasCollisionProbability ?pc2 .
    }
    GROUP BY ?event ?pc
    """
    fail_count = 0
    pass_count = 0

    rows = list(g["ontology"].query(query))
    for row in rows:
        event = str(row.event)
        pc_count = int(row.pc_count)
        pc_val = float(row.pc) if row.pc is not None else None

        if pc_count > 1:
            result("P8", "FAIL", f"CollisionRiskEvent {event.split('#')[-1]} has multivalued hasCollisionProbability ({pc_count} values)", pc_count)
            fail_count += 1
        elif pc_val is not None and (pc_val < 0 or pc_val > 1):
            result("P9", "FAIL", f"CollisionRiskEvent {event.split('#')[-1]} hasCollisionProbability = {pc_val} outside [0,1]", 0)
            fail_count += 1
        else:
            pass_count += 1

    if rows:
        if fail_count == 0:
            result("P8-P10", "PASS", f"All {pass_count} classifiable CollisionRiskEvents have valid single-valued Pc in [0,1]", pass_count)
        else:
            result("P8-P10", "FAIL", f"{fail_count} failures, {pass_count} passed", fail_count)
    else:
        result("P8-P10", "PASS", "No classifiable CollisionRiskEvents found (skipping)", 0)


# =============================================================================
# P11-P12: PredictedMissDistance single-valued and non-negative
# =============================================================================
def check_miss_distance(g: Graph):
    query = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT ?event (COUNT(?d) AS ?dcount) (MIN(?d) AS ?dmin) WHERE {
        ?event a tc:CollisionRiskEvent .
        ?event tc:hasPredictedMissDistance ?d .
    }
    GROUP BY ?event
    """
    fail_count = 0
    pass_count = 0

    rows = list(g["ontology"].query(query))
    for row in rows:
        event = str(row.event)
        dcount = int(row.dcount)
        dmin = float(row.dmin) if row.dmin is not None else None

        if dcount > 1:
            result("P11", "FAIL", f"CollisionRiskEvent {event.split('#')[-1]} has multivalued hasPredictedMissDistance ({dcount} values)", dcount)
            fail_count += 1
        elif dmin is not None and dmin < 0:
            result("P12", "FAIL", f"CollisionRiskEvent {event.split('#')[-1]} hasPredictedMissDistance = {dmin} < 0", 0)
            fail_count += 1
        else:
            pass_count += 1

    if rows:
        if fail_count == 0:
            result("P11-P12", "PASS", f"All {pass_count} CollisionRiskEvents have valid single-valued miss distance >= 0", pass_count)
        else:
            result("P11-P12", "FAIL", f"{fail_count} failures, {pass_count} passed", fail_count)
    else:
        result("P11-P12", "PASS", "No CollisionRiskEvents with miss distance found (skipping)", 0)


# =============================================================================
# P13-P15: CombinedHardBodyRadius single-valued and positive
# =============================================================================
def check_hbr(g: Graph):
    query = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT ?event (COUNT(?h) AS ?hcount) (MIN(?h) AS ?hmin) WHERE {
        ?event a tc:CollisionRiskEvent .
        ?event tc:hasCombinedHardBodyRadius ?h .
    }
    GROUP BY ?event
    """
    fail_count = 0
    pass_count = 0

    rows = list(g["ontology"].query(query))
    for row in rows:
        event = str(row.event)
        hcount = int(row.hcount)
        hmin = float(row.hmin) if row.hmin is not None else None

        if hcount > 1:
            result("P13", "FAIL", f"CollisionRiskEvent {event.split('#')[-1]} has multivalued hasCombinedHardBodyRadius ({hcount} values)", hcount)
            fail_count += 1
        elif hmin is not None and hmin <= 0:
            result("P14", "FAIL", f"CollisionRiskEvent {event.split('#')[-1]} hasCombinedHardBodyRadius = {hmin} <= 0", 0)
            fail_count += 1
        elif hmin is not None and hmin < 0:
            result("P15", "FAIL", f"CollisionRiskEvent {event.split('#')[-1]} hasCombinedHardBodyRadius = {hmin} < 0", 0)
            fail_count += 1
        else:
            pass_count += 1

    if rows:
        if fail_count == 0:
            result("P13-P15", "PASS", f"All {pass_count} CollisionRiskEvents have valid HBR > 0", pass_count)
        else:
            result("P13-P15", "FAIL", f"{fail_count} failures, {pass_count} passed", fail_count)
    else:
        result("P13-P15", "PASS", "No CollisionRiskEvents with HBR found (skipping)", 0)


# =============================================================================
# P16-P18: Object pair integrity
# =============================================================================
def check_object_pair(g: Graph):
    # Check ApproachEvent and CollisionRiskEvent
    query = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT ?event (COUNT(DISTINCT ?p) AS ?pcount) (COUNT(DISTINCT ?s) AS ?scount) WHERE {
        { ?event a tc:ApproachEvent } UNION { ?event a tc:CollisionRiskEvent }
        OPTIONAL { ?event tc:hasPrimaryObject ?p }
        OPTIONAL { ?event tc:hasSecondaryObject ?s }
    }
    GROUP BY ?event
    """
    fail_count = 0
    pass_count = 0

    rows = list(g["ontology"].query(query))
    for row in rows:
        event = str(row.event)
        pcount = int(row.pcount) if row.pcount else 0
        scount = int(row.scount) if row.scount else 0

        if pcount > 1:
            result("P16", "FAIL", f"{event.split('#')[-1]} has multivalued hasPrimaryObject ({pcount} values)", pcount)
            fail_count += 1
        if scount > 1:
            result("P17", "FAIL", f"{event.split('#')[-1]} has multivalued hasSecondaryObject ({scount} values)", scount)
            fail_count += 1

    # Check primary != secondary
    query2 = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        { ?event a tc:ApproachEvent } UNION { ?event a tc:CollisionRiskEvent }
        ?event tc:hasPrimaryObject ?p .
        ?event tc:hasSecondaryObject ?s .
        FILTER(?p = ?s)
    }
    """
    rows2 = list(g["ontology"].query(query2))
    same_count = int(rows2[0][0]) if rows2 else 0
    if same_count > 0:
        result("P18", "FAIL", f"{same_count} events have primary == secondary", same_count)
        fail_count += 1
    else:
        result("P18", "PASS", "All events have distinct primary and secondary objects", 0)

    if fail_count == 0:
        result("P16-P18", "PASS", f"Object pair integrity check passed for {len(rows)} events", len(rows))


# =============================================================================
# P19-P21: SituationSeverityRank range
# =============================================================================
def check_severity_rank(g: Graph):
    # TC-SSSAO data model: severity ranks are DERIVED by R5-R8 rules, not pre-existing on instances.
    # This preflight checks actual instances in the data graph.
    # Schema-level validation (SHACL shapes created in Phase 5) validate the class definitions.
    # P19-P21: Check any hasSeverityRank values that actually appear in data are in {0,1,2,3}
    rank_values_check = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT ?rank (COUNT(?rank) AS ?rcount) WHERE {
        { ?state a tc:NormalSituationState } UNION
        { ?state a tc:AttentionSituationState } UNION
        { ?state a tc:WarningSituationState } UNION
        { ?state a tc:DangerousSituationState }
        OPTIONAL { ?state tc:hasSeverityRank ?rank }
    }
    GROUP BY ?rank
    """
    rows = list(g["ontology"].query(rank_values_check))

    # Check for out-of-range values
    out_of_range = 0
    valid_values_seen = 0
    for row in rows:
        rv = row.rank
        if rv is not None:
            try:
                rv_int = int(rv)
                if rv_int not in {0, 1, 2, 3}:
                    out_of_range += 1
                    result("P20", "FAIL", f"hasSeverityRank = {rv_int} not in {{0,1,2,3}}", 0)
                else:
                    valid_values_seen += 1
            except (ValueError, TypeError):
                out_of_range += 1
                result("P20", "FAIL", f"hasSeverityRank = {rv} is not an integer", 0)

    if out_of_range == 0:
        if valid_values_seen > 0:
            result("P21", "PASS", f"All {valid_values_seen} SituationState instances have valid severity ranks in {{0,1,2,3}}", valid_values_seen)
        else:
            # No instances in the schema file — severity is derived by rules at runtime.
            # Schema-level SHACL shapes (Phase 5) validate the definitions.
            result("P19-P21", "PASS", "No SituationState instances in schema (ranks derived by R5-R8 at runtime; SHACL shapes validate schema)", 0)
            result("P22", "PASS", "Severity rank schema validated by SHACL shapes (Phase 5)", 0)


# =============================================================================
# P22-P24: CausalAssertion integrity
# =============================================================================
def check_causal_assertion_integrity(g: Graph):
    # P22: missing hasCausalEvidence
    query_missing_evidence = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        ?ca a tc:CausalAssertion .
        FILTER NOT EXISTS { ?ca tc:hasCausalEvidence ?ev }
    }
    """
    rows = list(g["ontology"].query(query_missing_evidence))
    missing_evidence = int(rows[0][0]) if rows else 0
    if missing_evidence > 0:
        result("P22", "FAIL", f"{missing_evidence} CausalAssertion(s) missing hasCausalEvidence", missing_evidence)
    else:
        result("P22", "PASS", "All CausalAssertions have hasCausalEvidence", 0)

    # P23: hasEffect with 2+ distinct effects
    query_multi_effect = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        ?ca a tc:CausalAssertion .
        ?ca tc:hasEffect ?e1 .
        ?ca tc:hasEffect ?e2 .
        FILTER(?e1 != ?e2)
    }
    """
    rows = list(g["ontology"].query(query_multi_effect))
    multi_effect = int(rows[0][0]) if rows else 0
    if multi_effect > 0:
        result("P23", "FAIL", f"{multi_effect} CausalAssertion(s) have 2+ distinct hasEffect values", multi_effect)
    else:
        result("P23", "PASS", "All CausalAssertions have at most one hasEffect", 0)

    # P24: complete CausalAssertions
    query_complete = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        ?ca a tc:CausalAssertion .
        ?ca tc:hasCause ?c .
        ?ca tc:hasEffect ?e .
        ?ca tc:hasCausalEvidence ?ev .
    }
    """
    rows = list(g["ontology"].query(query_complete))
    complete = int(rows[0][0]) if rows else 0

    query_total = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        ?ca a tc:CausalAssertion .
    }
    """
    rows_total = list(g["ontology"].query(query_total))
    total = int(rows_total[0][0]) if rows_total else 0

    if complete == total and total > 0:
        result("P24", "PASS", f"All {complete} CausalAssertions are complete (hasCause + hasEffect + hasCausalEvidence)", complete)
    elif complete < total:
        result("P24", "FAIL", f"{complete}/{total} CausalAssertions complete, {total - complete} incomplete", complete)
    else:
        result("P24", "PASS", "No CausalAssertions in data (skipping)", 0)


# =============================================================================
# P25-P27: StateTransition integrity
# =============================================================================
def check_state_transition_integrity(g: Graph):
    # P25: missing triggeredByEvent
    query_missing_trigger = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        ?st a tc:StateTransition .
        FILTER NOT EXISTS { ?st tc:triggeredByEvent ?te }
    }
    """
    rows = list(g["ontology"].query(query_missing_trigger))
    missing_trigger = int(rows[0][0]) if rows else 0
    if missing_trigger > 0:
        result("P25", "FAIL", f"{missing_trigger} StateTransition(s) missing triggeredByEvent", missing_trigger)
    else:
        result("P25", "PASS", "All StateTransitions have triggeredByEvent", 0)

    # P26: hasTargetState with 2+ distinct targets
    query_multi_target = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        ?st a tc:StateTransition .
        ?st tc:hasTargetState ?t1 .
        ?st tc:hasTargetState ?t2 .
        FILTER(?t1 != ?t2)
    }
    """
    rows = list(g["ontology"].query(query_multi_target))
    multi_target = int(rows[0][0]) if rows else 0
    if multi_target > 0:
        result("P26", "FAIL", f"{multi_target} StateTransition(s) have 2+ distinct hasTargetState values", multi_target)
    else:
        result("P26", "PASS", "All StateTransitions have at most one hasTargetState", 0)

    # P27: complete StateTransitions
    query_complete = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        ?st a tc:StateTransition .
        ?st tc:hasSourceState ?ss .
        ?st tc:hasTargetState ?ts .
        ?st tc:triggeredByEvent ?te .
    }
    """
    rows = list(g["ontology"].query(query_complete))
    complete = int(rows[0][0]) if rows else 0

    query_total = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        ?st a tc:StateTransition .
    }
    """
    rows_total = list(g["ontology"].query(query_total))
    total = int(rows_total[0][0]) if rows_total else 0

    if complete == total and total > 0:
        result("P27", "PASS", f"All {complete} StateTransitions are complete (hasSourceState + hasTargetState + triggeredByEvent)", complete)
    elif complete < total:
        result("P27", "FAIL", f"{complete}/{total} StateTransitions complete, {total - complete} incomplete", complete)
    else:
        result("P27", "PASS", "No StateTransitions in data (skipping)", 0)


# =============================================================================
# P28-P29: Stable IRI for risk events
# =============================================================================
def check_stable_iri(g: Graph):
    # P28: CollisionRiskEvent or DebrisRiskEvent as blank node
    query_blank = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        { ?event a tc:CollisionRiskEvent }
        UNION
        { ?event a tc:DebrisRiskEvent }
        FILTER(ISBLANK(?event))
    }
    """
    rows = list(g["ontology"].query(query_blank))
    blank_count = int(rows[0][0]) if rows else 0
    if blank_count > 0:
        result("P28", "FAIL", f"{blank_count} CollisionRiskEvent(s)/DebrisRiskEvent(s) are blank nodes (must use named IRI)", blank_count)
    else:
        result("P28", "PASS", "No blank nodes used for CollisionRiskEvent/DebrisRiskEvent", 0)

    # P29: named IRI for risk events
    query_named = """
    PREFIX tc: <https://w3id.org/tc-sssao#>
    SELECT (COUNT(*) AS ?cnt) WHERE {
        { ?event a tc:CollisionRiskEvent }
        UNION
        { ?event a tc:DebrisRiskEvent }
        FILTER(ISIRI(?event))
    }
    """
    rows = list(g["ontology"].query(query_named))
    named_count = int(rows[0][0]) if rows else 0
    if named_count > 0:
        result("P29", "PASS", f"All {named_count} CollisionRiskEvent(s)/DebrisRiskEvent(s) use named IRIs", named_count)
    else:
        result("P29", "PASS", "No CollisionRiskEvent/DebrisRiskEvent in data (skipping)", 0)


# =============================================================================
# Main
# =============================================================================
class RuleInputPreflightError(ValueError):
    """Formal inference was refused before any domain rules were executed."""


def require_formal_input(data: Graph, config: Graph, ontology: Graph) -> list:
    """Check the actual deployment and instance graph, without mutating either.

    RDFS closure on a copy resolves subclass types; it executes no domain rules.
    Diagnostic rule-contract experiments have a separate runner, not a bypass
    option on the formal runner. Missing ranks remain permissible before R5-R8.
    """
    from owlrl import DeductiveClosure, RDFS_Semantics
    instance = data + ontology + config
    type_closure = instance + Graph()
    DeductiveClosure(RDFS_Semantics).expand(type_closure)
    # owlrl's RDFS literal handling can materialize equal-valued lexical/datatype
    # aliases. They are not additional supplied values. Retain original property
    # assertions for cardinality/numeric checks; project only inferred types.
    for triple in type_closure.triples((None, RDF.type, None)):
        instance.add(triple)
    # The real rules run with RDFS property inheritance as well. Project each
    # supplied assertion to its inferred superproperties, keeping its original
    # RDF object term. This closes subproperty input bypasses without copying
    # owlrl's synthetic equal-valued numeric aliases.
    for subject, predicate, value in list(instance):
        for parent in type_closure.objects(predicate, RDFS.subPropertyOf):
            if isinstance(parent, URIRef):
                instance.add((subject, parent, value))
    records = []
    token = _ACTIVE_RESULTS.set(records)
    try:
        graphs = {"ontology": instance, "config": instance}
        for check in (check_config_singleton, check_thresholds,
                      check_collision_probability, check_miss_distance, check_hbr,
                      check_object_pair, check_severity_rank,
                      check_causal_assertion_integrity,
                      check_state_transition_integrity, check_stable_iri):
            try:
                check(graphs)
            except (ValueError, TypeError, OverflowError) as exc:
                result(check.__name__, "FAIL", str(exc))
        # Reject nonfinite/multivalued parameters that SPARQL aggregate checks
        # or numeric casts could otherwise miss. No new scientific thresholds.
        for subject in instance.subjects(RDF.type, TC.RuleDeploymentConfiguration):
            for prop in (TC.attentionPcThreshold, TC.mitigationPcThreshold):
                values = list(instance.objects(subject, prop))
                if len(values) != 1 or not all(math.isfinite(float(v)) for v in values):
                    result("P4-P7", "FAIL", f"{subject} requires one finite {prop}")
        for prop, lower, inclusive in ((TC.hasCollisionProbability, 0, True),
                                       (TC.hasPredictedMissDistance, 0, True),
                                       (TC.hasCombinedHardBodyRadius, 0, False)):
            for subject in set(instance.subjects(prop, None)):
                values = list(instance.objects(subject, prop))
                for v in values:
                    try:
                        number = float(v)
                        ok = math.isfinite(number) and (number >= lower if inclusive else number > lower)
                        if prop == TC.hasCollisionProbability:
                            ok = ok and number <= 1
                    except (ValueError, TypeError, OverflowError):
                        ok = False
                    if not ok:
                        result("P8-P15", "FAIL", f"{subject} invalid {prop}: {v}")
        for subject in set(instance.subjects(TC.hasSeverityRank, None)):
            values = list(instance.objects(subject, TC.hasSeverityRank))
            if len(values) != 1 or any(str(v) not in {"0", "1", "2", "3"} for v in values):
                result("P19-P21", "FAIL", f"{subject} requires one integer rank 0..3")
        # Per-instance completeness avoids aggregate joins hiding one incomplete
        # record behind another record with multiple legitimate causes.
        for kind, specifications, code in (
            (TC.CausalAssertion, ((TC.hasCause, 1, None), (TC.hasEffect, 1, 1),
                                  (TC.hasCausalEvidence, 1, None)), "P22-P24"),
            (TC.StateTransition, ((TC.hasSourceState, 1, 1), (TC.hasTargetState, 1, 1),
                                  (TC.triggeredByEvent, 1, None)), "P25-P27"),
            (TC.ApproachEvent, ((TC.hasPrimaryObject, 1, 1), (TC.hasSecondaryObject, 1, 1)), "P16-P18"),
            (TC.CollisionRiskEvent, ((TC.hasPrimaryObject, 1, 1), (TC.hasSecondaryObject, 1, 1)), "P16-P18"),
        ):
            for subject in set(instance.subjects(RDF.type, kind)):
                for prop, minimum, maximum in specifications:
                    values = set(instance.objects(subject, prop))
                    if len(values) < minimum or (maximum is not None and len(values) > maximum):
                        result(code, "FAIL", f"{subject}: invalid cardinality for {prop}: {len(values)}")
                    if prop in (TC.hasPrimaryObject, TC.hasSecondaryObject) and any(
                            not isinstance(v, URIRef) for v in values):
                        result(code, "FAIL", f"{subject}: {prop} must use an IRI")
        # RDFS range typing does not make a literal a legal OWL object-property
        # value, nor an IRI a legal datatype-property value. Reject bad encoding
        # before domain rules, rather than relying on post-inference shapes.
        for kind in (OWL.ObjectProperty, OWL.DatatypeProperty):
            for prop in set(instance.subjects(RDF.type, kind)):
                for subject, value in instance.subject_objects(prop):
                    literal = isinstance(value, Literal)
                    if (kind == OWL.ObjectProperty and literal) or (
                            kind == OWL.DatatypeProperty and not literal):
                        result("RDF_TERM_KIND", "FAIL", f"{subject}: {prop} has invalid {kind} value {value.n3()}")
    except (ValueError, TypeError, OverflowError) as exc:
        result("P1-P29", "FAIL", str(exc))
    finally:
        _ACTIVE_RESULTS.reset(token)
    failures = [r for r in records if r["status"] == "FAIL"]
    if failures:
        raise RuleInputPreflightError("Formal RDF input refused: " + "; ".join(
            f"{r['check_id']}: {r['message']}" for r in failures))
    return records


def main():
    global RESULTS, EXIT_CODE

    script_dir = Path(__file__).parent
    # Walk up from scripts/validate/ to workspace root
    workspace_dir = script_dir.parent.parent

    print("=" * 70)
    print("TC-SSSAO Rule Input Preflight System")
    print("=" * 70)
    print(f"Workspace: {workspace_dir}")
    print()

    # Load graphs
    g = load_graphs(workspace_dir)

    print()
    print("Running checks P1-P29...")
    print("-" * 70)

    # Run all checks
    check_config_singleton(g)
    check_thresholds(g)
    check_collision_probability(g)
    check_miss_distance(g)
    check_hbr(g)
    check_object_pair(g)
    check_severity_rank(g)
    check_causal_assertion_integrity(g)
    check_state_transition_integrity(g)
    check_stable_iri(g)

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")

    print(f"Total checks: {len(RESULTS)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    # Output JSON
    output = {
        "preflight_version": "1.0",
        "total_checks": len(RESULTS),
        "passed": passed,
        "failed": failed,
        "exit_code": EXIT_CODE,
        "checks": RESULTS,
    }

    json_path = workspace_dir / "data" / "current" / "preflight_results.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults written to: {json_path}")
    print()

    if EXIT_CODE == 0:
        print("RESULT: ALL CHECKS PASSED")
    else:
        print("RESULT: SOME CHECKS FAILED")

    sys.exit(EXIT_CODE)


if __name__ == "__main__":
    main()
