"""Export current class inventory from ontology/tc_sssao.owl as TSV.

Extracts all owl:Class names with their direct superclasses and outputs:
    class_name | direct_superclasses | namespace
"""
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL

TC = Namespace("https://w3id.org/tc-sssao#")
# Script is at scripts/figures/export_current_class_inventory.py
# OWL is at ontology/tc_sssao.owl  =>  parents[2] / "ontology" / "tc_sssao.owl"
ROOT = Path(__file__).resolve().parents[2]
OWL_PATH = ROOT / "ontology" / "tc_sssao.owl"


def local_name(uri):
    """Strip namespace URI to get local name."""
    return str(uri).replace("https://w3id.org/tc-sssao#", "")


def main():
    g = Graph()
    g.parse(OWL_PATH, format="xml")

    rows = []
    for cls in g.subjects(RDF.type, OWL.Class):
        # Skip blank nodes and external classes
        if "w3id.org/tc-sssao" not in str(cls):
            continue
        if str(cls).startswith("http://") or str(cls).startswith("https://"):
            if "w3id.org/tc-sssao" not in str(cls):
                continue

        # Get direct superclasses (named only, no anonymous restrictions)
        superclasses = []
        for sc in g.objects(cls, RDFS.subClassOf):
            # Only include named classes (URI nodes, not bnodes)
            if sc.startswith("https://w3id.org/tc-sssao#"):
                superclasses.append(local_name(sc))
        superclasses.sort()

        row = {
            "class_name": local_name(cls),
            "direct_superclasses": ", ".join(superclasses) if superclasses else "-",
            "namespace": "tc-sssao",
        }
        rows.append(row)

    # Sort by class name
    rows.sort(key=lambda r: r["class_name"])

    # Print TSV to stdout
    header = "class_name\tdirect_superclasses\tnamespace"
    lines = [header]
    for row in rows:
        lines.append(f"{row['class_name']}\t{row['direct_superclasses']}\t{row['namespace']}")

    output = "\n".join(lines)
    print(output)

    # Also write to file
    out_path = Path(__file__).resolve().parent / "class_inventory_current.tsv"
    out_path.write_text(output, encoding="utf-8")
    print(f"\nTotal classes: {len(rows)}", file=__import__("sys").stderr)
    print(f"Output written to: {out_path}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
