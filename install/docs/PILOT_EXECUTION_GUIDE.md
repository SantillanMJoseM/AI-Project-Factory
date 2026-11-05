# ProjectDesk Pilot Execution Guide

## Goal

Use AI-Project-Factory to develop `ProjectDesk`, a small project management application.

## 1. Prepare the project repository

```bash
# Create ProjectDesk repository (or clone existing pilot repo)
mkdir -p /tmp/opencode/worktrees/projectdesk
cd /tmp/opencode/worktrees/projectdesk
git init
```

## 2. Register the project in Factory

```bash
cd /opt/ai-project-factory
export APF_DB_PATH=/opt/ai-project-factory/orchestration/runtime/runtime.db
python3 -m orchestration.runtime project register \
  --name ProjectDesk \
  --repo-path /tmp/opencode/worktrees/projectdesk \
  --coordinator-agent AG-001
```

## 3. Create tasks

Example using the runtime CLI or Python API:

```bash
python3 -m orchestration.runtime task create \
  --project PROJECT-001 \
  --agent AG-004 \
  --title "Analyze requirements" \
  --objective "Define ProjectDesk functional requirements" \
  --priority high
```

Create tasks for:
- Requirements analysis (AG-004)
- Architecture (AG-005)
- Database design (AG-007)
- Backend implementation (AG-008)
- Frontend implementation (AG-009)
- Integration (AG-011)
- QA tests (AG-012)
- Security audit (AG-015)
- Documentation (AG-018)

## 4. Run the workflow

```bash
python3 -m orchestration.runtime workflow start --project PROJECT-001 --workflow standard-delivery
python3 -m orchestration.runtime workflow run --run-id RUN-XXXX --model opencode-go/qwen3.8-flash
```

Or run tasks individually:

```bash
python3 -m orchestration.runtime task run --task TASK-0001 --model opencode-go/qwen3.8-flash
```

## 5. Quality Gates

After each stage, run the Quality Gate:

```bash
python3 -m orchestration.validators.quality_gate validate \
  --certificate projects/PROJECT-001/quality/QUALITY_CERTIFICATE.json \
  --evidence-dir projects/PROJECT-001/evidence/
```

## 6. Independent review

Request AG-002 to audit the stage:

```bash
python3 -m orchestration.runtime audit request --project PROJECT-001 --scope stage --auditor AG-002
```

## 7. Publish ProjectDesk

```bash
cd /tmp/opencode/worktrees/projectdesk
git remote add origin https://github.com/SantillanMJoseM/AI-Project-Factory-Pilot.git
git checkout -b projectdesk
git add .
git commit -m "ProjectDesk delivery"
git push origin projectdesk
```

## 8. Generate report

The final report is created at:

```
docs/pilot/FACTORY_FIRST_INSTALL_AND_PROJECTDESK_REPORT.md
```
