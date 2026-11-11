import pytest
from rdflib import Graph
from scripts.report import oops_quality_check as scan

@pytest.mark.parametrize("code", ["P29", "P11"])
def test_blocking_findings_fail_gate(monkeypatch, tmp_path, code):
    class Detector:
        findings = {code: [{"entity": "urn:bad", "message": "controlled violation"}]}
        def __init__(self, graph):
            pass
        def run(self):
            pass
    monkeypatch.setattr(scan, "load_ontology", lambda path: Graph())
    monkeypatch.setattr(scan, "OOPSDetector", Detector)
    monkeypatch.setattr(scan, "generate_report", lambda detector: "controlled finding")
    monkeypatch.setattr(scan, "REPORT_PATH", str(tmp_path / "report.md"))
    assert scan.main() == 1
