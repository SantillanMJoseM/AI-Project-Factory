# Agent Delegation Workflow

## Rules

- Primary agents may invoke subagents via task tool according to permissions.
- Delegation must include task context and expected output.
- Subagent results return to the invoking agent.
- Nested subagent depth defaults to 1.