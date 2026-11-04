#!/usr/bin/env python3
"""Artifact and release traceability validator for AI-Project-Factory."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
FULL_TREE_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_hash(obj, exclude=None):
    exclude = exclude or set()
    cleaned = {k: v for k, v in obj.items() if k not in exclude}
    data = json.dumps(cleaned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    cmd = ["git", "-C", str(repo)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def verify_commit(repo, commit):
    if not FULL_COMMIT_RE.match(commit):
        raise ValueError("Commit must be a full 40 or 64 character Git object ID")
    git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}")
    resolved = git(repo, "rev-parse", f"{commit}^{{commit}}")
    if resolved != commit:
        raise ValueError("Commit does not resolve to itself")
    return resolved


def tree_hash(repo, commit):
    return git(repo, "rev-parse", f"{commit}^{{tree}}")


def resolve_path(path, base):
    p = Path(path)
    if p.is_absolute():
        return p
    if (base / p).exists():
        return base / p
    return Path.cwd() / p


def evaluate(release_path, cert_path, repo=".", artifact=None, deployment_plan=None, approval=None, evidence_dir=None):
    rules = []
    release = load_json(release_path)
    cert = load_json(cert_path)
    release_dir = Path(release_path).resolve().parent

    # Required fields.
    for field in ["release_id", "project_id", "version", "commit", "artifact", "quality_certificate", "created_by"]:
        if field not in release:
            rules.append(f"Release manifest missing field: {field}")
    for field in ["certificate_id", "project_id", "version", "commit", "final_verdict", "evaluation_id"]:
        if field not in cert:
            rules.append(f"Quality certificate missing field: {field}")

    source_commit = release.get("commit") or release.get("source_commit")
    if not source_commit:
        rules.append("Release manifest missing source commit")
    cert_commit = cert.get("commit") or cert.get("source_commit")
    if not cert_commit:
        rules.append("Quality certificate missing source commit")

    # Verify commit.
    try:
        if source_commit:
            verify_commit(repo, source_commit)
    except Exception as exc:
        rules.append(f"Source commit verification failed: {exc}")

    # Tree hash.
    try:
        if source_commit:
            actual_tree = tree_hash(repo, source_commit)
            if "source_tree_hash" in release and release.get("source_tree_hash") and release["source_tree_hash"] != actual_tree:
                rules.append("Release manifest source_tree_hash does not match Git tree")
            if "source_tree_hash" in cert and cert.get("source_tree_hash") and cert["source_tree_hash"] != actual_tree:
                rules.append("Quality certificate source_tree_hash does not match Git tree")
    except Exception as exc:
        rules.append(f"Git tree hash verification failed: {exc}")

    # Commit consistency.
    if source_commit and cert_commit and source_commit != cert_commit:
        rules.append("Commit mismatch between release manifest and quality certificate")

    # Certificate verdict.
    if cert.get("final_verdict") in {"FAIL", "BLOCKED"}:
        rules.append("Quality certificate is not approved")

    # Certificate hash.
    cert_hash = canonical_json_hash(cert, exclude={"certificate_hash"})
    cert_hash_ref = release.get("quality_certificate_hash") or release.get("certificate_hash")
    if cert_hash_ref:
        if cert_hash_ref != cert_hash:
            rules.append("Quality certificate hash does not match certificate content")
    if "certificate_hash" in cert and cert.get("certificate_hash"):
        if cert["certificate_hash"] != cert_hash:
            rules.append("Quality certificate self-hash is invalid")

    # Artifact hash.
    artifact_path = None
    if artifact:
        artifact_path = Path(artifact)
    elif release.get("artifact"):
        artifact_path = resolve_path(release["artifact"], release_dir)
    artifact_hash = None
    if artifact_path and artifact_path.exists():
        artifact_hash = sha256_file(artifact_path)
        if "artifact_hash" in release and release.get("artifact_hash"):
            if release["artifact_hash"] != artifact_hash:
                rules.append("Artifact hash does not match artifact file")
    else:
        if release.get("artifact"):
            rules.append(f"Artifact file not found: {artifact_path}")

    # Release evaluation ID consistency.
    if release.get("evaluation_id") and cert.get("evaluation_id") and release["evaluation_id"] != cert["evaluation_id"]:
        rules.append("Evaluation ID mismatch between release manifest and quality certificate")

    # Deployment plan consistency.
    if deployment_plan:
        dp = load_json(deployment_plan)
        if dp.get("commit") or dp.get("source_commit"):
            dp_commit = dp.get("commit") or dp.get("source_commit")
            if dp_commit != source_commit:
                rules.append("Deployment plan commit does not match release commit")
        if dp.get("artifact_hash") and artifact_hash and dp["artifact_hash"] != artifact_hash:
            rules.append("Deployment plan artifact hash does not match artifact")
        if dp.get("environment") and release.get("target_environment") and dp["environment"] != release["target_environment"]:
            rules.append("Deployment plan environment does not match release target environment")

    # Approval consistency and non-reuse.
    if approval:
        ap = load_json(approval)
        ap_commit = ap.get("commit") or ap.get("source_commit")
        if ap_commit != source_commit:
            rules.append("Approval commit does not match release commit")
        if ap.get("artifact") and release.get("artifact") and ap["artifact"] != release["artifact"]:
            rules.append("Approval artifact does not match release artifact")
        if ap.get("artifact_hash") and artifact_hash and ap["artifact_hash"] != artifact_hash:
            rules.append("Approval artifact hash does not match artifact")
        if ap.get("environment") and release.get("target_environment") and ap["environment"] != release["target_environment"]:
            rules.append("Approval environment does not match target environment")
        if ap.get("project_id") and release.get("project_id") and ap["project_id"] != release["project_id"]:
            rules.append("Approval project does not match release project")
        if ap.get("version") and release.get("version") and ap["version"] != release["version"]:
            rules.append("Approval version does not match release version")

    # R1 integration.
    if evidence_dir:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
            from orchestration.validators.quality_gate import evaluate as qg_evaluate
            qg_cert = dict(cert)
            result = qg_evaluate(qg_cert, evidence_dir)
            if result["verdict"] not in {"PASS", "PASS_WITH_OBSERVATIONS"}:
                rules.append(f"Quality Gate Runtime verdict is {result['verdict']}")
            if result["rules_violated"]:
                rules.append("Quality Gate Runtime reported violations")
        except Exception as exc:
            rules.append(f"Quality Gate Runtime integration failed: {exc}")

    # Obsolete certificate detection: if release commit differs already caught. Modified cert hash caught.

    verdict = "PASS"
    if any("BLOCKED" in r or "commit" in r.lower() and "mismatch" in r for r in rules):
        # Conservative: any rule violation is FAIL unless critical? We'll map.
        pass
    if rules:
        if any("CRITICAL" in r.upper() for r in rules):
            verdict = "BLOCKED"
        else:
            verdict = "FAIL"

    return {
        "verdict": verdict,
        "exit_code": 0 if verdict in {"PASS", "PASS_WITH_OBSERVATIONS"} else (2 if verdict == "BLOCKED" else 1),
        "rules_violated": sorted(set(rules)),
        "source_commit": source_commit,
        "source_tree_hash": actual_tree if "actual_tree" in locals() else None,
        "artifact_hash": artifact_hash,
        "certificate_hash": cert_hash,
    }


def cmd_validate(args):
    result = evaluate(
        args.release,
        args.certificate,
        repo=args.repo,
        artifact=args.artifact,
        deployment_plan=args.deployment_plan,
        approval=args.approval,
        evidence_dir=args.evidence_dir,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) if args.format == "json" else "\n".join(
        [f"Traceability verdict: {result['verdict']}", f"Exit code: {result['exit_code']}"] +
        [f"  - {r}" for r in result["rules_violated"]]
    )
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return result["exit_code"]


def cmd_generate(args):
    repo = args.repo
    commit = verify_commit(repo, args.commit)
    tree = tree_hash(repo, commit)
    cert = load_json(args.certificate)
    cert_hash = canonical_json_hash(cert, exclude={"certificate_hash"})
    artifact_path = Path(args.artifact)
    if not artifact_path.exists():
        print("ERROR: artifact not found")
        return 3
    artifact_hash = sha256_file(artifact_path)
    manifest = {
        "release_id": args.release_id,
        "project_id": args.project,
        "version": args.version,
        "commit": commit,
        "source_commit": commit,
        "source_tree_hash": tree,
        "quality_certificate": str(args.certificate),
        "quality_certificate_hash": cert_hash,
        "evaluation_id": cert.get("evaluation_id"),
        "artifact": str(args.artifact),
        "artifact_hash": artifact_hash,
        "artifact_format": artifact_path.suffix.lstrip(".") or "unknown",
        "target_environment": args.environment,
        "created_by": args.responsible or "AG-016",
        "creation_timestamp": datetime.now(timezone.utc).isoformat(),
        "responsible_agent": args.responsible or "AG-016",
    }
    Path(args.output).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def cmd_hash_file(args):
    print(sha256_file(args.file))
    return 0


def cmd_git_info(args):
    commit = verify_commit(args.repo, args.commit)
    print(json.dumps({"commit": commit, "tree": tree_hash(args.repo, commit)}, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description="AI-Project-Factory Traceability Validator")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--release", required=True)
    validate.add_argument("--certificate", required=True)
    validate.add_argument("--repo", default=".")
    validate.add_argument("--artifact")
    validate.add_argument("--deployment-plan")
    validate.add_argument("--approval")
    validate.add_argument("--evidence-dir")
    validate.add_argument("--format", choices=["human", "json"], default="json")
    validate.add_argument("--output")
    validate.set_defaults(func=cmd_validate)

    generate = sub.add_parser("generate")
    generate.add_argument("--project", required=True)
    generate.add_argument("--version", required=True)
    generate.add_argument("--commit", required=True)
    generate.add_argument("--certificate", required=True)
    generate.add_argument("--artifact", required=True)
    generate.add_argument("--environment", required=True)
    generate.add_argument("--output", required=True)
    generate.add_argument("--repo", default=".")
    generate.add_argument("--release-id", default="REL-0001")
    generate.add_argument("--responsible", default="AG-016")
    generate.set_defaults(func=cmd_generate)

    hash_file = sub.add_parser("hash-file")
    hash_file.add_argument("file")
    hash_file.set_defaults(func=cmd_hash_file)

    git_info = sub.add_parser("git-info")
    git_info.add_argument("--repo", default=".")
    git_info.add_argument("--commit", required=True)
    git_info.set_defaults(func=cmd_git_info)

    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
