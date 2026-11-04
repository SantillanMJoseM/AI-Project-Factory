# Agent Contract

## Purpose

Defines the normative structure and behavior of an AI-Project-Factory agent.

## Agent identity

Each agent has a unique ID `AG-XXX`, name, domain, and version.

## Required fields

- `id`
- `name`
- `domain`
- `objective`
- `responsibilities`
- `limits`
- `inputs`
- `outputs`
- `tools`
- `permissions`
- `dependencies`
- `acceptance_criteria`
- `escalation_rules`

## Behavioral rules

1. An agent must operate only within its responsibilities.
2. An agent must not modify audit results.
3. An agent must not perform critical operations without approval.
4. An agent must record outputs in the required contract format.
5. An agent must escalate when limits are exceeded.

## Independence

Quality agents and auditors must be independent from development agents. An agent cannot approve its own work.

## Versioning

Changes to an agent definition require a decision record if they alter responsibilities or permissions.