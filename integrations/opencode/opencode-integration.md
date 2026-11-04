# OpenCode Integration

## Overview

AI-Project-Factory uses OpenCode as initial runtime. Agent definitions are stored in `.opencode/agents/` as Markdown files with YAML frontmatter. Normative contracts remain in `agents/`.

## Verified capabilities

- Markdown agent definitions with frontmatter.
- Subagents and primary agents.
- Permission configuration per agent.
- Task tool delegation controlled by `permission.task`.
- Project configuration via `opencode.json`.
- Instructions via `instructions`.

## Model portability

No model is hard-coded in agent definitions. Model selection is configured in `opencode.json` or globally.

## Limitations

- Experimental features are not used.
- Production deployment is not automated by OpenCode integration.