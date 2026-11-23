# Configuration Guide

## OpenCode provider

AI-Project-Factory uses OpenCode v2.2.5. The provider and model are configured through environment variables or OpenCode's own configuration.

### Beam / OpenCode Go provider

```bash
export OPENCODE_API_KEY="your-api-key"
```

### Model policy (BEAM_FREE_ONLY)

AI-Project-Factory uses exclusively `opencode-go/beam-free`. No other providers or models are authorized. Do not set OPENAI_API_KEY, ANTHROPIC_API_KEY, or other provider keys for this project.

## Runtime configuration

| Variable | Default | Description |
|---|---|---|
| `APF_DB_PATH` | `orchestration/runtime/runtime.db` | SQLite database path |
| `APF_LOG_LEVEL` | `info` | Log level |
| `OPENCODE_BIN` | `opencode` | Path to OpenCode binary |

## Permission model

- Factory agents have explicit permissions in `.opencode/agents/*.md`.
- `AG-001` can delegate only to agents matching `ag-*`.
- All factory agents deny `execute` (Code Mode) and `webfetch`/`websearch`.
- `bash` and `edit` are `ask` for most agents; non-interactive runs fail closed.

## Sandbox

The sandbox runs a private OpenCode server inside a user+mount namespace:

```bash
unshare -Urm /bin/bash sandbox-script.sh
```

Factory root paths are masked with tmpfs. Normative directories are bind-mounted read-only into the worktree.

## Network isolation

The sandbox does **not** use a network namespace, because the server must reach the model provider. Agent tool network access is controlled by OpenCode permissions. For stricter isolation, run the LXC behind a firewall that restricts outbound destinations.
