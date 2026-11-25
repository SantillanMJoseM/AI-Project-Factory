from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def test_structure_dirs():
    expected = ["agents/management","agents/analysis","agents/development","agents/quality","agents/delivery",
                "contracts","schemas","orchestration/workflows","quality-gates","tests","docs"]
    for rel in expected:
        assert (ROOT / rel).is_dir(), rel

def test_eighteen_agents_normative():
    files = list((ROOT / "agents").rglob("*.md"))
    assert len(files) == 18, len(files)

def test_nineteen_agents_executable():
    # Normative catalog has 18 unique agent IDs (AG-001..AG-018).
    # Executable catalog has 19 files: AG-003 ships two documented
    # specializations (security-risk-manager + security-risk-assessor)
    # under the same AG-003 identity (see docs/execution/032_STAGE2O_AG003_IDENTITY_PROPOSAL.md).
    files = list((ROOT / ".opencode" / "agents").glob("*.md"))
    assert len(files) == 19, len(files)


def test_ag003_specialization_preserved():
    normative = ROOT / "agents" / "management" / "ag-003-security-risk-manager.md"
    assessor = ROOT / ".opencode" / "agents" / "ag-003-security-risk-assessor.md"
    manager = ROOT / ".opencode" / "agents" / "ag-003-security-risk-manager.md"
    assert normative.is_file(), normative
    assert assessor.is_file(), assessor
    assert manager.is_file(), manager
    for path in (assessor, manager):
        text = path.read_text()
        assert "opencode-go/beam-free" in text, path
        assert "effect: deny" in text, path
    assert "ag-003-security-risk-assessor.md" in normative.read_text(), normative

def test_schemas_exist():
    for name in ["agent.schema.json","task.schema.json","execution.schema.json","audit.schema.json"]:
        assert (ROOT / "schemas" / name).is_file()

def test_quality_gates_count():
    files = list((ROOT / "quality-gates").rglob("*.md"))
    assert len(files) >= 6, len(files)

def test_opencode_agents_frontmatter():
    for path in (ROOT / ".opencode" / "agents").glob("*.md"):
        text = path.read_text()
        assert text.startswith("---"), path
        assert "description:" in text
        assert "mode:" in text

def test_context_files_exist():
    for name in ["AI_START_HERE.md","PROJECT_CONTEXT.md","PROJECT_STATUS.md","PROJECT_DECISIONS.md",
                 "PROJECT_PROGRESS.md","PROJECT_HANDOFF.md","PROJECT_MAP.md","SESSION_LOG.md"]:
        assert (ROOT / name).is_file()

if __name__ == "__main__":
    for fn in [test_structure_dirs, test_eighteen_agents_normative, test_nineteen_agents_executable,
               test_ag003_specialization_preserved, test_schemas_exist, test_quality_gates_count,
               test_opencode_agents_frontmatter, test_context_files_exist]:
        fn()
        print("PASS", fn.__name__)
