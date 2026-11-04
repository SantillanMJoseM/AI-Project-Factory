from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_policy_files_exist():
    expected = [
        "orchestration/policies/context-policy.md",
        "orchestration/policies/security-policy.md",
        "orchestration/policies/approval-policy.md",
        "orchestration/policies/model-portability-policy.md",
    ]
    for rel in expected:
        assert (ROOT / rel).is_file(), rel

def test_no_secret_like_files():
    forbidden = [".env", "secrets", "credentials.json"]
    for name in forbidden:
        assert not (ROOT / name).exists(), name

if __name__ == "__main__":
    test_policy_files_exist()
    test_no_secret_like_files()
    print("PASS policies")
