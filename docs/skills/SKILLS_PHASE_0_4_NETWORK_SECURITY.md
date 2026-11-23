# Skills Phase 0.4 — Network Security

**Date:** 2026-11-19

## Controls
- `webfetch: deny` and `websearch: deny` in all 18 agents.
- `external_directory: deny` confines file access to the workspace.
- No network tools available to agents with these denials.

## Test evidence
- Pilot agent with `webfetch: deny` could not fetch `https://example.com` via shell (permission rejected).
- No external requests observed during skill loading tests.

## Distinction
- Tool-level restrictions (OpenCode permissions) vs. OS-level network controls.
- Our runtime adds URL/download detection in the security scanner.