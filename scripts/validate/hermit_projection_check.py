"""HermiT 临时投影一致性检查

HermiT 不支持 xsd:duration 与 geo:wktLiteral（不在 OWL 2 DL datatype map 中），
因此生成一个临时投影文件：将这两种 datatype 映射为 xsd:string，
在该投影上运行 HermiT 一致性检查与类可满足性检查。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def _find_project_root(start: Path) -> Path:
    path = start.resolve()
    for parent in [path, *path.parents]:
        if any((parent / marker).exists() for marker in ("pyproject.toml", "requirements.txt")):
            return parent
    raise RuntimeError(f"Could not find project root from {start}")

BASE_DIR = _find_project_root(Path(__file__).parent)
OWL_PATH = BASE_DIR / "ontology" / "tc_sssao.owl"


def main():
    print("=" * 70)
    print("HermiT Projection Consistency Check")
    print("=" * 70)
    print(f"Source OWL: {OWL_PATH}")

    try:
        import rdflib
        import owlready2 as owl
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        sys.exit(1)

    # 1. 构建投影：替换 xsd:duration 与 geo:wktLiteral -> xsd:string
    print("[1] Building datatype projection...")
    g = rdflib.Graph()
    g.parse(str(OWL_PATH), format="xml")

    XSD = rdflib.Namespace("http://www.w3.org/2001/XMLSchema#")
    GEO = rdflib.Namespace("http://www.opengis.net/ont/geosparql#")
    forbidden = {XSD.duration, GEO.wktLiteral}

    replacements = 0
    for s, p, o in list(g):
        if o in forbidden:
            g.remove((s, p, o))
            g.add((s, p, XSD.string))
            replacements += 1

    # 清理对 geo:wktLiteral 自身的任何类型声明
    for s in list(g.subjects(rdflib.RDF.type, GEO.wktLiteral)):
        g.remove((s, rdflib.RDF.type, GEO.wktLiteral))

    fd, proj_path = tempfile.mkstemp(suffix=".owl")
    os.close(fd)
    proj_path = Path(proj_path)
    g.serialize(destination=str(proj_path), format="xml")
    print(f"  Projected file: {proj_path}")
    print(f"  Replaced {replacements} datatype references")

    # 2. 用 owlready2 加载投影（使用独立 World，避免与原始本体混合）
    print("[2] Loading projected ontology into owlready2...")
    world = owl.World()
    onto = world.get_ontology(str(proj_path)).load()
    classes = list(onto.classes())
    print(f"  Classes: {len(classes)}")

    # 3. 运行 HermiT
    print("[3] Running HermiT reasoner on projection...")
    try:
        with onto:
            owl.sync_reasoner(infer_property_values=True, debug=0)
        print("  [PASS] HermiT reasoning completed")
    except Exception as e:
        print(f"  [FAIL] HermiT reasoning failed: {e}")
        sys.exit(1)

    # 4. 一致性
    print("[4] Consistency check...")
    inconsistent = owl.Nothing in owl.Thing.equivalent_to
    if inconsistent:
        print("  [FAIL] Ontology is INCONSISTENT under HermiT projection")
        sys.exit(1)
    print("  [PASS] Ontology is consistent under HermiT projection")

    # 5. 不可满足类
    print("[5] Unsatisfiable class check...")
    unsatisfiable = []
    for cls in classes:
        try:
            if owl.Nothing in cls.equivalent_to or owl.Nothing in cls.is_a:
                unsatisfiable.append(cls)
        except Exception:
            pass
    if unsatisfiable:
        print(f"  [FAIL] Found {len(unsatisfiable)} unsatisfiable classes:")
        for cls in unsatisfiable:
            print(f"    - {cls.name}")
        sys.exit(1)
    print("  [PASS] No unsatisfiable classes found")

    # 6. 清理临时文件
    try:
        proj_path.unlink(missing_ok=True)
    except Exception:
        pass

    print("=" * 70)
    print("HermiT projection check: ALL PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
