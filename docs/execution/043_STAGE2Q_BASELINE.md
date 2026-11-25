# Stage 2Q — Baseline Report

Date: 2026-11-23
Branch: feature/model-fallback-manager
HEAD: f676d7116dcbf252dd5da0bb19c42e0b657a6e14

## 1. Estado real verificado

- Rama: feature/model-fallback-manager. HEAD: f676d711.
- Usuario: developer. Git status: modified tracked + untracked artifacts.
- 18 agentes V2 + assessor (19 ejecutables), todos beam-free, todos cargan en OpenCode.
- 54 Skills presentes, 5 LIVE_VERIFIED.
- 17 ejecuciones (EXEC-0001..0017), todas beam-free.
- 9 acceptance verifications (AV-0001..0009).
- 9 audits (AUDIT-0001..0009).
- SQLite: integrity ok. Counts: projects=10, tasks=15, executions=17, model_fallback_log=17, events=135, delegations=0.
- Snapshots: 13 (PROJECT-007..0010). Context: 7. Ledger: 7.
- Backup: backups/AI-Project-Factory-pre-2q-20261123142517.tar.gz (SHA256: 8a141738...)

## 2. Verificación de modelo

- All 19 agents: opencode-go/beam-free (verified via opencode debug agents).
- All 17 executions: effective_model = opencode-go/beam-free (verified via SQLite).
- opencode.json: model=beam-free, no ollama provider.

## 3. Gate A

- Baseline verificado. Proceder a auditoría.