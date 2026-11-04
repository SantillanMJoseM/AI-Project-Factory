from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_risk_matrix_exists():
    assert (ROOT / "orchestration/policies/risk-matrix.md").is_file()

def test_severity_matrix_exists():
    assert (ROOT / "quality-gates/development/defect-severity-matrix.md").is_file()

if __name__ == "__main__":
    test_risk_matrix_exists()
    test_severity_matrix_exists()
    print("PASS f1 policies")
