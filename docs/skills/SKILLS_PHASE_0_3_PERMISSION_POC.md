# Skills Phase 0.3 — Permission Proof of Concept

**Date:** 2026-11-19  
**Environment:** OpenCode v2.2.5 (`/home/developer/.opencode/bin/opencode`), project config V2 with `permissions` arrays in agent frontmatter.

## 1. Environment identification
- OpenCode version: `v2.2.5`.
- Configuration schema: V2 (`permissions` array of `{action, resource, effect}`).
- V1 frontmatter (`permission:` map) is deprecated but still read for compatibility.
- No global configuration file present (`~/.config/opencode/` contains only `service.json`).
- Project-level configuration used only in isolated test projects under `/tmp/opencode/perm-poc`.

## 2. Isolated test agents
- `skill-deny`: `skill: deny`, `read: deny`, `shell: deny`, `edit: deny`, `execute: deny`.
- `skill-readonly`: `skill: allow`, `read: allow`, `external_directory: deny`, `shell: deny`, `edit: deny`, `webfetch: deny`, `execute: deny`.
- `skill-controlled`: `skill: allow`, `read: allow`, `external_directory: deny`, `shell: * ask` then `shell: echo * allow`, `edit: deny`, `webfetch: deny`, `execute: deny`.

## 3. Real test results
| Test | Agent | Result |
|---|---|---|
| Load `@valid-skill` | skill-deny | **Blocked** — `Permission denied: skill` |
| Load `@valid-skill` + read ref | skill-readonly | **Allowed** — skill loaded and reference read |
| Read `/etc/hostname` | skill-readonly | **Allowed** (read * permits any path, including outside workspace) |
| Read `/etc/hostname` | skill-readonly with `external_directory: deny` | **Blocked** — `external_directory` denied |
| Read inside workspace | skill-readonly | **Allowed** |
| Run `echo PWNED` | skill-controlled (allow echo *, ask *) | **Allowed** (rule order: broad ask then specific allow) |
| Run `whoami` | skill-controlled | **Blocked** — auto-rejected in non-interactive run |
| Read `../secret.txt` | skill-readonly | Allowed by permission, failed only on file existence |
| Fetch network | skill-readonly | No webfetch tool / cancelled |
| Load unknown skill `nope` | any | Blocked — skill not found |

## 4. Permission precedence
- OpenCode combines global and agent rules; agent rules are appended after global rules.
- Last matching rule wins.
- Correct ordering is required: broad rules first, specific exceptions last.
- `external_directory` is a separate action that gates reads/writes outside the working directory.

## 5. Subagent isolation
- A subagent uses its own configured permissions, not a subset of the parent's permissions (per official docs).
- Therefore, subagent permissions must be explicitly configured; inheritance is not restrictive by default.
- Parent agents cannot rely on their own restrictions to constrain a subagent.

## 6. Governance model
- Skills provide instructions/knowledge only; they do not grant capabilities.
- Agents retain their own permissions.
- Runtime controls assignment, validation, versioning, and rollback.
- Sensitive actions remain protected by OpenCode permissions + our task contract + risk classification.
- Skills cannot modify normative policies by construction (no write access to protected paths; validator and governance gates).

## 7. Native vs. additional controls
- Native: discovery, `skill` permission, tool permissions, external_directory, subagent permissions, ask/allow/deny.
- Additional (ours): registry, validation harness V1–V8, security scan, license check, task contract, drift detection, versioning/rollback, audit evidence.

## 8. Conclusion
- Effective permission enforcement is achievable with V2 `permissions` arrays and correct rule ordering.
- V1 `permission:` map syntax is deprecated and may not enforce reliably.
- OQ-4 is **partially resolved**: command-level and external-directory restrictions are proven; V1 inconsistency remains an open risk until migration/verification.