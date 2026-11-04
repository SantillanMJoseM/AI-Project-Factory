ALLOWED = {
    "PENDING": {"ASSIGNED"},
    "ASSIGNED": {"RUNNING"},
    "RUNNING": {"BLOCKED", "REVIEW_REQUIRED", "COMPLETED", "FAILED"},
    "BLOCKED": {"RUNNING", "CANCELLED"},
    "REVIEW_REQUIRED": {"COMPLETED", "REJECTED"},
    "REJECTED": {"RUNNING"},
    "FAILED": {"PENDING"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}

def can_transition(src, dst):
    # Any non-terminal may cancel; model above includes explicit; add global cancel
    if dst == "CANCELLED" and src not in ("COMPLETED", "CANCELLED"):
        return True
    return dst in ALLOWED.get(src, set())

def test_allowed_transitions():
    assert can_transition("PENDING", "ASSIGNED")
    assert can_transition("RUNNING", "COMPLETED")
    assert can_transition("RUNNING", "CANCELLED")

def test_disallowed_transitions():
    assert not can_transition("COMPLETED", "RUNNING")
    assert not can_transition("PENDING", "COMPLETED")
    assert not can_transition("CANCELLED", "RUNNING")

if __name__ == "__main__":
    test_allowed_transitions()
    test_disallowed_transitions()
    print("PASS state transitions")
