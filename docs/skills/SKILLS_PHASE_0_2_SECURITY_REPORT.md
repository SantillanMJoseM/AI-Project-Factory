# Skills Phase 0.2 — Security Report

**Date:** 2026-11-19  
**Scope:** Adversarial review of permission and instruction-injection risks for Skills.

## 1. Threat model
- A Skill is untrusted content. It may contain instructions attempting to escalate privileges, read secrets, modify policies, execute commands, or alter other Skills.
- The agent's effective tool permissions (OpenCode) are the primary enforcement boundary.
- Our registry/validator/security scan are advisory gates, not runtime enforcement.

## 2. Adversarial cases designed
1. Skill requests additional permissions in its body.
2. Skill instructs modification of normative agents/policies.
3. Skill instructs bash execution.
4. Skill instructs reading files outside workspace (e.g. secrets).
5. Skill instructs editing configuration files.
6. Skill instructs accessing fictitious secrets.
7. Skill instructs modifying other Skills.
8. Skill uses prompt-injection markers ("ignore previous instructions", "do not tell the user").

## 3. Results
- Security scan (`orchestration/skills/security_scan.py`) detects injection markers, fetch-and-execute patterns, egress URLs, encoded payloads, `/dev/tcp`, destructive commands, sudo, credential shapes, CI hooks, and executable assets.
- Missing/untrusted provenance and incompatible licenses produce BLOCKED.
- However, the scanner is static and heuristic; it cannot prove absence of semantic attacks.
- OQ-4 (permission enforcement) remains open: a Skill loaded in this environment was not demonstrably blocked by `skill: deny` under V1 syntax.

## 4. Verdict
- **PASS_WITH_OBSERVATIONS** for the offline controls.
- **BLOCKED** for the claim "Skills cannot expand permissions in all cases" until OQ-4 is verified with V2 syntax and runtime tests.

## 5. Residual risks
- R-SEC-1: V1 permission syntax may not enforce as expected.
- R-SEC-2: Static scan can be evaded by semantic/obfuscated instructions.
- R-SEC-3: No live proof of deny enforcement for explicit `@skill-id`.
- R-SEC-4: Human review (AG-015) still required for any real Skill.