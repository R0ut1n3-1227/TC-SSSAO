from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
from rdflib.namespace import SH

from common import BASE, RDF_DIR, RESULTS, WORKSPACE, derive_transitions, load_processed, save_json, select_event_keys, stable_token

sys.path.insert(0, str(WORKSPACE))
from scripts.utils.shacl_utils import load_rule_config, load_rules  # noqa: E402

TC = Namespace("https://w3id.org/tc-sssao#")
ESA = Namespace("https://w3id.org/tc-sssao/esa-cdm-v1#")


def run_r5_r8_gate(data_graph: Graph):
    """Execute the unchanged R5--R8 shapes only for the mandatory 50-event RDF gate.

    The project-wide rule graph contains unrelated global pairwise rules.  This
    gate is specifically about real-CDM state classification, so selecting the
    four named deployed shapes gives a faithful and tractable check before scale.
    """
    all_rules = load_rules()
    roots = [
        TC.CollisionRiskLeadsToNormalRuleShape,
        TC.CollisionRiskLeadsToAttentionRuleShape,
        TC.CollisionRiskLeadsToWarningRuleShape,
        TC.CollisionRiskLeadsToDangerousRuleShape,
    ]
    working = data_graph + load_rule_config()
    additions = []
    for _ in range(10):
        before = set(working)
        for root in roots:
            rule = all_rules.value(root, SH.rule)
            construct = all_rules.value(rule, SH.construct)
            if construct is None:
                raise RuntimeError(f"Missing SHACL SPARQL construct for {root}")
            result = working.query(str(construct))
            for triple in result.graph:
                working.add(triple)
        additions.append(len(set(working) - before))
        if additions[-1] == 0:
            break
    conforms = bool(additions) and additions[0] > 0 and additions[-1] == 0
    report_text = (
        "Unchanged R5--R8 sh:construct bodies were executed on the 50-event RDF graph "
        f"with RDFLib SPARQL until a zero-addition round; additions={additions}."
    )
    return conforms, Graph(), report_text, working, len(additions), additions


def uri(kind: str, *parts: object) -> URIRef:
    return ESA[f"{kind}_{stable_token(*parts)}"]


def add_optional(g: Graph, subject: URIRef, predicate: URIRef, value, datatype=XSD.float) -> None:
    if pd.notna(value):
        g.add((subject, predicate, Literal(float(value), datatype=datatype)))


def build_graph(df: pd.DataFrame) -> Graph:
    graph = Graph()
    graph.bind("tc", TC)
    graph.bind("esa", ESA)
    graph.bind("xsd", XSD)
    for event_key, group in df.groupby("event_key", sort=True):
        target = uri("Target", event_key)
        chaser = uri("Chaser", event_key)
        encounter = uri("Approach", event_key)
        graph.add((target, RDF.type, TC.Spacecraft))
        graph.add((chaser, RDF.type, TC.SpaceObject))
        graph.add((encounter, RDF.type, TC.ApproachEvent))
        graph.add((encounter, TC.hasPrimaryObject, target))
        graph.add((encounter, TC.hasSecondaryObject, chaser))
        first_obs = None
        for row in group.itertuples(index=False):
            obs = uri("CDMObservation", event_key, row.source_row)
            assessment = uri("Assessment", event_key, row.source_row)
            risk_event = URIRef(f"{TC}esa_risk_snapshot_{row.snapshot_id}")
            if first_obs is None:
                first_obs = obs
            graph.add((obs, RDF.type, TC.ObservationData))
            graph.add((obs, ESA.sourceRow, Literal(int(row.source_row), datatype=XSD.integer)))
            graph.add((assessment, RDF.type, TC.AssessmentData))
            graph.add((assessment, ESA.derivedFromCDM, obs))
            graph.add((assessment, ESA.rawLog10Risk, Literal(float(row.risk), datatype=XSD.double)))
            graph.add((assessment, ESA.timeToTCA, Literal(float(row.time_to_tca), datatype=XSD.double)))
            graph.add((assessment, ESA.missDistanceMetres, Literal(float(row.miss_distance), datatype=XSD.double)))
            graph.add((assessment, ESA.targetSpanMetres, Literal(float(row.t_span), datatype=XSD.double)))
            graph.add((assessment, ESA.chaserSpanMetres, Literal(float(row.c_span), datatype=XSD.double)))
            if pd.notna(row.mission_id):
                graph.add((assessment, ESA.missionIdentifier, Literal(float(row.mission_id), datatype=XSD.double)))
            if pd.notna(row.c_object_type):
                graph.add((assessment, ESA.chaserObjectType, Literal(str(row.c_object_type))))
            for col, pred in (
                ("t_obs_available", ESA.targetObservationsAvailable),
                ("c_obs_available", ESA.chaserObservationsAvailable),
                ("t_obs_used", ESA.targetObservationsUsed),
                ("c_obs_used", ESA.chaserObservationsUsed),
                ("t_weighted_rms", ESA.targetWeightedRMS),
                ("c_weighted_rms", ESA.chaserWeightedRMS),
                ("t_actual_od_span", ESA.targetActualODSpanDays),
                ("c_actual_od_span", ESA.chaserActualODSpanDays),
                ("t_recommended_od_span", ESA.targetRecommendedODSpanDays),
                ("c_recommended_od_span", ESA.chaserRecommendedODSpanDays),
            ):
                add_optional(graph, assessment, pred, getattr(row, col))
            graph.add((risk_event, RDF.type, TC.CollisionRiskEvent))
            graph.add((risk_event, TC.hasEncounterID, Literal(str(event_key), datatype=XSD.string)))
            graph.add((risk_event, TC.hasPrimaryObject, target))
            graph.add((risk_event, TC.hasSecondaryObject, chaser))
            graph.add((risk_event, TC.detectedFromData, obs))
            graph.add((risk_event, TC.supportedByData, assessment))
            graph.add((risk_event, TC.hasCollisionProbability, Literal(float(row.pc), datatype=XSD.float)))
            graph.add((risk_event, TC.hasPredictedMissDistance, Literal(float(row.miss_distance_km), datatype=XSD.float)))
            graph.add((risk_event, TC.hasCombinedHardBodyRadius, Literal(float(row.hbr_km), datatype=XSD.float)))
            graph.add((risk_event, ESA.timeToTCA, Literal(float(row.time_to_tca), datatype=XSD.double)))
        if first_obs is not None:
            graph.add((encounter, TC.detectedFromData, first_obs))
    return graph


