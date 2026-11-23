# Stage 0.1 Skills Multimodel and Permission Observation Report

| Field | Value |
|---|---|
| doc_id | SKILLS-PHASE-0-1-MULTIMODEL-REPORT-0001 |
| created_at | 2026-11-19 |
| author | AG-018 Documentation Engineer |
| status | OBSERVATION REPORT — records a three-provider experiment and one open permission observation; **not** a gate PASS, an approved model matrix, or proof of permission enforcement |
| stage | Stage 0.1 — multimodel discovery/interpretation and OQ-4 (permission semantics) |
| experiment project | `/tmp/opencode/perm-test` (external temporary project, **not** the factory repository) |
| skill under test | `.opencode/skills/valid-skill` — `SKILL.md` + `references/guide.md` (read-only guidance skill) |
| providers | `opencode-go/hy4-flash-free`, `opencode/inkling-2-small-free`, `opencode-go/longcat-2.5-free` |
| related open items | OQ-4 (installed-build permission semantics), ES-3 (no approved multimodel matrix), ADR-003 (verify against installed build) |

---

## 1. Purpose and scope

This report records what was actually observed when the same project-local guidance skill was made available to three different model providers, plus a permission experiment. Its purpose is descriptive: to show which behaviours were reproduced across providers and which remain unproven.

Per ADR-003, the experiment is an observation against the environments used, not a substitute for the G6 live gate on the installed OpenCode build with recorded version, and not an approval of any skill for adoption.

## 2. Setup

- Project: `/tmp/opencode/perm-test`.
- Skill location: `.opencode/skills/valid-skill/` containing `SKILL.md` and `references/guide.md`.
- Skill content posture: short, read-only guidance (summarise a local checklist; keep work inside the workspace; **make no external requests**; performs no actions of its own).
- Invocation: skills were loaded and explicitly referenced with `@valid-skill` in at least the permission experiment; the multimodel runs loaded/interpreted the skill.
- No external skill was downloaded, installed or enabled in the factory repository by this experiment. The factory repository's own fixture `tests/fixtures/skills/valid-skill/` remains local test data; the experiment project is outside the repository.

## 3. Multimodel results

| Provider / model | Discovery | Interpretation of `SKILL.md` | Supporting reference (`references/guide.md`) | Read-only guidance | External requests | Result |
|---|---|---|---|---|---|---|
| `opencode-go/hy4-flash-free` | PASS — skill loaded/available | PASS — followed the skill's instructions | PASS — reference file read | Respected | None observed | **PASS: discovery + interpretation + reference read** |
| `opencode/inkling-2-small-free` | PASS — skill loaded/available | PASS — interpreted the skill | Not evidenced in the first run — reference file absent; skill interpreted from `SKILL.md` | Respected | None observed | **PASS: discovery + interpretation** |
| `opencode-go/longcat-2.5-free` | PASS — skill loaded/available | PASS — interpreted the skill | Not evidenced in the first run — reference file absent; skill interpreted from `SKILL.md` | Respected | None observed | **PASS: discovery + interpretation** |

All three providers loaded the skill and respected its read-only guidance; no external requests were observed. The skill was treated as instructions/data to interpret, not as code to execute.

### 3.1 Interpretation of the results

- **Reproduced across all three providers:** project-local skill discovery, loading, and interpretation of the guidance in `SKILL.md`; compliance with the "no external requests / read-only" instruction.
- **Not reproduced uniformly:** reading `references/guide.md` was confirmed for `hy4-flash-free`; for the other two providers the reference file was absent in the first run, so only `SKILL.md`-level interpretation is evidenced. This is recorded as an observation, **not** as a claim that supporting files auto-load (or fail to auto-load) in any provider. The difference may be a file-availability issue in the first run rather than a provider behaviour difference; it was not re-probed for this report.
- **Not an approved matrix:** only three providers were exercised. ES-3 ("no approved multimodel test matrix") remains open; no compatibility verdict vocabulary was frozen by this experiment (ES-5). No result here changes a registry posture or approves a skill for promotion.

## 4. Permission experiment — OQ-4 (open observation)

**Observation as supplied:** an agent configured with `read`, `bash` and `skill` **deny** still loaded the skill when it was referenced explicitly as `@valid-skill` in this environment. In the CLI test performed, the `read`/`bash` denial was **not demonstrably enforced** through the skill's frontmatter.

**Honest classification:** this is an **open observation, not proof**. It neither establishes that the installed OpenCode build honours `deny` rules for skills nor that it ignores them universally; the test setup did not isolate the enforcement path with sufficient control to attribute the outcome to a specific mechanism. It must not be reported as "permissions verified" or "full enforcement".

**Consequences:**

- OQ-4 remains **OPEN**. The authoritative resolution is the G6 live V-4/V-5 discovery and invocation probe on the installed build, with the build version recorded and permission effects checked per class (deny/ask/allow).
- No `allow`/`ask`/`deny` posture in the skills registry is validated by this experiment; the derived permission configuration remains metadata until G6 verifies its live effect (`SKILLS_PERMISSION_MODEL.md`, `SKILLS_VALIDATION_FRAMEWORK.md`).
- Frontmatter in the experiment was Plane A guidance (`autoinvoke: false` style metadata); it is not a permission-control channel. Governance fields in frontmatter are rejected by the offline validator (V-2), and the fail-closed permission model is expressed in the registry/derived config, not asserted by a skill's own frontmatter.
- Per ADR-004 (independent audit) and factory policy §16, human final approval remains mandatory for all LEVEL C operations regardless of any token-level observation.

## 5. What this report does and does not claim

**Claims:**

- Three named providers discovered, loaded and interpreted the read-only `valid-skill` in `/tmp/opencode/perm-test`; all three respected the no-external-requests guidance.
- One provider additionally read `references/guide.md` in the runs observed; two did not have the reference present in their first run.
- A deny-configured agent still loaded the skill via explicit `@valid-skill` in this environment; read/bash denial was not demonstrably enforced in the CLI test.

**Does not claim:**

- That skill permission rules (`deny`/`ask`/`allow`) or `autoinvoke` semantics are verified, enforced, or fully implemented in the installed OpenCode build (OQ-4 open).
- That supporting-file auto-loading works uniformly across providers.
- That any provider/model is approved, preferred, or part of an approved matrix (ES-3 open).
- That a skill is USABLE at Stage 0/0.1, that G6 passed, or that the factory repository now contains an installed skill.
- Any security guarantee about skill content; the independent V-6 review verdict and its conditions govern that question.

## 6. Evidence and companion documents

- Experiment data supplied for Stage 0.1 (provider outcomes and permission observation); reproduced here without upgrading its status.
- Skill under test: `/tmp/opencode/perm-test/.opencode/skills/valid-skill/SKILL.md` and `references/guide.md` (external temp project).
- Local fixture analogue: `tests/fixtures/skills/valid-skill/` (in-repository test data only).
- `SKILLS_PHASE_0_1_TEST_REPORT.md` — offline suite, 115 PASS aggregate.
- `SKILLS_PHASE_0_1_SECURITY_REVIEW.md` — AG-015 verdict, session `ses_e0bfce0b8ffemcG0O03RIKN11Z`.
- `SKILLS_PHASE_0_1_COMPLETION.md` — criteria closure status.
- `SKILLS_PERMISSION_MODEL.md` §OQ-4, `SKILLS_VALIDATION_FRAMEWORK.md` §V-4/V-5, `SKILLS_ADOPTION_PLAN.md` §5 (G6).
