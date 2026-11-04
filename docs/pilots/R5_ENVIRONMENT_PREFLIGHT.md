# R5 Environment Preflight

Run:

```bash
python3 -m orchestration.preflight.r5
```

Optional controlled agent invocation:

```bash
APF_PREFLIGHT_INVOKE=1 python3 -m orchestration.preflight.r5
```

Checks include Python, repository, OpenCode, agents, runtime, validators, tests, permissions, and project isolation. Results use PASS, FAIL, BLOCKED, and NOT_VERIFIED.