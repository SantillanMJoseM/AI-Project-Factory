# Risk Matrix

| Operation | Level | Approval |
|---|---|---|
| Read files | A | Autonomous |
| Edit non-critical files | A | Autonomous with audit |
| Run authorized tests | A | Autonomous |
| External network access | B | Context-dependent |
| Dependency changes | B | Context-dependent |
| Infrastructure changes | B | Context-dependent |
| Production deployment | C | Explicit human approval |
| Data deletion | C | Explicit human approval |
| Credential changes | C | Explicit human approval |
| Policy changes | C | Explicit human approval |
| Irreversible operations | C | Explicit human approval |
| Security exceptions | C | Explicit human approval |
| Quality Gate bypass | C | Explicit human approval |