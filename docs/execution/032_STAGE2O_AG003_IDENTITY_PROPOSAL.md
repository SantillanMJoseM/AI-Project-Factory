# Stage 2O — AG-003 Identity Proposal

Date: 2026-11-23
Branch: feature/model-fallback-manager

## 1. Responsabilidades

- Risk Manager (.opencode/agents/ag-003-security-risk-manager.md): risk classification LEVEL A/B/C, permission verification, blocking unauthorized/unsafe operations.
- Security Risk Assessor (.opencode/agents/ag-003-security-risk-assessor.md): vulnerability assessment, compliance, security requirements.

## 2. Diferencias funcionales

- Risk Manager: operational risk classification, permission enforcement, blocking.
- Security Risk Assessor: security vulnerability assessment, compliance checking, security requirement extraction.

## 3. Propuesta

- Dos especializaciones distintas bajo AG-003 identity.
- Ambos preservados. No file rename, no ID change, no deletion.
- Requires user authorization for further identity changes.

## 4. Impacto

- Permisos: both deny-by-default, beam-free.
- Skills: risk manager (stride, threat-mitigation, attack-tree, security-requirement-extraction, sast, secrets); assessor (same set, complementary).
- Delegación: AG-001 can select either based on task content.