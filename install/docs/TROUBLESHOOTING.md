# Troubleshooting

## OpenCode not found

```bash
which opencode
# If empty, install it: npm install -g @opencode/cli@2.2.5
```

## Agent not found

Ensure the worktree contains `.opencode/agents/` and `opencode.json`. The sandbox materializes these automatically.

## Permission denied inside sandbox

The LXC needs `nesting=1`:

```bash
pct set <ctid> --features nesting=1
```

## Mount namespace fails

Check that user namespaces are enabled:

```bash
sysctl kernel.unprivileged_userns_clone
# Should be 1
```

## Model quota exhausted

```
provider.free-limit
```

Wait for quota reset, switch model, or configure a paid provider key.

## Database migration failed

Migration 4 is atomic. If it fails:

1. Restore from backup.
2. Fix the underlying issue (e.g., duplicate RUNNING executions).
3. Re-run.

## Tests fail

```bash
cd /opt/ai-project-factory
rm -f orchestration/runtime/runtime.db*
python3 tests/run_all.py
```
