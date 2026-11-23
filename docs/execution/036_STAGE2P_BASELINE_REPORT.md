# Stage 2P — Baseline Report

Date: 2026-11-23
Branch: feature/model-fallback-manager
HEAD: f676d7116dcbf252dd5da0bb19c42e0b657a6e14

## 1. Estado real verificado

- 18 agentes V2 + assessor (19 ejecutables), todos beam-free, todos cargan en OpenCode.
- 56 Skills presentes, 5 LIVE_VERIFIED.
- 17 ejecuciones (EXEC-0001..0017), todas COMPLETED/INTERRUPTED, todas beam-free.
- Continuidad: snapshots/context/ledger automáticos en run_task (Stage 2N), recovery entre sesiones (Stage 2O).
- SQLite: integrity ok. Counts: projects=10, tasks=15, executions=17, AV=9, audits=9.
- Backup: backups/AI-Project-Factory-pre-2p-20261123141103.tar.gz (SHA256: 99e831c2...)

## 2. Archivos verificados

- docs/execution/027_STAGE2N_FINAL_REPORT.md — existe.
- docs/execution/035_STAGE2O_FINAL_REPORT.md — existe.
- docs/execution/SKILLS_COVERAGE_MATRIX_2H.md — existe (5 LIVE_VERIFIED).
- docs/execution/PERMISSIONS_MATRIX_2H.md — existe.
- docs/execution/LXC_INSTALL_PROCEDURE_2H.md — existe.

## 3. Gate A

- Inventario verificado. Backup verificado. Proceder.