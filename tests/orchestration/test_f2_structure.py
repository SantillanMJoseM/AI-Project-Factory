from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_f2_agents():
    for aid in ["ag-004","ag-005","ag-006","ag-007"]:
        files = list((ROOT / "agents" / "analysis").glob(f"{aid}-*.md"))
        assert files, aid
    for aid in ["ag-004-business-analyst","ag-005-software-architect","ag-006-ux-ui-designer","ag-007-database-architect"]:
        assert (ROOT / ".opencode" / "agents" / f"{aid}.md").is_file()

def test_f2_schemas():
    names = ["project-requirements.schema.json","user-story.schema.json","architecture-component.schema.json","architecture-decision.schema.json","ui-screen.schema.json","database-entity.schema.json","traceability-matrix.schema.json"]
    for name in names:
        assert (ROOT / "schemas" / name).is_file()

def test_f2_quality_gates():
    assert len(list((ROOT / "quality-gates" / "f2").glob("*.md"))) == 6

if __name__ == "__main__":
    test_f2_agents()
    test_f2_schemas()
    test_f2_quality_gates()
    print("PASS f2 structure")
