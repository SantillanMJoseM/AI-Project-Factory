# Skills Phase 0.5 — Multimodel Validation

**Date:** 2026-11-19

## Providers tested
1. `opencode-go/hy4-flash-free` — PASS (discovery, interpretation, reference read).
2. `opencode/inkling-2-small-free` — PASS (discovery, interpretation).
3. `opencode-go/longcat-2.5-free` — PASS (discovery, interpretation).

## Results
- All three loaded `valid-skill` and interpreted its instructions.
- Reference file read succeeded when present.
- No external requests observed.
- Restrictions (deny rules) are enforced by OpenCode, not by model compliance.

## Limitation
- Three providers do not prove universal compatibility. Additional providers should be tested when quota allows.