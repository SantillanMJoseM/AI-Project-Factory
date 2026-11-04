# Development Task Contract

## Purpose

Defines a development task assigned to a development agent.

## Required fields

- task_id
- project_id
- module_id
- agent_id
- objective
- requirements
- dependencies
- assigned_files
- allowed_directories
- expected_artifacts
- acceptance_criteria
- test_requirements
- git_branch
- status

## Statuses

Uses task states: PENDING, ASSIGNED, RUNNING, BLOCKED, REVIEW_REQUIRED, REJECTED, COMPLETED, FAILED, CANCELLED.

## Rules

1. Each task has one owner.
2. Assigned files must be within allowed directories.
3. No two tasks may modify the same files without explicit coordination.
4. Status changes follow Task Contract transitions.