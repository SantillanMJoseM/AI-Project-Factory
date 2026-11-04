# AUDIT-TEST-F2-006 — PROJECT-001 Cross-Consistency: FUNCTIONAL_REQUIREMENTS vs COMPONENT_DIAGRAM

- Auditor: AG-002 Quality Gatekeeper (independent)
- Date: 2026-11-04
- Scope: `requirements/FUNCTIONAL_REQUIREMENTS.md` ↔ `architecture/COMPONENT_DIAGRAM.md`; detection of nonexistent REQ IDs.
- Method: full read of both artifacts; mechanical regex extraction of all REQ/COMP tokens (ranges expanded); set-difference against the canonical registry; reverse coverage check; project-wide grep to rule out an alternate ID registry. Audited files unmodified.

## 1. Canonical baseline (evidence)

`FUNCTIONAL_REQUIREMENTS.md` defines, via section headers, exactly:
REQ-0001, REQ-0002, REQ-0003, REQ-0004, REQ-0005 (lines 35, 54, 73, 91, 109).
Internal cross-references within that document are self-consistent (0 dangling refs).

## 2. Findings

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| D-001 | Major | All 13 provisional IDs (`REQ-UI-001..004`, `REQ-TASK-001..005`, `REQ-AUTH-001..004`) do not exist in the requirements baseline. Zero of them appear anywhere under `requirements/`. | COMPONENT_DIAGRAM lines 54–57, 74–78, 95–98, 104–106; grep across `requirements/` = NOT FOUND |
| D-002 | Critical | Orphan section "TEST CONTRADICTION" (lines 128–130) asserts `COMP-9999` references `REQ-9999`. Both IDs are nonexistent: `COMP-9999` appears nowhere else in the project and is not a defined component (§3 lists only Web UI, Task API, Auth Service); `REQ-9999` is not in any registry. The section sits after the change log, has no author/version entry, and matches no document convention — unattributed content, document-integrity defect. | lines 128–130; `grep -rn "COMP-"` returns only that line |
| D-003 | Major | Reverse traceability gap: the diagram references no canonical `REQ-000N` ID. No component covers REQ-0004 (lists/priority/sorting) or REQ-0005 (due dates/overdue highlighting) explicitly. Architecture cannot be validated against the approved scope. | grep `REQ-000[1-5]` in COMPONENT_DIAGRAM = NOT FOUND |

Aggravating process finding: AG-004 escalated (§7 of FUNCTIONAL_REQUIREMENTS.md) that architecture should not consume this document before stakeholder validation; the diagram was nevertheless produced (and self-declares, lines 7–11, 110–113, that requirements "were not read"). The self-declaration mitigates intent for D-001 but not the artifact-level breakage, and does not cover D-002, which is absent from the document's own caveat.

## 3. Nonexistent REQ IDs (complete list, 14)

REQ-9999, REQ-AUTH-001, REQ-AUTH-002, REQ-AUTH-003, REQ-AUTH-004, REQ-TASK-001, REQ-TASK-002, REQ-TASK-003, REQ-TASK-004, REQ-TASK-005, REQ-UI-001, REQ-UI-002, REQ-UI-003, REQ-UI-004.

## 4. Verdict

**FAIL — COMPONENT_DIAGRAM.md v0.1 is not acceptable.**
- FUNCTIONAL_REQUIREMENTS.md: internally consistent; remains Draft pending OQ-001 (upstream condition, not a cross-consistency defect).
- COMPONENT_DIAGRAM.md: REJECTED for acceptance. Mandatory rework before re-audit:
  1. Remove or attribute/justify the "TEST CONTRADICTION" section (D-002) — explain provenance to AG-001; possible unauthorized/unverified edit.
  2. Replace provisional IDs with mappings to canonical REQ-0001..0005 (D-001, D-003) once the baseline is approved; produce a component→REQ traceability table covering REQ-0004 and REQ-0005.
  3. Honor the AG-004 escalation gate: no architecture artifact enters reconciliation until OQ-001 is answered.
- Note: repository is not a Git checkout at this path; version-control verification could not be performed. Recorded for AG-001.

Audit type: cross-consistency (TEST-F2-006). Result: defects detected; verdict FAIL with 1 Critical, 2 Major.