def main() -> None:
    full = load_processed()
    eligible = full[full["preflight_pass"]].copy()
    # Keep the mandatory 50-event RDF gate at exactly 50 multi-CDM events while choosing
    # the smallest eligible series.  This exercises mapping + the unchanged
    # SHACL rules without turning the gate into an accidental stress test.
    sizes = eligible.groupby("event_key", sort=True).size()
    keys = sizes[sizes >= 2].sort_values(kind="stable").head(50).index.astype(str).tolist()
    sample = full[full["event_key"].astype(str).isin(set(keys))].copy()
    sample.to_csv(RESULTS / "rdf_50event_summary.csv", index=False)

    input_graph = build_graph(sample)
    input_path = RDF_DIR / "rdf_50event_input.ttl"
    input_graph.serialize(input_path, format="turtle")
    parsed = Graph().parse(input_path, format="turtle")
    conforms, report_graph, report_text, inferred, iterations, additions = run_r5_r8_gate(parsed)
    output_path = RDF_DIR / "rdf_50event_graph.ttl"
    inferred.serialize(output_path, format="turtle")

    risk_events = set(inferred.subjects(RDF.type, TC.CollisionRiskEvent))
    state_counts = {event: len(set(inferred.objects(event, TC.leadsToState))) for event in risk_events}
    transitions = derive_transitions(sample)
    checks = {
        "csv_parse": len(sample) > 0,
        "pc_transform": bool(((10.0 ** sample["risk"] - sample["pc"]).abs() < 1e-15).all()),
        "unit_transform": bool(((sample["miss_distance"] / 1000 - sample["miss_distance_km"]).abs() < 1e-12).all()),
        "rdf_generation": len(input_graph) > 0,
        "execution_layer_input_contract": bool(sample["preflight_pass"].all()),
        "r5_r8_executable": sum(state_counts.values()) == len(risk_events),
        "unique_state": all(value == 1 for value in state_counts.values()),
        "b3_relative_order": all(transitions.get("target_rank", pd.Series(dtype=int)) != transitions.get("source_rank", pd.Series(dtype=int))),  # must be strictly increasing or decreasing
        "rdf_parse": len(parsed) == len(input_graph),
        "r5_r8_construct_fixed_point": bool(conforms),
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "seed": 20260911,
        "events": int(sample["event_key"].nunique()),
        "cdms": int(len(sample)),
        "input_triples": len(input_graph),
        "output_triples": len(inferred),
        "fixed_point_iterations": iterations,
        "additions_per_round": additions,
        "b3_transitions_execution_layer": len(transitions),
        "checks": checks,
        "shacl_report": report_text,
    }
    save_json(RESULTS / "rdf_50event_report.json", report)
    print(report["status"], {k: v for k, v in report.items() if k != "shacl_report"})
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
