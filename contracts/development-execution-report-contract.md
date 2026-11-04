# Development Execution Report Contract

## Purpose

Defines the report returned by a development agent.

## Required fields

- execution_id
- modified_files
- generated_artifacts
- implementation_summary
- tests_executed
- test_results
- known_issues
- technical_decisions
- commit_reference
- handoff_notes

## Rules

1. Every modified file must be listed.
2. Test results must be recorded.
3. Known issues must be explicit.
4. Commit reference must identify the related change.