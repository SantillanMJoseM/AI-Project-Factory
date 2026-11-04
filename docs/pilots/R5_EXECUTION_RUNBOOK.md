# R5 Execution Runbook

## Flow

1. Register project in R3 runtime.
2. Create analysis tasks for AG-004 to AG-007.
3. Create development tasks for AG-008 to AG-011.
4. Create quality tasks for AG-012 to AG-015.
5. Create delivery tasks for AG-016 to AG-018.
6. Execute tasks through OpenCode agent adapter or documented invocation.
7. Run R1 Quality Gate.
8. Run R2 Traceability validation.
9. Prepare release and deployment plan.
10. Request human approval for staging deployment.
11. Deploy to isolated staging.
12. Run health checks and smoke tests.
13. Test rollback.
14. Generate documentation.
15. Run independent audit.

## Evidence

Store all outputs under the project's own directory and runtime database. Do not store secrets.