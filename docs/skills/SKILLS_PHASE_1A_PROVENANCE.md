# Skills Phase 1A — Provenance

**Date:** 2026-11-19

## Sources
- obra/superpowers @ commit `22f0b463e7a5e579904dd6211a520321035526f7` (2 skills: verification-before-completion, receiving-code-review)
- wshobson/agents @ commit `42203085cfc5736204bf0f6d436dff7e1da0bf3f` (15 skills)

## Provenance records
- Full provenance (repo, commit, upstream path, file hashes) recorded in `orchestration/skills/registry.json`.
- License: MIT (repo-level claim, verified by AG-015).
- No local modifications to skill content.
- SHA-256 hashes computed for every vendored file.

## Verification
- Registry entries validated by `Registry.load()` and `tests/run_all.py`.
- Security scan: all 17 ACCEPT (risk class A).